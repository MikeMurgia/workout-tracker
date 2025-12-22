"""
Recommendations Router
API endpoints for training recommendations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd

from database import get_db
from services import TrainingRecommender

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def get_dataframes(db: Session, days: int = 30):
    """Helper to get all needed DataFrames for recommendations"""
    
    # Get workouts
    workouts_query = text("""
        SELECT id, workout_date, perceived_exertion, name
        FROM workouts
        WHERE workout_date >= CURRENT_DATE - :days
        ORDER BY workout_date
    """)
    workouts_result = db.execute(workouts_query, {"days": days}).fetchall()
    workouts_df = pd.DataFrame(workouts_result, 
                                columns=['id', 'workout_date', 'perceived_exertion', 'name'])
    
    # Get sets
    sets_query = text("""
        SELECT id, workout_id, exercise_id, set_number, weight, reps, set_type, rpe
        FROM workout_sets
    """)
    sets_result = db.execute(sets_query).fetchall()
    sets_df = pd.DataFrame(sets_result,
                           columns=['id', 'workout_id', 'exercise_id', 'set_number',
                                   'weight', 'reps', 'set_type', 'rpe'])
    
    # Get exercises
    exercises_query = text("""
        SELECT id, name, muscle_group, movement_type, equipment, is_compound
        FROM exercises
    """)
    exercises_result = db.execute(exercises_query).fetchall()
    exercises_df = pd.DataFrame(exercises_result,
                                 columns=['id', 'name', 'muscle_group', 'movement_type',
                                         'equipment', 'is_compound'])
    
    return workouts_df, sets_df, exercises_df


@router.get("/next-workout")
async def get_next_workout_recommendation(
    db: Session = Depends(get_db)
):
    """
    Get a recommendation for your next workout.
    
    Based on:
    - What muscle groups you've trained recently
    - Recovery time since last training each muscle
    - Overall training balance
    """
    workouts_df, sets_df, exercises_df = get_dataframes(db, days=14)
    
    if len(workouts_df) == 0:
        # No recent workouts - suggest a balanced start
        return {
            "recommendation": "full_body",
            "reason": "No recent workouts found - start with a full body session",
            "suggested_muscles": ["chest", "back", "legs"],
            "exercises": _get_starter_exercises(exercises_df)
        }
    
    recommender = TrainingRecommender()
    recommendation = recommender.get_next_workout_recommendation(
        workouts_df, sets_df, exercises_df
    )
    
    return recommendation


def _get_starter_exercises(exercises_df: pd.DataFrame):
    """Get basic exercises for each major muscle group"""
    suggestions = []
    
    priority_exercises = [
        ("Barbell Bench Press", "chest"),
        ("Barbell Row", "back"),
        ("Barbell Squat", "legs"),
        ("Overhead Press", "shoulders"),
    ]
    
    for exercise_name, muscle in priority_exercises:
        match = exercises_df[exercises_df['name'] == exercise_name]
        if len(match) > 0:
            ex = match.iloc[0]
            suggestions.append({
                "exercise_id": ex['id'],
                "name": ex['name'],
                "muscle_group": muscle,
                "equipment": ex['equipment'],
                "is_compound": ex['is_compound']
            })
    
    return suggestions


@router.get("/balance")
async def get_training_balance(
    days: int = Query(default=7, ge=7, le=30),
    db: Session = Depends(get_db)
):
    """
    Analyze your muscle group training balance.
    
    Shows:
    - Sets per muscle group
    - Volume per muscle group
    - Comparison to optimal ranges
    - Recommendations for underexercised or overtrained areas
    
    - **days**: Number of days to analyze (7-30)
    """
    workouts_df, sets_df, exercises_df = get_dataframes(db, days=days)
    
    if len(workouts_df) == 0:
        return {
            "period_days": days,
            "message": "No workouts found in this period",
            "muscle_groups": {}
        }
    
    recommender = TrainingRecommender()
    balance = recommender.analyze_training_balance(
        workouts_df, sets_df, exercises_df, days=days
    )
    
    return balance


@router.get("/deload")
async def check_deload_needed(
    db: Session = Depends(get_db)
):
    """
    Check if you should take a deload week.
    
    Analyzes:
    - Training streak length
    - Perceived exertion trends
    - Signs of accumulated fatigue
    """
    # Get more history for deload analysis
    workouts_query = text("""
        SELECT id, workout_date, perceived_exertion, name
        FROM workouts
        ORDER BY workout_date
    """)
    workouts_result = db.execute(workouts_query).fetchall()
    workouts_df = pd.DataFrame(workouts_result,
                                columns=['id', 'workout_date', 'perceived_exertion', 'name'])
    
    if len(workouts_df) < 8:
        return {
            "needs_deload": False,
            "reason": "Not enough training history to evaluate",
            "workouts_logged": len(workouts_df),
            "minimum_needed": 8
        }
    
    sets_query = text("SELECT id, workout_id, exercise_id, weight, reps, set_type FROM workout_sets")
    sets_result = db.execute(sets_query).fetchall()
    sets_df = pd.DataFrame(sets_result,
                           columns=['id', 'workout_id', 'exercise_id', 'weight', 'reps', 'set_type'])
    
    recommender = TrainingRecommender()
    deload_recommendation = recommender.suggest_deload(workouts_df, sets_df)
    
    return deload_recommendation


@router.get("/exercises")
async def get_exercise_recommendations(
    muscle_group: str = Query(..., description="Target muscle group"),
    equipment: str = Query(default=None, description="Available equipment (optional)"),
    limit: int = Query(default=5, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """
    Get exercise recommendations for a specific muscle group.
    
    - **muscle_group**: Target muscle (chest, back, legs, shoulders, arms, core)
    - **equipment**: Filter by equipment type (barbell, dumbbell, cable, machine, bodyweight)
    - **limit**: Number of exercises to return (1-10)
    """
    query = text("""
        SELECT id, name, muscle_group, movement_type, equipment, is_compound, description
        FROM exercises
        WHERE muscle_group = :muscle_group
        ORDER BY is_compound DESC, name
    """)
    
    result = db.execute(query, {"muscle_group": muscle_group.lower()}).fetchall()
    
    if len(result) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No exercises found for muscle group: {muscle_group}"
        )
    
    exercises = []
    for row in result:
        ex = {
            "id": row[0],
            "name": row[1],
            "muscle_group": row[2],
            "movement_type": row[3],
            "equipment": row[4],
            "is_compound": row[5],
            "description": row[6]
        }
        
        # Filter by equipment if specified
        if equipment and ex['equipment'] != equipment.lower():
            continue
            
        exercises.append(ex)
        
        if len(exercises) >= limit:
            break
    
    # Separate compounds and isolations
    compounds = [e for e in exercises if e['is_compound']]
    isolations = [e for e in exercises if not e['is_compound']]
    
    return {
        "muscle_group": muscle_group,
        "equipment_filter": equipment,
        "total_found": len(exercises),
        "recommendation": "Start with compound movements, finish with isolations",
        "compound_exercises": compounds,
        "isolation_exercises": isolations
    }
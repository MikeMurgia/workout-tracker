"""
Analysis Router
API endpoints for workout analysis, anomaly detection, and health scores
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd
from typing import Optional

from database import get_db
from services import AnomalyDetector

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get("/anomalies/{exercise_id}")
async def detect_exercise_anomalies(
    exercise_id: str,
    days: int = Query(default=90, ge=30, le=365),
    db: Session = Depends(get_db)
):
    """
    Detect unusual patterns in an exercise's history.
    
    Identifies:
    - Performance drops (possible fatigue/injury)
    - Performance spikes (possible PRs)
    - Volume anomalies
    - Training gaps
    
    - **exercise_id**: UUID of the exercise to analyze
    - **days**: Number of days to analyze (30-365)
    """
    # Get exercise info
    exercise_result = db.execute(
        text("SELECT id, name, muscle_group FROM exercises WHERE id = :id"),
        {"id": exercise_id}
    ).fetchone()
    
    if not exercise_result:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Get historical data
    query = text("""
        SELECT 
            w.workout_date,
            MAX(ws.weight) as max_weight,
            MAX(ws.reps) as reps_at_max_weight,
            SUM(CASE WHEN ws.set_type = 'working' THEN ws.weight * ws.reps ELSE 0 END) as total_volume,
            AVG(ws.rpe) as avg_rpe,
            w.perceived_exertion
        FROM workout_sets ws
        JOIN workouts w ON ws.workout_id = w.id
        WHERE ws.exercise_id = CAST(:exercise_id AS UUID)
          AND w.workout_date >= CURRENT_DATE - CAST(:days AS INTEGER)
        GROUP BY w.id, w.workout_date, w.perceived_exertion
        ORDER BY w.workout_date
    """)
    
    result = db.execute(query, {"exercise_id": exercise_id, "days": days}).fetchall()
    
    if len(result) < 3:
        return {
            "exercise": {
                "id": exercise_result[0],
                "name": exercise_result[1],
                "muscle_group": exercise_result[2]
            },
            "message": "Not enough data for anomaly detection (need at least 3 sessions)",
            "anomalies": []
        }
    
    # Convert to DataFrame
    df = pd.DataFrame(result, columns=['workout_date', 'max_weight', 'reps_at_max_weight',
                                        'total_volume', 'avg_rpe', 'perceived_exertion'])
    
    # Convert Decimal types to float for pandas compatibility
    df['max_weight'] = pd.to_numeric(df['max_weight'], errors='coerce')
    df['reps_at_max_weight'] = pd.to_numeric(df['reps_at_max_weight'], errors='coerce')
    df['total_volume'] = pd.to_numeric(df['total_volume'], errors='coerce').fillna(0)
    df['avg_rpe'] = pd.to_numeric(df['avg_rpe'], errors='coerce')
    df['perceived_exertion'] = pd.to_numeric(df['perceived_exertion'], errors='coerce')
    
    # Calculate estimated 1RM
    df['estimated_1rm'] = df.apply(
        lambda row: row['max_weight'] * (1 + row['reps_at_max_weight'] / 30)
                    if pd.notna(row['max_weight']) and pd.notna(row['reps_at_max_weight'])
                    else None,
        axis=1
    )
    
    # Run anomaly detection
    detector = AnomalyDetector(z_threshold=2.0)
    anomalies = detector.detect_anomalies(df)
    
    return {
        "exercise": {
            "id": exercise_result[0],
            "name": exercise_result[1],
            "muscle_group": exercise_result[2]
        },
        "period_days": days,
        "sessions_analyzed": len(df),
        "anomalies_found": len(anomalies),
        "anomalies": anomalies
    }


@router.get("/health")
async def get_training_health_score(
    days: int = Query(default=30, ge=14, le=90),
    db: Session = Depends(get_db)
):
    """
    Get an overall training health score.
    
    Evaluates:
    - Training consistency
    - Progressive overload
    - Volume management
    - Recovery patterns
    
    Returns a score from 0-100 with recommendations.
    
    - **days**: Number of days to evaluate (14-90)
    """
    # Get workout history with sets
    query = text("""
        SELECT 
            w.id,
            w.workout_date,
            w.perceived_exertion,
            COUNT(CASE WHEN ws.set_type = 'working' THEN 1 END) as working_sets,
            SUM(CASE WHEN ws.set_type = 'working' THEN ws.weight * ws.reps ELSE 0 END) as total_volume,
            AVG(ws.rpe) as avg_rpe
        FROM workouts w
        LEFT JOIN workout_sets ws ON w.id = ws.workout_id
        WHERE w.workout_date >= CURRENT_DATE - CAST(:days AS INTEGER)
        GROUP BY w.id, w.workout_date, w.perceived_exertion
        ORDER BY w.workout_date
    """)
    
    result = db.execute(query, {"days": days}).fetchall()
    
    if len(result) < 5:
        return {
            "score": None,
            "message": f"Need at least 5 workouts for health score. Found: {len(result)}",
            "recommendation": "Keep training consistently to build enough data"
        }
    
    df = pd.DataFrame(result, columns=['id', 'workout_date', 'perceived_exertion',
                                        'working_sets', 'total_volume', 'avg_rpe'])
    
    # Convert Decimal types to float for pandas compatibility
    df['working_sets'] = pd.to_numeric(df['working_sets'], errors='coerce').fillna(0)
    df['total_volume'] = pd.to_numeric(df['total_volume'], errors='coerce').fillna(0)
    df['avg_rpe'] = pd.to_numeric(df['avg_rpe'], errors='coerce')
    df['perceived_exertion'] = pd.to_numeric(df['perceived_exertion'], errors='coerce')
    
    # For health score, we need a dummy 1RM column (using volume as proxy)
    df['estimated_1rm'] = df['total_volume'] / df['working_sets'].replace(0, 1)
    
    detector = AnomalyDetector()
    health = detector.get_health_score(df)
    
    return {
        "period_days": days,
        "workouts_analyzed": len(df),
        **health
    }


@router.get("/anomalies")
async def detect_all_anomalies(
    days: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db)
):
    """
    Detect anomalies across all recent workouts.
    
    Provides a holistic view of training patterns and potential issues.
    
    - **days**: Number of days to analyze (7-90)
    """
    # Get all workout data
    query = text("""
        SELECT 
            w.workout_date,
            w.perceived_exertion,
            e.name as exercise_name,
            e.muscle_group,
            MAX(ws.weight) as max_weight,
            SUM(CASE WHEN ws.set_type = 'working' THEN ws.weight * ws.reps ELSE 0 END) as total_volume,
            AVG(ws.rpe) as avg_rpe,
            COUNT(ws.id) as set_count
        FROM workouts w
        JOIN workout_sets ws ON w.id = ws.workout_id
        JOIN exercises e ON ws.exercise_id = e.id
        WHERE w.workout_date >= CURRENT_DATE - CAST(:days AS INTEGER)
        GROUP BY w.id, w.workout_date, w.perceived_exertion, e.id, e.name, e.muscle_group
        ORDER BY w.workout_date
    """)
    
    result = db.execute(query, {"days": days}).fetchall()
    
    if len(result) < 3:
        return {
            "period_days": days,
            "message": "Not enough data for analysis",
            "anomalies": []
        }
    
    df = pd.DataFrame(result, columns=['workout_date', 'perceived_exertion', 'exercise_name',
                                        'muscle_group', 'max_weight', 'total_volume', 
                                        'avg_rpe', 'set_count'])
    
    # Convert Decimal types to float for pandas compatibility
    df['max_weight'] = pd.to_numeric(df['max_weight'], errors='coerce')
    df['total_volume'] = pd.to_numeric(df['total_volume'], errors='coerce').fillna(0)
    df['avg_rpe'] = pd.to_numeric(df['avg_rpe'], errors='coerce')
    df['set_count'] = pd.to_numeric(df['set_count'], errors='coerce').fillna(0)
    df['perceived_exertion'] = pd.to_numeric(df['perceived_exertion'], errors='coerce')
    
    # Aggregate by workout date for overall anomalies
    workout_df = df.groupby('workout_date').agg({
        'perceived_exertion': 'first',
        'total_volume': 'sum',
        'avg_rpe': 'mean',
        'set_count': 'sum',
        'max_weight': 'max'
    }).reset_index()
    
    workout_df['estimated_1rm'] = workout_df['max_weight']  # Simplified
    
    detector = AnomalyDetector()
    anomalies = detector.detect_anomalies(workout_df)
    
    # Add muscle group imbalance detection
    muscle_volume = df.groupby('muscle_group')['total_volume'].sum()
    total_volume = muscle_volume.sum()
    
    imbalances = []
    if total_volume > 0:
        for muscle, volume in muscle_volume.items():
            percentage = (volume / total_volume) * 100
            if percentage > 40:
                imbalances.append({
                    'muscle_group': muscle,
                    'percentage': round(percentage, 1),
                    'issue': 'overtrained',
                    'message': f'{muscle} accounts for {percentage:.0f}% of your training volume'
                })
            elif percentage < 5 and muscle in ['legs', 'back', 'chest']:
                imbalances.append({
                    'muscle_group': muscle,
                    'percentage': round(percentage, 1),
                    'issue': 'undertrained',
                    'message': f'{muscle} only accounts for {percentage:.0f}% of your training'
                })
    
    return {
        "period_days": days,
        "workouts_analyzed": len(workout_df),
        "anomalies": anomalies,
        "muscle_imbalances": imbalances,
        "summary": {
            "total_anomalies": len(anomalies),
            "high_severity": len([a for a in anomalies if a['severity'] == 'high']),
            "medium_severity": len([a for a in anomalies if a['severity'] == 'medium']),
            "low_severity": len([a for a in anomalies if a['severity'] == 'low'])
        }
    }
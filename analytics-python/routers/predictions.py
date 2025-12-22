"""
Predictions Router
API endpoints for ML-powered predictions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd
from typing import Optional

from database import get_db
from services import StrengthPredictor, calculate_1rm

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get("/strength/{exercise_id}")
async def predict_strength(
    exercise_id: str,
    days_ahead: int = Query(default=30, ge=7, le=180),
    db: Session = Depends(get_db)
):
    """
    Predict future strength for an exercise.
    
    Uses machine learning to forecast your estimated 1RM based on historical data.
    
    - **exercise_id**: UUID of the exercise to predict
    - **days_ahead**: How far into the future to predict (7-180 days)
    """
    # Get exercise info
    exercise_result = db.execute(
        text("SELECT id, name, muscle_group FROM exercises WHERE id = :id"),
        {"id": exercise_id}
    ).fetchone()
    
    if not exercise_result:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Get historical data for this exercise
    query = text("""
        SELECT 
            w.workout_date,
            MAX(ws.weight) as max_weight,
            MAX(ws.reps) as reps_at_max_weight,
            SUM(CASE WHEN ws.set_type = 'working' THEN ws.weight * ws.reps ELSE 0 END) as total_volume,
            AVG(ws.rpe) as avg_rpe
        FROM workout_sets ws
        JOIN workouts w ON ws.workout_id = w.id
        WHERE ws.exercise_id = CAST(:exercise_id AS UUID)
        GROUP BY w.id, w.workout_date
        ORDER BY w.workout_date
    """)
    
    result = db.execute(query, {"exercise_id": exercise_id}).fetchall()
    
    if len(result) < 3:
        raise HTTPException(
            status_code=400, 
            detail=f"Need at least 3 workout sessions for predictions. Found: {len(result)}"
        )
    
    # Convert to DataFrame
    df = pd.DataFrame(result, columns=['workout_date', 'max_weight', 'reps_at_max_weight', 
                                        'total_volume', 'avg_rpe'])
    
    # Convert Decimal types to float for pandas compatibility
    df['max_weight'] = pd.to_numeric(df['max_weight'], errors='coerce')
    df['reps_at_max_weight'] = pd.to_numeric(df['reps_at_max_weight'], errors='coerce')
    df['total_volume'] = pd.to_numeric(df['total_volume'], errors='coerce').fillna(0)
    df['avg_rpe'] = pd.to_numeric(df['avg_rpe'], errors='coerce')
    
    # Calculate estimated 1RM for each session
    df['estimated_1rm'] = df.apply(
        lambda row: calculate_1rm(row['max_weight'], row['reps_at_max_weight']) 
                    if pd.notna(row['max_weight']) and pd.notna(row['reps_at_max_weight']) 
                    else None,
        axis=1
    )
    
    # Remove rows without 1RM
    df = df.dropna(subset=['estimated_1rm'])
    
    if len(df) < 3:
        raise HTTPException(
            status_code=400,
            detail="Not enough valid data points for prediction"
        )
    
    # Train predictor and make predictions
    predictor = StrengthPredictor()
    
    try:
        training_metrics = predictor.train(df)
        predictions = predictor.predict_future(days_ahead=days_ahead)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
    
    return {
        "exercise": {
            "id": exercise_result[0],
            "name": exercise_result[1],
            "muscle_group": exercise_result[2]
        },
        "current_estimated_1rm": round(df['estimated_1rm'].iloc[-1], 1),
        "training_sessions_used": len(df),
        "model_metrics": training_metrics,
        "predictions": predictions
    }


@router.get("/goal/{exercise_id}")
async def predict_goal_date(
    exercise_id: str,
    target_weight: float = Query(..., gt=0, description="Target weight to achieve"),
    db: Session = Depends(get_db)
):
    """
    Predict when you'll reach a specific strength goal.
    
    - **exercise_id**: UUID of the exercise
    - **target_weight**: The weight you want to be able to lift (1RM)
    """
    # Get exercise info
    exercise_result = db.execute(
        text("SELECT id, name FROM exercises WHERE id = :id"),
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
            AVG(ws.rpe) as avg_rpe
        FROM workout_sets ws
        JOIN workouts w ON ws.workout_id = w.id
        WHERE ws.exercise_id = CAST(:exercise_id AS UUID)
        GROUP BY w.id, w.workout_date
        ORDER BY w.workout_date
    """)
    
    result = db.execute(query, {"exercise_id": exercise_id}).fetchall()
    
    if len(result) < 3:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 3 workout sessions. Found: {len(result)}"
        )
    
    # Convert to DataFrame
    df = pd.DataFrame(result, columns=['workout_date', 'max_weight', 'reps_at_max_weight',
                                        'total_volume', 'avg_rpe'])
    
    # Convert Decimal types to float for pandas compatibility
    df['max_weight'] = pd.to_numeric(df['max_weight'], errors='coerce')
    df['reps_at_max_weight'] = pd.to_numeric(df['reps_at_max_weight'], errors='coerce')
    df['total_volume'] = pd.to_numeric(df['total_volume'], errors='coerce').fillna(0)
    df['avg_rpe'] = pd.to_numeric(df['avg_rpe'], errors='coerce')
    
    df['estimated_1rm'] = df.apply(
        lambda row: calculate_1rm(row['max_weight'], row['reps_at_max_weight'])
                    if pd.notna(row['max_weight']) and pd.notna(row['reps_at_max_weight'])
                    else None,
        axis=1
    )
    df = df.dropna(subset=['estimated_1rm'])
    
    # Train and predict
    predictor = StrengthPredictor()
    predictor.train(df)
    
    prediction = predictor.predict_target_date(target_weight)
    
    return {
        "exercise": {
            "id": exercise_result[0],
            "name": exercise_result[1]
        },
        "target_weight": target_weight,
        "prediction": prediction
    }


@router.get("/1rm/calculate")
async def calculate_one_rep_max(
    weight: float = Query(..., gt=0),
    reps: int = Query(..., ge=1, le=30),
    formula: str = Query(default="average", regex="^(epley|brzycki|lombardi|oconner|average)$")
):
    """
    Calculate estimated 1RM using various formulas.
    
    - **weight**: Weight lifted
    - **reps**: Number of reps completed
    - **formula**: Formula to use (epley, brzycki, lombardi, oconner, average)
    """
    if reps == 1:
        return {
            "weight": weight,
            "reps": reps,
            "estimated_1rm": weight,
            "note": "1 rep = actual 1RM"
        }
    
    all_formulas = {
        'epley': round(calculate_1rm(weight, reps, 'epley'), 1),
        'brzycki': round(calculate_1rm(weight, reps, 'brzycki'), 1),
        'lombardi': round(calculate_1rm(weight, reps, 'lombardi'), 1),
        'oconner': round(calculate_1rm(weight, reps, 'oconner'), 1),
    }
    
    if formula == 'average':
        result = round(sum(all_formulas.values()) / len(all_formulas), 1)
    else:
        result = all_formulas[formula]
    
    return {
        "weight": weight,
        "reps": reps,
        "formula": formula,
        "estimated_1rm": result,
        "all_formulas": all_formulas
    }
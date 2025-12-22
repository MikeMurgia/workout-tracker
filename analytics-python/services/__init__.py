"""
Analytics Services Package

Contains the core data science logic:
- StrengthPredictor: ML-based strength predictions
- AnomalyDetector: Identifies unusual patterns
- TrainingRecommender: Suggests workouts and exercises
"""

from .strength_predictor import StrengthPredictor, calculate_1rm
from .anomaly_detector import AnomalyDetector, AnomalyType
from .recommender import TrainingRecommender

__all__ = [
    'StrengthPredictor',
    'calculate_1rm',
    'AnomalyDetector', 
    'AnomalyType',
    'TrainingRecommender'
]
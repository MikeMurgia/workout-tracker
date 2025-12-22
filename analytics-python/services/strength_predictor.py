"""
Strength Prediction Service
Uses machine learning to predict future strength levels

CONCEPTS DEMONSTRATED:
1. Time Series Analysis - treating workout data as a time series
2. Feature Engineering - creating useful features from raw data
3. Multiple Models - comparing different approaches
4. Model Evaluation - measuring prediction accuracy
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings

warnings.filterwarnings('ignore')


class StrengthPredictor:
    """
    Predicts future strength levels for a given exercise.
    
    Uses multiple approaches:
    1. Linear Regression - simple trend line
    2. Polynomial Regression - captures non-linear progress
    3. Weighted Recent - gives more importance to recent data
    """
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.poly_features = PolynomialFeatures(degree=2, include_bias=False)
        
    def prepare_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare raw workout data for modeling.
        
        Feature Engineering:
        - days_since_start: Numeric representation of time
        - cumulative_volume: Total volume lifted up to that point
        - rolling_avg: Moving average of recent performance
        - session_number: Which workout session this is
        
        Args:
            df: DataFrame with columns [workout_date, max_weight, total_volume, estimated_1rm]
            
        Returns:
            X: Feature matrix
            y: Target values (estimated 1RM or max weight)
        """
        if len(df) < 2:
            raise ValueError("Need at least 2 data points for prediction")
        
        # Sort by date
        df = df.sort_values('workout_date').copy()
        
        # Convert dates to numeric (days since first workout)
        df['workout_date'] = pd.to_datetime(df['workout_date'])
        start_date = df['workout_date'].min()
        df['days_since_start'] = (df['workout_date'] - start_date).dt.days
        
        # Feature: Session number
        df['session_number'] = range(1, len(df) + 1)
        
        # Feature: Cumulative volume (total work done up to this point)
        df['cumulative_volume'] = df['total_volume'].cumsum()
        
        # Feature: Rolling average of 1RM (last 3 sessions)
        df['rolling_avg_1rm'] = df['estimated_1rm'].rolling(window=3, min_periods=1).mean()
        
        # Feature: Days since last session (recovery time)
        df['days_since_last'] = df['days_since_start'].diff().fillna(7)
        
        # Feature: Volume trend (increasing or decreasing)
        df['volume_trend'] = df['total_volume'].pct_change().fillna(0)
        
        # Select features for the model
        feature_columns = [
            'days_since_start',
            'session_number', 
            'cumulative_volume',
            'rolling_avg_1rm',
            'days_since_last'
        ]
        
        X = df[feature_columns].values
        y = df['estimated_1rm'].values
        
        return X, y, df
    
    def train(self, df: pd.DataFrame) -> Dict:
        """
        Train the prediction model on historical data.
        
        Tries multiple models and selects the best one based on 
        cross-validation score.
        
        Args:
            df: DataFrame with workout history
            
        Returns:
            Dictionary with training metrics
        """
        X, y, processed_df = self.prepare_data(df)
        
        # Store for later use
        self.training_data = processed_df
        self.last_date = processed_df['workout_date'].max()
        self.last_days = processed_df['days_since_start'].max()
        self.last_session = len(processed_df)
        self.last_cumulative_volume = processed_df['cumulative_volume'].iloc[-1]
        self.last_1rm = processed_df['estimated_1rm'].iloc[-1]
        self.avg_days_between = processed_df['days_since_last'].mean()
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Try different models
        models = {
            'linear': LinearRegression(),
            'ridge': Ridge(alpha=1.0),  # Regularized to prevent overfitting
        }
        
        best_score = -float('inf')
        best_model_name = None
        scores = {}
        
        for name, model in models.items():
            # Use cross-validation if we have enough data
            if len(X) >= 5:
                cv_scores = cross_val_score(model, X_scaled, y, cv=min(5, len(X)), 
                                           scoring='neg_mean_absolute_error')
                score = cv_scores.mean()
            else:
                # Not enough data for CV, just fit and use R²
                model.fit(X_scaled, y)
                score = model.score(X_scaled, y)
            
            scores[name] = score
            
            if score > best_score:
                best_score = score
                best_model_name = name
        
        # Train the best model on all data
        self.model = models[best_model_name]
        self.model.fit(X_scaled, y)
        
        # Calculate training metrics
        predictions = self.model.predict(X_scaled)
        mae = mean_absolute_error(y, predictions)
        rmse = np.sqrt(mean_squared_error(y, predictions))
        
        return {
            'model_type': best_model_name,
            'data_points': len(X),
            'mae': round(mae, 2),  # Mean Absolute Error in lbs
            'rmse': round(rmse, 2),  # Root Mean Square Error
            'r_squared': round(self.model.score(X_scaled, y), 3),
            'model_scores': {k: round(v, 3) for k, v in scores.items()}
        }
    
    def predict_future(self, days_ahead: int = 30, sessions_ahead: int = None) -> List[Dict]:
        """
        Predict future strength levels.
        
        Args:
            days_ahead: How many days into the future to predict
            sessions_ahead: Alternative - predict for N future sessions
            
        Returns:
            List of predictions with dates and estimated 1RM
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        predictions = []
        
        # Estimate sessions based on average training frequency
        if sessions_ahead is None:
            sessions_ahead = max(1, int(days_ahead / self.avg_days_between))
        
        for i in range(1, sessions_ahead + 1):
            # Estimate the date of this future session
            future_days = self.last_days + (i * self.avg_days_between)
            future_date = self.last_date + timedelta(days=int(i * self.avg_days_between))
            
            # Estimate features for this future session
            future_session = self.last_session + i
            
            # Assume volume continues at similar rate
            avg_volume_per_session = self.last_cumulative_volume / self.last_session
            future_cumulative_volume = self.last_cumulative_volume + (i * avg_volume_per_session)
            
            # Rolling average will be close to recent performance
            future_rolling_avg = self.last_1rm
            
            # Create feature vector
            X_future = np.array([[
                future_days,
                future_session,
                future_cumulative_volume,
                future_rolling_avg,
                self.avg_days_between
            ]])
            
            # Scale and predict
            X_future_scaled = self.scaler.transform(X_future)
            predicted_1rm = self.model.predict(X_future_scaled)[0]
            
            predictions.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'session_number': future_session,
                'predicted_1rm': round(predicted_1rm, 1),
                'days_from_now': int(future_days - self.last_days)
            })
            
            # Update rolling average for next prediction
            future_rolling_avg = predicted_1rm
        
        return predictions
    
    def predict_target_date(self, target_weight: float) -> Optional[Dict]:
        """
        Predict when you'll reach a target weight.
        
        Args:
            target_weight: The goal weight to predict
            
        Returns:
            Dictionary with predicted date and confidence, or None if unreachable
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Get current level
        current_1rm = self.last_1rm
        
        if target_weight <= current_1rm:
            return {
                'status': 'already_achieved',
                'message': f'You can already lift {target_weight} lbs (current 1RM: {current_1rm})'
            }
        
        # Predict forward until we hit the target (max 365 days)
        for days in range(1, 366):
            future_date = self.last_date + timedelta(days=days)
            sessions = int(days / self.avg_days_between)
            
            if sessions < 1:
                continue
                
            predictions = self.predict_future(sessions_ahead=sessions)
            
            if predictions and predictions[-1]['predicted_1rm'] >= target_weight:
                return {
                    'status': 'achievable',
                    'target_weight': target_weight,
                    'predicted_date': predictions[-1]['date'],
                    'days_from_now': days,
                    'sessions_needed': sessions,
                    'current_1rm': round(current_1rm, 1)
                }
        
        # Calculate rate of progress
        if len(self.training_data) >= 2:
            first_1rm = self.training_data['estimated_1rm'].iloc[0]
            total_days = self.last_days
            if total_days > 0:
                rate_per_day = (current_1rm - first_1rm) / total_days
                if rate_per_day > 0:
                    days_needed = (target_weight - current_1rm) / rate_per_day
                    return {
                        'status': 'long_term',
                        'target_weight': target_weight,
                        'estimated_days': int(days_needed),
                        'message': f'At current rate, this could take ~{int(days_needed)} days'
                    }
        
        return {
            'status': 'uncertain',
            'message': 'Not enough data to predict this target'
        }


def calculate_1rm(weight: float, reps: int, formula: str = 'epley') -> float:
    """
    Calculate estimated 1RM using various formulas.
    
    Args:
        weight: Weight lifted
        reps: Number of reps
        formula: Which formula to use ('epley', 'brzycki', 'lombardi', 'average')
        
    Returns:
        Estimated 1RM
    """
    if reps == 1:
        return weight
    if reps < 1 or weight <= 0:
        return 0
    
    formulas = {
        'epley': weight * (1 + reps / 30),
        'brzycki': weight * (36 / (37 - reps)) if reps < 37 else weight * 2,
        'lombardi': weight * (reps ** 0.10),
        'oconner': weight * (1 + reps / 40),
        'mayhew': weight * (100 / (52.2 + 41.9 * np.exp(-0.055 * reps)))
    }
    
    if formula == 'average':
        return np.mean(list(formulas.values()))
    
    return formulas.get(formula, formulas['epley'])
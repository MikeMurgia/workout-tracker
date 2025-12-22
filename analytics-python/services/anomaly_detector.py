"""
Anomaly Detection Service
Identifies unusual workouts and patterns

CONCEPTS DEMONSTRATED:
1. Statistical Methods - Z-scores, IQR
2. Trend Analysis - Detecting changes in performance
3. Fatigue Detection - Identifying overtraining signals
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class AnomalyType(str, Enum):
    """Types of anomalies we can detect"""
    PERFORMANCE_DROP = "performance_drop"
    PERFORMANCE_SPIKE = "performance_spike"
    VOLUME_SPIKE = "volume_spike"
    VOLUME_DROP = "volume_drop"
    HIGH_FATIGUE = "high_fatigue"
    POSSIBLE_PR = "possible_pr"
    LONG_GAP = "long_gap"
    UNUSUAL_RPE = "unusual_rpe"


@dataclass
class Anomaly:
    """Represents a detected anomaly"""
    type: AnomalyType
    date: str
    severity: str  # 'low', 'medium', 'high'
    message: str
    details: Dict
    

class AnomalyDetector:
    """
    Detects unusual patterns in workout data.
    
    Uses statistical methods to identify:
    - Unexpected performance drops (possible injury/fatigue)
    - Performance spikes (possible PRs)
    - Training load anomalies
    - Recovery issues
    """
    
    def __init__(self, z_threshold: float = 2.0):
        """
        Args:
            z_threshold: How many standard deviations from mean counts as anomaly
        """
        self.z_threshold = z_threshold
        
    def detect_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """
        Run all anomaly detection checks on workout data.
        
        Args:
            df: DataFrame with columns [workout_date, max_weight, total_volume, 
                                       estimated_1rm, avg_rpe, perceived_exertion]
                                       
        Returns:
            List of detected anomalies
        """
        if len(df) < 3:
            return []
        
        df = df.sort_values('workout_date').copy()
        df['workout_date'] = pd.to_datetime(df['workout_date'])
        
        anomalies = []
        
        # Run each detection method
        anomalies.extend(self._detect_performance_anomalies(df))
        anomalies.extend(self._detect_volume_anomalies(df))
        anomalies.extend(self._detect_fatigue_signals(df))
        anomalies.extend(self._detect_training_gaps(df))
        
        # Sort by date (most recent first)
        anomalies.sort(key=lambda x: x['date'], reverse=True)
        
        return anomalies
    
    def _calculate_z_score(self, value: float, series: pd.Series) -> float:
        """Calculate z-score for a value given a series"""
        mean = series.mean()
        std = series.std()
        if std == 0:
            return 0
        return (value - mean) / std
    
    def _detect_performance_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """Detect unusual strength performance"""
        anomalies = []
        
        if 'estimated_1rm' not in df.columns or df['estimated_1rm'].isna().all():
            return anomalies
        
        # Calculate rolling statistics
        df['rolling_mean'] = df['estimated_1rm'].rolling(window=5, min_periods=2).mean()
        df['rolling_std'] = df['estimated_1rm'].rolling(window=5, min_periods=2).std()
        
        for idx, row in df.iterrows():
            if pd.isna(row['rolling_mean']) or pd.isna(row['rolling_std']):
                continue
            if row['rolling_std'] == 0:
                continue
                
            z_score = (row['estimated_1rm'] - row['rolling_mean']) / row['rolling_std']
            
            # Performance drop
            if z_score < -self.z_threshold:
                severity = 'high' if z_score < -3 else 'medium'
                anomalies.append({
                    'type': AnomalyType.PERFORMANCE_DROP.value,
                    'date': row['workout_date'].strftime('%Y-%m-%d'),
                    'severity': severity,
                    'message': f"Performance dropped significantly ({abs(z_score):.1f} std below average)",
                    'details': {
                        'actual_1rm': round(row['estimated_1rm'], 1),
                        'expected_1rm': round(row['rolling_mean'], 1),
                        'z_score': round(z_score, 2)
                    }
                })
            
            # Performance spike (possible PR)
            elif z_score > self.z_threshold:
                severity = 'low'  # Good anomaly!
                anomalies.append({
                    'type': AnomalyType.PERFORMANCE_SPIKE.value,
                    'date': row['workout_date'].strftime('%Y-%m-%d'),
                    'severity': severity,
                    'message': f"Exceptional performance! ({z_score:.1f} std above average)",
                    'details': {
                        'actual_1rm': round(row['estimated_1rm'], 1),
                        'expected_1rm': round(row['rolling_mean'], 1),
                        'z_score': round(z_score, 2)
                    }
                })
        
        return anomalies
    
    def _detect_volume_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """Detect unusual training volume"""
        anomalies = []
        
        if 'total_volume' not in df.columns:
            return anomalies
            
        mean_volume = df['total_volume'].mean()
        std_volume = df['total_volume'].std()
        
        if std_volume == 0:
            return anomalies
        
        for idx, row in df.iterrows():
            z_score = (row['total_volume'] - mean_volume) / std_volume
            
            if z_score > self.z_threshold:
                anomalies.append({
                    'type': AnomalyType.VOLUME_SPIKE.value,
                    'date': row['workout_date'].strftime('%Y-%m-%d'),
                    'severity': 'medium',
                    'message': f"Training volume unusually high",
                    'details': {
                        'volume': round(row['total_volume'], 0),
                        'average_volume': round(mean_volume, 0),
                        'percent_above': round((row['total_volume'] / mean_volume - 1) * 100, 1)
                    }
                })
            elif z_score < -self.z_threshold:
                anomalies.append({
                    'type': AnomalyType.VOLUME_DROP.value,
                    'date': row['workout_date'].strftime('%Y-%m-%d'),
                    'severity': 'low',
                    'message': f"Training volume unusually low",
                    'details': {
                        'volume': round(row['total_volume'], 0),
                        'average_volume': round(mean_volume, 0),
                        'percent_below': round((1 - row['total_volume'] / mean_volume) * 100, 1)
                    }
                })
        
        return anomalies
    
    def _detect_fatigue_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Detect signs of fatigue or overtraining"""
        anomalies = []
        
        # Check for high RPE combined with lower performance
        if 'avg_rpe' in df.columns and 'estimated_1rm' in df.columns:
            df['performance_trend'] = df['estimated_1rm'].pct_change()
            
            for idx, row in df.iterrows():
                # High RPE (8+) but performance declining
                if (not pd.isna(row.get('avg_rpe')) and 
                    row['avg_rpe'] >= 8.5 and 
                    not pd.isna(row.get('performance_trend')) and
                    row['performance_trend'] < -0.05):
                    
                    anomalies.append({
                        'type': AnomalyType.HIGH_FATIGUE.value,
                        'date': row['workout_date'].strftime('%Y-%m-%d'),
                        'severity': 'medium',
                        'message': "High effort but declining performance - possible fatigue",
                        'details': {
                            'rpe': row['avg_rpe'],
                            'performance_change': f"{row['performance_trend']*100:.1f}%"
                        }
                    })
        
        # Check perceived exertion trends
        if 'perceived_exertion' in df.columns:
            recent = df.tail(3)
            if len(recent) >= 3 and recent['perceived_exertion'].notna().all():
                if (recent['perceived_exertion'] >= 8).all():
                    anomalies.append({
                        'type': AnomalyType.HIGH_FATIGUE.value,
                        'date': recent.iloc[-1]['workout_date'].strftime('%Y-%m-%d'),
                        'severity': 'high',
                        'message': "3 consecutive high-exertion workouts - consider a deload",
                        'details': {
                            'recent_exertion': recent['perceived_exertion'].tolist()
                        }
                    })
        
        return anomalies
    
    def _detect_training_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """Detect unusual gaps between workouts"""
        anomalies = []
        
        df['days_gap'] = df['workout_date'].diff().dt.days
        
        mean_gap = df['days_gap'].mean()
        std_gap = df['days_gap'].std()
        
        if pd.isna(mean_gap) or std_gap == 0:
            return anomalies
        
        for idx, row in df.iterrows():
            if pd.isna(row['days_gap']):
                continue
                
            # Flag gaps more than 2x the average
            if row['days_gap'] > max(14, mean_gap + 2 * std_gap):
                anomalies.append({
                    'type': AnomalyType.LONG_GAP.value,
                    'date': row['workout_date'].strftime('%Y-%m-%d'),
                    'severity': 'low',
                    'message': f"Long gap since last workout ({int(row['days_gap'])} days)",
                    'details': {
                        'days_gap': int(row['days_gap']),
                        'average_gap': round(mean_gap, 1)
                    }
                })
        
        return anomalies
    
    def get_health_score(self, df: pd.DataFrame) -> Dict:
        """
        Calculate an overall training health score.
        
        Returns a score from 0-100 based on:
        - Consistency
        - Progressive overload
        - Recovery patterns
        - Fatigue management
        """
        if len(df) < 5:
            return {
                'score': None,
                'message': 'Need at least 5 workouts for health score'
            }
        
        df = df.sort_values('workout_date').copy()
        df['workout_date'] = pd.to_datetime(df['workout_date'])
        
        scores = {}
        
        # Consistency score (0-25): Regular training
        df['days_gap'] = df['workout_date'].diff().dt.days
        avg_gap = df['days_gap'].mean()
        gap_variance = df['days_gap'].var()
        
        # Ideal: 2-4 day gaps with low variance
        if 2 <= avg_gap <= 4:
            consistency = 25
        elif avg_gap < 2:
            consistency = 20  # Training very frequently
        elif avg_gap <= 7:
            consistency = 20 - (avg_gap - 4) * 3
        else:
            consistency = max(0, 15 - (avg_gap - 7))
        
        # Reduce for high variance
        if gap_variance > 10:
            consistency -= min(10, gap_variance / 2)
        
        scores['consistency'] = max(0, round(consistency))
        
        # Progress score (0-25): Are you getting stronger?
        if 'estimated_1rm' in df.columns and not df['estimated_1rm'].isna().all():
            first_half = df.head(len(df)//2)['estimated_1rm'].mean()
            second_half = df.tail(len(df)//2)['estimated_1rm'].mean()
            
            if first_half > 0:
                progress_pct = (second_half - first_half) / first_half * 100
                progress = min(25, max(0, 12.5 + progress_pct * 2))
            else:
                progress = 12.5
        else:
            progress = 12.5
            
        scores['progress'] = round(progress)
        
        # Volume score (0-25): Appropriate training volume
        if 'total_volume' in df.columns:
            volume_trend = df['total_volume'].pct_change().mean()
            volume_consistency = 1 - min(1, df['total_volume'].std() / df['total_volume'].mean())
            
            volume = 12.5 + (volume_trend * 50) + (volume_consistency * 10)
            volume = min(25, max(0, volume))
        else:
            volume = 12.5
            
        scores['volume'] = round(volume)
        
        # Recovery score (0-25): Managing fatigue
        recovery = 25
        
        # Penalize consecutive high-exertion workouts
        if 'perceived_exertion' in df.columns:
            high_exertion_streak = 0
            max_streak = 0
            for _, row in df.iterrows():
                if row.get('perceived_exertion', 0) >= 8:
                    high_exertion_streak += 1
                    max_streak = max(max_streak, high_exertion_streak)
                else:
                    high_exertion_streak = 0
            
            recovery -= max_streak * 3
        
        scores['recovery'] = max(0, round(recovery))
        
        # Calculate total
        total = sum(scores.values())
        
        # Determine rating
        if total >= 80:
            rating = 'Excellent'
        elif total >= 60:
            rating = 'Good'
        elif total >= 40:
            rating = 'Fair'
        else:
            rating = 'Needs Attention'
        
        return {
            'score': total,
            'rating': rating,
            'breakdown': scores,
            'recommendations': self._get_recommendations(scores, df)
        }
    
    def _get_recommendations(self, scores: Dict, df: pd.DataFrame) -> List[str]:
        """Generate recommendations based on scores"""
        recommendations = []
        
        if scores.get('consistency', 25) < 15:
            recommendations.append("Try to maintain more consistent training frequency")
        
        if scores.get('progress', 25) < 10:
            recommendations.append("Consider progressive overload - gradually increase weight or volume")
        
        if scores.get('recovery', 25) < 15:
            recommendations.append("Consider adding deload weeks or reducing intensity periodically")
        
        if scores.get('volume', 25) < 10:
            recommendations.append("Training volume may be inconsistent - try to standardize your workouts")
        
        if not recommendations:
            recommendations.append("Keep up the great work! Your training looks well-balanced.")
        
        return recommendations
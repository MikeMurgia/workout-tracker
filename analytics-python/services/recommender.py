"""
Training Recommendations Service
Provides intelligent workout recommendations

CONCEPTS DEMONSTRATED:
1. Rule-based Systems - Encoding domain knowledge
2. Data-driven Recommendations - Based on user's history
3. Balancing Multiple Factors - Volume, frequency, muscle groups
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict


class TrainingRecommender:
    """
    Generates personalized training recommendations based on:
    - Muscle group balance
    - Training frequency
    - Volume trends
    - Recovery needs
    """
    
    # Target weekly sets per muscle group (evidence-based ranges)
    VOLUME_TARGETS = {
        'chest': {'min': 10, 'max': 20, 'optimal': 14},
        'back': {'min': 10, 'max': 20, 'optimal': 16},
        'shoulders': {'min': 8, 'max': 16, 'optimal': 12},
        'legs': {'min': 12, 'max': 22, 'optimal': 16},
        'arms': {'min': 6, 'max': 14, 'optimal': 10},
        'core': {'min': 4, 'max': 12, 'optimal': 8}
    }
    
    # Minimum days between training same muscle group
    RECOVERY_DAYS = {
        'chest': 2,
        'back': 2,
        'shoulders': 2,
        'legs': 2,
        'arms': 1,
        'core': 1
    }
    
    def __init__(self):
        self.workout_history = None
        self.exercise_catalog = None
    
    def analyze_training_balance(self, 
                                  workouts_df: pd.DataFrame, 
                                  sets_df: pd.DataFrame,
                                  exercises_df: pd.DataFrame,
                                  days: int = 7) -> Dict:
        """
        Analyze muscle group training balance over a period.
        
        Args:
            workouts_df: Workout records
            sets_df: Set records with exercise_id
            exercises_df: Exercise catalog with muscle_group
            days: Number of days to analyze
            
        Returns:
            Analysis of training balance
        """
        # Filter to recent workouts
        cutoff_date = datetime.now() - timedelta(days=days)
        
        workouts_df['workout_date'] = pd.to_datetime(workouts_df['workout_date'])
        recent_workouts = workouts_df[workouts_df['workout_date'] >= cutoff_date]
        
        if len(recent_workouts) == 0:
            return {
                'status': 'no_data',
                'message': f'No workouts in the last {days} days'
            }
        
        # Join sets with exercises to get muscle groups
        recent_workout_ids = recent_workouts['id'].tolist()
        recent_sets = sets_df[sets_df['workout_id'].isin(recent_workout_ids)]
        
        # Merge with exercises
        sets_with_muscles = recent_sets.merge(
            exercises_df[['id', 'muscle_group', 'name']], 
            left_on='exercise_id', 
            right_on='id',
            suffixes=('', '_exercise')
        )
        
        # Count sets per muscle group (only working sets)
        working_sets = sets_with_muscles[sets_with_muscles['set_type'] == 'working']
        muscle_group_counts = working_sets.groupby('muscle_group').size().to_dict()
        
        # Calculate volume (weight x reps)
        muscle_group_volume = working_sets.groupby('muscle_group').apply(
            lambda x: (x['weight'].fillna(0) * x['reps']).sum()
        ).to_dict()
        
        # Analyze each muscle group
        analysis = {}
        for muscle, targets in self.VOLUME_TARGETS.items():
            sets = muscle_group_counts.get(muscle, 0)
            volume = muscle_group_volume.get(muscle, 0)
            
            # Determine status
            if sets < targets['min']:
                status = 'undertrained'
                recommendation = f"Add {targets['min'] - sets} more sets"
            elif sets > targets['max']:
                status = 'overtrained'
                recommendation = f"Consider reducing by {sets - targets['max']} sets"
            else:
                status = 'optimal'
                recommendation = "Volume is good"
            
            analysis[muscle] = {
                'sets': sets,
                'volume': round(volume, 0),
                'target_range': f"{targets['min']}-{targets['max']}",
                'status': status,
                'recommendation': recommendation
            }
        
        # Find most and least trained
        sorted_muscles = sorted(analysis.items(), key=lambda x: x[1]['sets'], reverse=True)
        
        return {
            'period_days': days,
            'total_workouts': len(recent_workouts),
            'muscle_groups': analysis,
            'most_trained': sorted_muscles[0][0] if sorted_muscles else None,
            'least_trained': sorted_muscles[-1][0] if sorted_muscles else None,
            'overall_balance': self._calculate_balance_score(analysis)
        }
    
    def _calculate_balance_score(self, analysis: Dict) -> Dict:
        """Calculate overall training balance score"""
        total_score = 0
        max_score = len(analysis) * 100
        
        for muscle, data in analysis.items():
            targets = self.VOLUME_TARGETS.get(muscle, {'min': 8, 'max': 16, 'optimal': 12})
            sets = data['sets']
            
            if targets['min'] <= sets <= targets['max']:
                # Score based on how close to optimal
                distance_from_optimal = abs(sets - targets['optimal'])
                max_distance = max(targets['optimal'] - targets['min'], 
                                  targets['max'] - targets['optimal'])
                if max_distance > 0:
                    score = 100 - (distance_from_optimal / max_distance * 30)
                else:
                    score = 100
            elif sets < targets['min']:
                # Below minimum
                score = max(0, 50 * (sets / targets['min']))
            else:
                # Above maximum
                score = max(0, 70 - (sets - targets['max']) * 5)
            
            total_score += score
        
        final_score = round(total_score / max_score * 100) if max_score > 0 else 0
        
        if final_score >= 80:
            rating = 'Excellent'
        elif final_score >= 60:
            rating = 'Good'
        elif final_score >= 40:
            rating = 'Fair'
        else:
            rating = 'Needs Work'
        
        return {
            'score': final_score,
            'rating': rating
        }
    
    def get_next_workout_recommendation(self,
                                         workouts_df: pd.DataFrame,
                                         sets_df: pd.DataFrame,
                                         exercises_df: pd.DataFrame) -> Dict:
        """
        Recommend what to train in the next workout.
        
        Based on:
        - What was trained recently
        - What hasn't been trained
        - Recovery time needed
        """
        # Get training balance
        balance = self.analyze_training_balance(workouts_df, sets_df, exercises_df, days=7)
        
        if balance.get('status') == 'no_data':
            # No recent workouts - recommend a balanced full body
            return {
                'recommendation': 'full_body',
                'reason': 'Starting fresh after a break',
                'suggested_muscles': ['chest', 'back', 'legs', 'shoulders'],
                'exercises': self._get_exercise_suggestions(exercises_df, 
                                                           ['chest', 'back', 'legs', 'shoulders'])
            }
        
        # Find undertrained muscles
        undertrained = [
            muscle for muscle, data in balance['muscle_groups'].items()
            if data['status'] == 'undertrained'
        ]
        
        # Check what was trained most recently
        workouts_df['workout_date'] = pd.to_datetime(workouts_df['workout_date'])
        last_workout = workouts_df.sort_values('workout_date').iloc[-1]
        last_workout_sets = sets_df[sets_df['workout_id'] == last_workout['id']]
        
        # Get muscles trained in last workout
        last_muscles = last_workout_sets.merge(
            exercises_df[['id', 'muscle_group']], 
            left_on='exercise_id', 
            right_on='id'
        )['muscle_group'].unique().tolist()
        
        # Calculate days since each muscle was trained
        days_since_trained = self._get_days_since_trained(workouts_df, sets_df, exercises_df)
        
        # Prioritize muscles that:
        # 1. Are undertrained
        # 2. Haven't been trained recently enough for recovery
        priority_muscles = []
        
        for muscle in undertrained:
            days_rest = days_since_trained.get(muscle, 999)
            min_rest = self.RECOVERY_DAYS.get(muscle, 2)
            
            if days_rest >= min_rest:
                priority_muscles.append({
                    'muscle': muscle,
                    'priority': 'high',
                    'reason': f'Undertrained and {days_rest} days rest'
                })
        
        # If no undertrained muscles need work, suggest based on recovery
        if not priority_muscles:
            for muscle, days in days_since_trained.items():
                min_rest = self.RECOVERY_DAYS.get(muscle, 2)
                if days >= min_rest and muscle not in last_muscles:
                    priority_muscles.append({
                        'muscle': muscle,
                        'priority': 'medium',
                        'reason': f'Fully recovered ({days} days rest)'
                    })
        
        # Generate recommendation
        if priority_muscles:
            suggested_muscles = [p['muscle'] for p in priority_muscles[:3]]
            
            return {
                'recommendation': 'targeted',
                'focus_muscles': priority_muscles[:3],
                'suggested_muscles': suggested_muscles,
                'exercises': self._get_exercise_suggestions(exercises_df, suggested_muscles),
                'avoid': last_muscles if len(last_muscles) > 0 else None,
                'reason': 'Based on training balance and recovery'
            }
        else:
            # Everything is balanced, suggest rest or light work
            return {
                'recommendation': 'rest_or_light',
                'reason': 'All muscle groups recently trained - consider rest day',
                'alternative': 'Light cardio, stretching, or mobility work'
            }
    
    def _get_days_since_trained(self, 
                                 workouts_df: pd.DataFrame,
                                 sets_df: pd.DataFrame,
                                 exercises_df: pd.DataFrame) -> Dict[str, int]:
        """Calculate days since each muscle group was trained"""
        today = datetime.now()
        days_since = {}
        
        # Join all data
        merged = sets_df.merge(
            workouts_df[['id', 'workout_date']], 
            left_on='workout_id', 
            right_on='id',
            suffixes=('', '_workout')
        ).merge(
            exercises_df[['id', 'muscle_group']], 
            left_on='exercise_id', 
            right_on='id',
            suffixes=('', '_exercise')
        )
        
        merged['workout_date'] = pd.to_datetime(merged['workout_date'])
        
        # Find most recent date for each muscle group
        for muscle in self.VOLUME_TARGETS.keys():
            muscle_data = merged[merged['muscle_group'] == muscle]
            
            if len(muscle_data) > 0:
                last_trained = muscle_data['workout_date'].max()
                days_since[muscle] = (today - last_trained).days
            else:
                days_since[muscle] = 999  # Never trained
        
        return days_since
    
    def _get_exercise_suggestions(self, 
                                   exercises_df: pd.DataFrame,
                                   muscle_groups: List[str],
                                   exercises_per_muscle: int = 2) -> List[Dict]:
        """Get exercise suggestions for given muscle groups"""
        suggestions = []
        
        for muscle in muscle_groups:
            muscle_exercises = exercises_df[exercises_df['muscle_group'] == muscle]
            
            # Prioritize compound movements
            compounds = muscle_exercises[muscle_exercises['is_compound'] == True]
            isolations = muscle_exercises[muscle_exercises['is_compound'] == False]
            
            # Take 1 compound and 1 isolation if possible
            selected = []
            
            if len(compounds) > 0:
                selected.append(compounds.sample(1).iloc[0])
            
            if len(isolations) > 0 and len(selected) < exercises_per_muscle:
                selected.append(isolations.sample(1).iloc[0])
            
            # Fill with any remaining
            remaining = exercises_per_muscle - len(selected)
            if remaining > 0:
                available = muscle_exercises[~muscle_exercises['id'].isin([s['id'] for s in selected])]
                if len(available) > 0:
                    additional = available.sample(min(remaining, len(available)))
                    selected.extend(additional.to_dict('records'))
            
            for exercise in selected:
                if isinstance(exercise, pd.Series):
                    exercise = exercise.to_dict()
                suggestions.append({
                    'exercise_id': exercise['id'],
                    'name': exercise['name'],
                    'muscle_group': muscle,
                    'equipment': exercise.get('equipment'),
                    'is_compound': exercise.get('is_compound', False)
                })
        
        return suggestions
    
    def suggest_deload(self, 
                       workouts_df: pd.DataFrame,
                       sets_df: pd.DataFrame) -> Dict:
        """
        Determine if a deload week is needed.
        
        Deload indicators:
        - 4+ weeks of consistent training
        - Increasing RPE/perceived exertion
        - Plateau in progress
        """
        if len(workouts_df) < 8:
            return {
                'needs_deload': False,
                'reason': 'Not enough training history'
            }
        
        workouts_df = workouts_df.sort_values('workout_date').copy()
        workouts_df['workout_date'] = pd.to_datetime(workouts_df['workout_date'])
        
        # Check training streak
        recent = workouts_df.tail(12)
        date_range = (recent['workout_date'].max() - recent['workout_date'].min()).days
        
        if date_range < 21:  # Less than 3 weeks of data
            return {
                'needs_deload': False,
                'reason': 'Training period too short for deload'
            }
        
        # Check for increasing perceived exertion
        if 'perceived_exertion' in recent.columns:
            exertion_trend = recent['perceived_exertion'].dropna()
            if len(exertion_trend) >= 4:
                first_half = exertion_trend.head(len(exertion_trend)//2).mean()
                second_half = exertion_trend.tail(len(exertion_trend)//2).mean()
                
                if second_half > first_half + 1:  # Exertion increasing by more than 1
                    return {
                        'needs_deload': True,
                        'reason': 'Perceived exertion increasing - signs of accumulated fatigue',
                        'suggestion': 'Reduce weights by 40-50% and volume by 50% for 1 week'
                    }
        
        # Check weeks since last deload/break
        gaps = workouts_df['workout_date'].diff().dt.days
        long_breaks = gaps[gaps >= 7].index
        
        if len(long_breaks) > 0:
            last_break_idx = long_breaks[-1]
            workouts_since_break = len(workouts_df) - last_break_idx
        else:
            workouts_since_break = len(workouts_df)
        
        if workouts_since_break >= 16:  # ~4 weeks of training 4x/week
            return {
                'needs_deload': True,
                'reason': f'{workouts_since_break} workouts since last break',
                'suggestion': 'Schedule a deload week: reduce intensity by 40%, volume by 50%'
            }
        
        return {
            'needs_deload': False,
            'workouts_until_deload': 16 - workouts_since_break,
            'suggestion': 'Continue training as normal'
        }
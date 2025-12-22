"""
Test Data Generator for Workout Tracker
Populates the database with realistic sample workout data

Run with: python seed_test_data.py
"""

import os
import sys
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

# Database connection
def get_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'workout_tracker'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )

def clear_existing_data(conn):
    """Clear existing workout data (but keep exercises)"""
    with conn.cursor() as cur:
        print("Clearing existing workout data...")
        cur.execute("DELETE FROM personal_records")
        cur.execute("DELETE FROM workout_sets")
        cur.execute("DELETE FROM workouts")
        cur.execute("DELETE FROM goals")
        cur.execute("DELETE FROM body_weight_log")
        conn.commit()
        print("✓ Existing data cleared")

def get_exercises(conn):
    """Get all exercises from database"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, name, muscle_group, is_compound FROM exercises")
        return cur.fetchall()

def generate_workouts(conn, exercises, num_weeks=12):
    """
    Generate realistic workout data over a period of weeks.
    
    Simulates a Push/Pull/Legs split with progressive overload.
    """
    
    # Organize exercises by muscle group
    exercises_by_group = {}
    for ex in exercises:
        group = ex['muscle_group']
        if group not in exercises_by_group:
            exercises_by_group[group] = []
        exercises_by_group[group].append(ex)
    
    # Define workout splits
    push_muscles = ['chest', 'shoulders', 'arms']  # triceps are in arms
    pull_muscles = ['back', 'arms']  # biceps are in arms
    leg_muscles = ['legs', 'core']
    
    # Starting weights for key exercises (will progressively increase)
    starting_weights = {
        'Barbell Bench Press': 135,
        'Incline Dumbbell Press': 50,
        'Overhead Press': 95,
        'Barbell Squat': 185,
        'Deadlift': 225,
        'Barbell Row': 135,
        'Romanian Deadlift': 155,
        'Leg Press': 270,
        'Lat Pulldown': 120,
        'Dumbbell Curl': 30,
        'Tricep Pushdown': 50,
    }
    
    # Track current weights (for progressive overload)
    current_weights = starting_weights.copy()
    
    # Generate workouts
    start_date = datetime.now() - timedelta(weeks=num_weeks)
    workouts_created = 0
    sets_created = 0
    
    with conn.cursor() as cur:
        current_date = start_date
        
        while current_date <= datetime.now():
            day_of_week = current_date.weekday()
            
            # Workout schedule: Mon=Push, Tue=Pull, Wed=Rest, Thu=Legs, Fri=Push, Sat=Pull, Sun=Rest
            workout_type = None
            if day_of_week == 0:  # Monday
                workout_type = ('Push Day', push_muscles)
            elif day_of_week == 1:  # Tuesday
                workout_type = ('Pull Day', pull_muscles)
            elif day_of_week == 3:  # Thursday
                workout_type = ('Leg Day', leg_muscles)
            elif day_of_week == 4:  # Friday
                workout_type = ('Push Day', push_muscles)
            elif day_of_week == 5:  # Saturday
                workout_type = ('Pull Day', pull_muscles)
            
            if workout_type:
                workout_name, muscle_groups = workout_type
                
                # Random chance to skip a workout (life happens)
                if random.random() < 0.1:  # 10% chance to skip
                    current_date += timedelta(days=1)
                    continue
                
                # Create workout
                perceived_exertion = random.randint(5, 9)
                
                cur.execute("""
                    INSERT INTO workouts (workout_date, name, perceived_exertion)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (current_date.date(), workout_name, perceived_exertion))
                
                workout_id = cur.fetchone()[0]
                workouts_created += 1
                
                # Select exercises for this workout
                workout_exercises = []
                for muscle in muscle_groups:
                    if muscle in exercises_by_group:
                        # Pick 1-2 exercises per muscle group
                        available = exercises_by_group[muscle]
                        num_exercises = min(2, len(available))
                        selected = random.sample(available, num_exercises)
                        workout_exercises.extend(selected)
                
                # Add sets for each exercise
                for exercise in workout_exercises:
                    ex_name = exercise['name']
                    ex_id = exercise['id']
                    is_compound = exercise['is_compound']
                    
                    # Determine weight
                    if ex_name in current_weights:
                        base_weight = current_weights[ex_name]
                    else:
                        # Generate a reasonable weight for unknown exercises
                        base_weight = random.randint(20, 100)
                    
                    # Number of sets (compounds get more)
                    num_sets = random.randint(3, 4) if is_compound else random.randint(2, 3)
                    
                    for set_num in range(1, num_sets + 1):
                        # Weight varies slightly per set
                        if set_num == 1:
                            weight = base_weight * 0.7  # Warmup-ish
                            reps = random.randint(10, 12)
                            set_type = 'warmup' if random.random() < 0.3 else 'working'
                        elif set_num == num_sets:
                            weight = base_weight * random.uniform(1.0, 1.1)  # Heavy
                            reps = random.randint(4, 6)
                            set_type = 'working'
                        else:
                            weight = base_weight * random.uniform(0.9, 1.0)
                            reps = random.randint(6, 10)
                            set_type = 'working'
                        
                        # RPE correlates with difficulty (must be between 6 and 10 per database constraint)
                        rpe = random.uniform(7.0, 9.5) if set_type == 'working' else random.uniform(6.0, 7.0)
                        
                        cur.execute("""
                            INSERT INTO workout_sets 
                            (workout_id, exercise_id, set_number, weight, reps, set_type, rpe)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (workout_id, ex_id, set_num, round(weight, 1), reps, set_type, round(rpe, 1)))
                        
                        sets_created += 1
                
                # Progressive overload: increase weights slightly each week
                if day_of_week == 5:  # End of week (Saturday)
                    for ex_name in current_weights:
                        # 1-2% increase per week (realistic progression)
                        increase = random.uniform(1.01, 1.025)
                        current_weights[ex_name] = round(current_weights[ex_name] * increase, 1)
            
            current_date += timedelta(days=1)
        
        conn.commit()
    
    return workouts_created, sets_created

def generate_body_weight_log(conn, num_weeks=12):
    """Generate body weight entries"""
    start_date = datetime.now() - timedelta(weeks=num_weeks)
    start_weight = random.uniform(170, 190)
    
    entries = 0
    with conn.cursor() as cur:
        current_date = start_date
        current_weight = start_weight
        
        while current_date <= datetime.now():
            # Log weight every 2-3 days
            if random.random() < 0.4:
                # Weight fluctuates day to day
                daily_fluctuation = random.uniform(-1.5, 1.5)
                # Slight upward trend (building muscle)
                trend = 0.02
                current_weight = current_weight + daily_fluctuation + trend
                
                cur.execute("""
                    INSERT INTO body_weight_log (log_date, weight)
                    VALUES (%s, %s)
                    ON CONFLICT (log_date) DO NOTHING
                """, (current_date.date(), round(current_weight, 1)))
                entries += 1
            
            current_date += timedelta(days=1)
        
        conn.commit()
    
    return entries

def generate_personal_records(conn):
    """Generate personal records based on workout data"""
    with conn.cursor() as cur:
        # Find max weights for each exercise
        cur.execute("""
            INSERT INTO personal_records (exercise_id, workout_set_id, record_type, record_value, record_date, is_current)
            SELECT DISTINCT ON (ws.exercise_id)
                ws.exercise_id,
                ws.id as workout_set_id,
                'weight' as record_type,
                ws.weight as record_value,
                w.workout_date as record_date,
                true as is_current
            FROM workout_sets ws
            JOIN workouts w ON ws.workout_id = w.id
            WHERE ws.weight IS NOT NULL
            ORDER BY ws.exercise_id, ws.weight DESC
        """)
        
        conn.commit()
        
        cur.execute("SELECT COUNT(*) FROM personal_records")
        return cur.fetchone()[0]

def print_summary(conn):
    """Print summary of generated data"""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM workouts")
        workouts = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM workout_sets")
        sets = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM personal_records")
        prs = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM body_weight_log")
        weight_logs = cur.fetchone()[0]
        
        cur.execute("""
            SELECT e.name, COUNT(*) as set_count, MAX(ws.weight) as max_weight
            FROM workout_sets ws
            JOIN exercises e ON ws.exercise_id = e.id
            GROUP BY e.id, e.name
            ORDER BY set_count DESC
            LIMIT 5
        """)
        top_exercises = cur.fetchall()
        
        print("\n" + "="*50)
        print("📊 TEST DATA SUMMARY")
        print("="*50)
        print(f"✓ Workouts created:      {workouts}")
        print(f"✓ Sets logged:           {sets}")
        print(f"✓ Personal records:      {prs}")
        print(f"✓ Body weight entries:   {weight_logs}")
        print("\n🏆 Top 5 Most Trained Exercises:")
        for name, count, max_weight in top_exercises:
            print(f"   • {name}: {count} sets (max: {max_weight} lbs)")
        print("="*50)

def main():
    print("\n🏋️ Workout Tracker - Test Data Generator")
    print("="*50)
    
    # Check for .env file
    if not os.getenv('DB_PASSWORD'):
        print("❌ Error: DB_PASSWORD not found in .env file")
        print("   Make sure you have a .env file with your database credentials")
        sys.exit(1)
    
    try:
        conn = get_connection()
        print("✓ Connected to database")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    try:
        # Ask for confirmation
        print("\n⚠️  This will DELETE existing workout data and create new test data.")
        response = input("Continue? (y/n): ").strip().lower()
        
        if response != 'y':
            print("Cancelled.")
            sys.exit(0)
        
        # Get exercises
        exercises = get_exercises(conn)
        print(f"✓ Found {len(exercises)} exercises in database")
        
        if len(exercises) == 0:
            print("❌ No exercises found! Run the schema.sql file first.")
            sys.exit(1)
        
        # Clear and generate
        clear_existing_data(conn)
        
        print("\nGenerating 12 weeks of workout data...")
        workouts, sets = generate_workouts(conn, exercises, num_weeks=12)
        print(f"✓ Created {workouts} workouts with {sets} sets")
        
        print("Generating body weight log...")
        weight_entries = generate_body_weight_log(conn, num_weeks=12)
        print(f"✓ Created {weight_entries} body weight entries")
        
        print("Generating personal records...")
        prs = generate_personal_records(conn)
        print(f"✓ Created {prs} personal records")
        
        # Print summary
        print_summary(conn)
        
        print("\n✅ Test data generated successfully!")
        print("\nYou can now test:")
        print("  • http://localhost:8000/docs (Swagger UI)")
        print("  • http://localhost:8000/predictions/strength/{exercise_id}")
        print("  • http://localhost:8000/analysis/health")
        print("  • http://localhost:8000/recommendations/next-workout")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
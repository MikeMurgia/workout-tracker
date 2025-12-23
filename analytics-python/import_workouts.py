"""
Workout Notes Importer
Parses iPhone Notes workout data and imports into PostgreSQL database

Usage:
    python import_workouts.py workouts.txt
"""

import re
import sys
import os
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

# ============================================
# Exercise Name Mapping & Muscle Group Detection
# ============================================
# Maps your note exercise names to standardized names

EXERCISE_MAPPING = {
    # Chest
    'bench': 'Barbell Bench Press',
    'bench press': 'Barbell Bench Press',
    'flat bench': 'Barbell Bench Press',
    'incline bench': 'Incline Dumbbell Press',
    'incline': 'Incline Dumbbell Press',
    'incline press': 'Incline Dumbbell Press',
    'chest press machine': 'Chest Press Machine',
    'chest press': 'Chest Press Machine',
    'cable flys': 'Cable Flys',
    'cable fly': 'Cable Flys',
    'cable flies': 'Cable Flys',
    'flys': 'Cable Flys',
    'flies': 'Cable Flys',
    'pec deck': 'Pec Deck',
    'dumbbell press': 'Dumbbell Bench Press',
    'db press': 'Dumbbell Bench Press',
    'push ups': 'Push Ups',
    'pushups': 'Push Ups',
    'dips': 'Dips',
    
    # Back
    'lat pulldowns': 'Lat Pulldown',
    'lat pulldown': 'Lat Pulldown',
    'pulldowns': 'Lat Pulldown',
    'front pulldown machine': 'Lat Pulldown',
    'front pulldown': 'Lat Pulldown',
    'barbell rows': 'Barbell Row',
    'barbell row': 'Barbell Row',
    'bent over rows': 'Barbell Row',
    'bent over row': 'Barbell Row',
    'rows': 'Barbell Row',
    'low rows': 'Seated Cable Row',
    'low row': 'Seated Cable Row',
    'cable rows': 'Seated Cable Row',
    'cable row': 'Seated Cable Row',
    'seated rows': 'Seated Cable Row',
    'seated row': 'Seated Cable Row',
    'seated cable row': 'Seated Cable Row',
    't-bar row': 'T-Bar Row',
    't bar row': 'T-Bar Row',
    'deadlift': 'Deadlift',
    'deadlifts': 'Deadlift',
    'pull ups': 'Pull Ups',
    'pullups': 'Pull Ups',
    'chin ups': 'Pull Ups',
    'chinups': 'Pull Ups',
    
    # Shoulders
    'shoulder press': 'Overhead Press',
    'shoulder press machine': 'Shoulder Press Machine',
    'overhead press': 'Overhead Press',
    'ohp': 'Overhead Press',
    'military press': 'Overhead Press',
    'lateral raise': 'Lateral Raise',
    'lateral raises': 'Lateral Raise',
    'lat raise': 'Lateral Raise',
    'side raises': 'Lateral Raise',
    'side raise': 'Lateral Raise',
    'front raise': 'Front Raise',
    'front raises': 'Front Raise',
    'rear delt': 'Rear Delt Fly',
    'rear delts': 'Rear Delt Fly',
    'face pulls': 'Face Pulls',
    'face pull': 'Face Pulls',
    'shrugs': 'Shrugs',
    'shrug': 'Shrugs',
    
    # Legs
    'squat': 'Barbell Squat',
    'squats': 'Barbell Squat',
    'back squat': 'Barbell Squat',
    'front squat': 'Barbell Squat',
    'leg press': 'Leg Press',
    'leg extensions': 'Leg Extension',
    'leg extension': 'Leg Extension',
    'leg curls': 'Leg Curl',
    'leg curl': 'Leg Curl',
    'hamstring curls': 'Leg Curl',
    'hamstring curl': 'Leg Curl',
    'romanian deadlift': 'Romanian Deadlift',
    'rdl': 'Romanian Deadlift',
    'rdls': 'Romanian Deadlift',
    'lunges': 'Lunges',
    'lunge': 'Lunges',
    'calf raises': 'Calf Raise',
    'calf raise': 'Calf Raise',
    'calves': 'Calf Raise',
    'hip thrust': 'Hip Thrust',
    'hip thrusts': 'Hip Thrust',
    
    # Arms - Biceps
    'bicep curls': 'Dumbbell Curl',
    'bicep curl': 'Dumbbell Curl',
    'curls': 'Dumbbell Curl',
    'dumbbell curls': 'Dumbbell Curl',
    'dumbbell curl': 'Dumbbell Curl',
    'hammer curls': 'Hammer Curl',
    'hammer curl': 'Hammer Curl',
    'preacher curls': 'Preacher Curl',
    'preacher curl': 'Preacher Curl',
    'barbell curls': 'Barbell Curl',
    'barbell curl': 'Barbell Curl',
    'ez bar curls': 'Barbell Curl',
    'ez bar curl': 'Barbell Curl',
    'cable curls': 'Cable Curl',
    'cable curl': 'Cable Curl',
    'concentration curls': 'Concentration Curl',
    'concentration curl': 'Concentration Curl',
    
    # Arms - Triceps
    'tricep extensions': 'Tricep Pushdown',
    'tricep extension': 'Tricep Pushdown',
    'tricep pushdowns': 'Tricep Pushdown',
    'tricep pushdown': 'Tricep Pushdown',
    'triceps pushdown': 'Tricep Pushdown',
    'pushdowns': 'Tricep Pushdown',
    'pushdown': 'Tricep Pushdown',
    'skull crushers': 'Skull Crushers',
    'skullcrushers': 'Skull Crushers',
    'skull crusher': 'Skull Crushers',
    'overhead tricep': 'Overhead Tricep Extension',
    'tricep overhead': 'Overhead Tricep Extension',
    'overhead tricep extension': 'Overhead Tricep Extension',
    'rope pushdown': 'Tricep Pushdown',
    'rope pushdowns': 'Tricep Pushdown',
    'close grip bench': 'Close Grip Bench Press',
    
    # Core
    'plank': 'Plank',
    'planks': 'Plank',
    'crunches': 'Crunches',
    'crunch': 'Crunches',
    'sit ups': 'Crunches',
    'situps': 'Crunches',
    'leg raises': 'Hanging Leg Raise',
    'hanging leg raises': 'Hanging Leg Raise',
    'hanging leg raise': 'Hanging Leg Raise',
    'ab wheel': 'Ab Wheel',
    'cable crunch': 'Cable Crunch',
    'cable crunches': 'Cable Crunch',
    'russian twist': 'Russian Twist',
    'russian twists': 'Russian Twist',
}

# Keywords to detect muscle group from exercise name
MUSCLE_GROUP_KEYWORDS = {
    'chest': ['bench', 'chest', 'pec', 'fly', 'flys', 'flies', 'push up', 'pushup', 'dip'],
    'back': ['row', 'pulldown', 'pull down', 'lat ', 'deadlift', 'pull up', 'pullup', 'chin'],
    'shoulders': ['shoulder', 'lateral', 'raise', 'shrug', 'delt', 'press machine', 'ohp', 'military'],
    'legs': ['squat', 'leg', 'lunge', 'calf', 'hip thrust', 'rdl', 'hamstring', 'quad', 'glute'],
    'arms': ['curl', 'bicep', 'tricep', 'hammer', 'pushdown', 'extension', 'skull'],
    'core': ['ab', 'crunch', 'plank', 'twist', 'core'],
}

def guess_muscle_group(exercise_name: str) -> str:
    """Guess the muscle group based on exercise name keywords"""
    name_lower = exercise_name.lower()
    
    for muscle_group, keywords in MUSCLE_GROUP_KEYWORDS.items():
        for keyword in keywords:
            if keyword in name_lower:
                return muscle_group
    
    return 'other'

def guess_equipment(exercise_name: str) -> str:
    """Guess equipment based on exercise name"""
    name_lower = exercise_name.lower()
    
    if 'barbell' in name_lower or 'bar ' in name_lower:
        return 'barbell'
    elif 'dumbbell' in name_lower or 'db ' in name_lower:
        return 'dumbbell'
    elif 'cable' in name_lower:
        return 'cable'
    elif 'machine' in name_lower:
        return 'machine'
    elif 'bodyweight' in name_lower or 'push up' in name_lower or 'pull up' in name_lower:
        return 'bodyweight'
    else:
        return 'other'

def is_compound(exercise_name: str) -> bool:
    """Guess if exercise is compound based on name"""
    compound_keywords = ['squat', 'deadlift', 'bench', 'row', 'press', 'pull up', 'dip', 'lunge']
    name_lower = exercise_name.lower()
    
    for keyword in compound_keywords:
        if keyword in name_lower:
            return True
    return False

# ============================================
# Database Connection
# ============================================
def get_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'workout_tracker'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )

def get_exercises(conn) -> Dict[str, dict]:
    """Load all exercises from database"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, name, muscle_group FROM exercises")
        exercises = cur.fetchall()
        return {ex['name'].lower(): dict(ex) for ex in exercises}

def add_exercise_to_db(conn, name: str) -> dict:
    """Add a new exercise to the database"""
    muscle_group = guess_muscle_group(name)
    equipment = guess_equipment(name)
    compound = is_compound(name)
    
    # Title case the name
    display_name = name.title()
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            INSERT INTO exercises (name, muscle_group, equipment, is_compound)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, muscle_group
        """, (display_name, muscle_group, equipment, compound))
        
        exercise = dict(cur.fetchone())
        conn.commit()
        
    return exercise

# ============================================
# Parsing Functions
# ============================================
def parse_date(date_str: str, default_year: int = 2023) -> Optional[datetime]:
    """Parse date from various formats"""
    date_str = date_str.strip()
    
    formats = [
        '%m/%d/%y',
        '%m/%d/%Y',
        '%m/%d',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if fmt == '%m/%d':
                dt = dt.replace(year=default_year)
            return dt
        except ValueError:
            continue
    
    return None

def extract_date_from_title(title: str) -> Tuple[str, Optional[datetime]]:
    """Extract date from workout title"""
    
    # First try: date with slashes (e.g., 10/22/25 or 8/28/23 or 1/5)
    date_pattern = r'(\d{1,2}/\d{1,2}(?:/\d{2,4})?)'
    match = re.search(date_pattern, title)
    
    if match:
        date_str = match.group(1)
        workout_date = parse_date(date_str)
        workout_name = re.sub(r'\d{1,2}/\d{1,2}(?:/\d{2,4})?\s*(?:\([^)]*\))?\s*$', '', title).strip()
        return workout_name, workout_date
    
    # Second try: date without slashes like 71823 (MDDYY) or 101523 (MMDDYY)
    no_slash_pattern = r'(\d{5,6})\s*(?:\([^)]*\))?\s*$'
    match = re.search(no_slash_pattern, title)
    
    if match:
        date_digits = match.group(1)
        try:
            if len(date_digits) == 5:
                month = int(date_digits[0])
                day = int(date_digits[1:3])
                year = int('20' + date_digits[3:5])
            elif len(date_digits) == 6:
                month = int(date_digits[0:2])
                day = int(date_digits[2:4])
                year = int('20' + date_digits[4:6])
            else:
                return title, None
            
            workout_date = datetime(year, month, day)
            workout_name = re.sub(no_slash_pattern, '', title).strip()
            return workout_name, workout_date
        except ValueError:
            pass
    
    return title, None

def parse_sets_line(line: str) -> List[Dict]:
    """
    Parse a sets line like:
    - 225 lbs 1, 205 lbs 4, 185 lbs 6
    - 120 lbs 9, 9, 6
    - 17.5 kgs 8, 9, 10
    - 50 lbs 9, 57.5 lbs 8, 7
    - 22.5 lbs 7, 17.5 8, 6
    - 30 lbs running the rack 6, 5, 4, 25 lbs 6.5, 7
    """
    sets = []
    
    line = line.strip()
    line = re.sub(r'^[\s\-–•]+', '', line).strip()
    
    if not line:
        return sets
    
    # Skip plate notation
    if 'plate' in line.lower():
        return []
    
    # Clean up special phrases
    line = re.sub(r'running the rack', ',', line, flags=re.IGNORECASE)
    line = re.sub(r'drop set', ',', line, flags=re.IGNORECASE)
    
    # Ensure space before units
    line = re.sub(r'(\d)(lbs|kgs)', r'\1 \2', line, flags=re.IGNORECASE)
    
    current_weight = None
    current_unit = 'lbs'
    
    parts = [p.strip() for p in line.split(',')]
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Pattern: [weight] [unit] [reps] e.g., "225 lbs 1" or "57.5 lbs 8"
        full_match = re.match(r'([\d.]+)\s*(lbs?|kgs?)?\s+([\d.]+)', part, re.IGNORECASE)
        
        if full_match:
            weight = float(full_match.group(1))
            unit = full_match.group(2)
            reps = float(full_match.group(3))
            
            if unit:
                current_unit = unit.lower()
            
            if current_unit.startswith('kg'):
                weight = round(weight * 2.205, 1)
            
            current_weight = weight
            
            sets.append({
                'weight': current_weight,
                'reps': int(reps) if reps == int(reps) else reps
            })
        
        # Pattern: [weight] [reps] (no unit) e.g., "17.5 8"
        elif re.match(r'^([\d.]+)\s+([\d.]+)$', part):
            match = re.match(r'^([\d.]+)\s+([\d.]+)$', part)
            weight = float(match.group(1))
            reps = float(match.group(2))
            
            if current_unit.startswith('kg'):
                weight = round(weight * 2.205, 1)
            
            current_weight = weight
            
            sets.append({
                'weight': current_weight,
                'reps': int(reps) if reps == int(reps) else reps
            })
        
        # Just a number (reps only)
        elif re.match(r'^[\d.]+$', part):
            try:
                reps = float(part)
                if current_weight is not None:
                    sets.append({
                        'weight': current_weight,
                        'reps': int(reps) if reps == int(reps) else reps
                    })
            except ValueError:
                continue
    
    return sets

def parse_workout_block(lines: List[str]) -> Optional[Dict]:
    """Parse a workout block into structured data"""
    if not lines:
        return None
    
    title = lines[0].strip()
    workout_name, workout_date = extract_date_from_title(title)
    
    if not workout_date:
        return None
    
    exercises = []
    current_exercise = None
    
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        
        # If line starts with a number, it's a sets line
        if re.match(r'^[\d.]', line):
            if current_exercise:
                sets = parse_sets_line(line)
                if sets:
                    exercises.append({
                        'name': current_exercise,
                        'sets': sets
                    })
                current_exercise = None
        else:
            # It's an exercise name
            current_exercise = line
    
    if not exercises:
        return None
    
    return {
        'name': workout_name,
        'date': workout_date,
        'exercises': exercises
    }

def parse_notes_file(content: str) -> List[Dict]:
    """Parse entire notes file into list of workouts"""
    workouts = []
    current_block = []
    
    lines = content.split('\n')
    
    for line in lines:
        stripped = line.strip()
        
        # Check if this is a new workout title
        is_title = bool(re.search(r'\d{1,2}/\d{1,2}', stripped)) or bool(re.search(r'\d{5,6}\s*(?:\([^)]*\))?\s*$', stripped))
        is_sets_line = bool(re.match(r'^[\d.\-–]', stripped))
        
        if is_title and not is_sets_line and stripped:
            if current_block:
                workout = parse_workout_block(current_block)
                if workout:
                    workouts.append(workout)
            current_block = [stripped]
        elif stripped:
            current_block.append(stripped)
    
    # Last block
    if current_block:
        workout = parse_workout_block(current_block)
        if workout:
            workouts.append(workout)
    
    return workouts

def map_exercise_name(name: str, db_exercises: Dict) -> Optional[dict]:
    """Map a note exercise name to a database exercise"""
    name_lower = name.lower().strip()
    
    # Direct match in mapping
    if name_lower in EXERCISE_MAPPING:
        mapped_name = EXERCISE_MAPPING[name_lower].lower()
        if mapped_name in db_exercises:
            return db_exercises[mapped_name]
    
    # Direct match in database
    if name_lower in db_exercises:
        return db_exercises[name_lower]
    
    # Partial match
    for db_name, exercise in db_exercises.items():
        if db_name in name_lower or name_lower in db_name:
            return exercise
    
    return None

# ============================================
# Import Functions
# ============================================
def import_workout(conn, workout: Dict, db_exercises: Dict, auto_add: bool = True) -> Tuple[int, int, List[str], List[str]]:
    """Import a single workout into the database"""
    sets_imported = 0
    exercises_imported = 0
    warnings = []
    new_exercises = []
    
    with conn.cursor() as cur:
        # Create workout
        cur.execute("""
            INSERT INTO workouts (workout_date, name)
            VALUES (%s, %s)
            RETURNING id
        """, (workout['date'].date(), workout['name']))
        workout_id = cur.fetchone()[0]
        
        for exercise_data in workout['exercises']:
            exercise_name = exercise_data['name']
            db_exercise = map_exercise_name(exercise_name, db_exercises)
            
            # Auto-add new exercises
            if not db_exercise and auto_add:
                db_exercise = add_exercise_to_db(conn, exercise_name)
                db_exercises[db_exercise['name'].lower()] = db_exercise
                new_exercises.append(f"{exercise_name} → {db_exercise['name']} ({db_exercise['muscle_group']})")
            
            if not db_exercise:
                warnings.append(f"Unknown exercise: '{exercise_name}'")
                continue
            
            exercises_imported += 1
            
            for set_num, set_data in enumerate(exercise_data['sets'], 1):
                reps = int(round(set_data['reps']))
                weight = round(set_data['weight'], 1)
                
                cur.execute("""
                    INSERT INTO workout_sets (workout_id, exercise_id, set_number, weight, reps, set_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (workout_id, db_exercise['id'], set_num, weight, reps, 'working'))
                
                sets_imported += 1
        
        conn.commit()
    
    return exercises_imported, sets_imported, warnings, new_exercises

# ============================================
# Main
# ============================================
def main():
    print("\n🏋️ Workout Notes Importer")
    print("=" * 50)
    
    if not os.getenv('DB_PASSWORD'):
        print("❌ Error: DB_PASSWORD not found in .env file")
        sys.exit(1)
    
    try:
        conn = get_connection()
        print("✓ Connected to database")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    db_exercises = get_exercises(conn)
    print(f"✓ Loaded {len(db_exercises)} exercises from database")
    
    if len(sys.argv) < 2:
        print("\nUsage: python import_workouts.py <filename.txt>")
        print("\nPut all your workout notes in a single text file, then run this script.")
        sys.exit(1)
    
    filename = sys.argv[1]
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        sys.exit(1)
    except UnicodeDecodeError:
        # Try with different encoding
        with open(filename, 'r', encoding='latin-1') as f:
            content = f.read()
    
    print(f"\nParsing {filename}...")
    workouts = parse_notes_file(content)
    
    # Sort by date
    workouts.sort(key=lambda w: w['date'])
    
    print(f"✓ Found {len(workouts)} workouts")
    
    if not workouts:
        print("❌ No valid workouts found")
        sys.exit(1)
    
    # Date range
    earliest = workouts[0]['date'].strftime('%Y-%m-%d')
    latest = workouts[-1]['date'].strftime('%Y-%m-%d')
    print(f"✓ Date range: {earliest} to {latest}")
    
    # Preview
    print("\n" + "=" * 50)
    print("PREVIEW (first 5 workouts):")
    print("=" * 50)
    
    unknown_exercises = set()
    
    for workout in workouts[:5]:
        print(f"\n📅 {workout['date'].strftime('%Y-%m-%d')} - {workout['name']}")
        for ex in workout['exercises']:
            db_ex = map_exercise_name(ex['name'], db_exercises)
            if db_ex:
                status = "✓"
                mapped_name = db_ex['name']
            else:
                status = "➕"  # Will be auto-added
                mapped_name = f"{ex['name'].title()} (NEW)"
                unknown_exercises.add(ex['name'])
            
            sets_str = ', '.join([f"{s['weight']}x{int(s['reps'])}" for s in ex['sets']])
            print(f"  {status} {ex['name']} → {mapped_name}")
            print(f"      Sets: {sets_str}")
    
    if len(workouts) > 5:
        print(f"\n... and {len(workouts) - 5} more workouts")
    
    # Collect all unknown exercises
    for workout in workouts:
        for ex in workout['exercises']:
            if not map_exercise_name(ex['name'], db_exercises):
                unknown_exercises.add(ex['name'])
    
    if unknown_exercises:
        print(f"\n📝 {len(unknown_exercises)} new exercises will be auto-added:")
        for ex in sorted(unknown_exercises)[:15]:
            muscle = guess_muscle_group(ex)
            print(f"   ➕ {ex.title()} ({muscle})")
        if len(unknown_exercises) > 15:
            print(f"   ... and {len(unknown_exercises) - 15} more")
    
    # Confirm
    print("\n" + "=" * 50)
    response = input(f"Import {len(workouts)} workouts? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("Cancelled.")
        sys.exit(0)
    
    # Clear existing data?
    clear_response = input("Clear existing workout data first? (yes/no): ").strip().lower()
    
    if clear_response == 'yes':
        with conn.cursor() as cur:
            cur.execute("DELETE FROM personal_records")
            cur.execute("DELETE FROM workout_sets")
            cur.execute("DELETE FROM workouts")
            conn.commit()
        print("✓ Cleared existing workout data")
    
    # Import
    print("\nImporting...")
    total_exercises = 0
    total_sets = 0
    all_warnings = []
    all_new_exercises = []
    
    for i, workout in enumerate(workouts):
        exercises, sets, warnings, new_ex = import_workout(conn, workout, db_exercises, auto_add=True)
        total_exercises += exercises
        total_sets += sets
        all_warnings.extend(warnings)
        all_new_exercises.extend(new_ex)
        
        # Progress indicator
        if (i + 1) % 50 == 0 or i == len(workouts) - 1:
            print(f"  Processed {i + 1}/{len(workouts)} workouts...")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 IMPORT SUMMARY")
    print("=" * 50)
    print(f"✓ Workouts imported:  {len(workouts)}")
    print(f"✓ Exercises logged:   {total_exercises}")
    print(f"✓ Sets logged:        {total_sets}")
    
    if all_new_exercises:
        unique_new = list(set(all_new_exercises))
        print(f"\n✨ New exercises added ({len(unique_new)}):")
        for ex in unique_new[:20]:
            print(f"   ➕ {ex}")
        if len(unique_new) > 20:
            print(f"   ... and {len(unique_new) - 20} more")
    
    if all_warnings:
        unique_warnings = list(set(all_warnings))
        print(f"\n⚠️  Warnings ({len(unique_warnings)}):")
        for w in unique_warnings[:10]:
            print(f"   - {w}")
        if len(unique_warnings) > 10:
            print(f"   ... and {len(unique_warnings) - 10} more")
    
    print("\n✅ Import complete!")
    print("\nYou can now view your data at:")
    print("  - Frontend: frontend/index.html")
    print("  - API: http://localhost:3000/workouts")
    print("  - Analytics: http://localhost:8000/analysis/health")
    
    conn.close()

if __name__ == "__main__":
    main()
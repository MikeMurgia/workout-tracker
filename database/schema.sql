-- Workout Tracker Database Schema
-- Version: 1.1 (Personal Use - No Authentication)
-- 
-- DESIGN PRINCIPLES:
-- 1. Single-user focus - no auth complexity
-- 2. Normalize data to avoid redundancy
-- 3. Use appropriate data types (DECIMAL for weights, not FLOAT)
-- 4. Include created_at/updated_at for tracking changes
-- 5. Add indexes for columns we'll query frequently

-- Enable UUID extension (PostgreSQL specific)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USER PROFILE TABLE
-- ============================================
-- Single user's preferences and physical stats
-- No password, no email - just your settings
CREATE TABLE user_profile (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    display_name VARCHAR(100) DEFAULT 'Me',
    weight_unit VARCHAR(10) DEFAULT 'lbs' CHECK (weight_unit IN ('lbs', 'kg')),
    
    -- Physical stats for calculations (optional, used for predictions)
    body_weight DECIMAL(5,2),           -- e.g., 185.50 lbs
    height_inches INTEGER,               -- e.g., 72 inches
    birth_date DATE,
    gender VARCHAR(20),
    
    -- Fitness level helps with recommendations
    experience_level VARCHAR(20) DEFAULT 'beginner' 
        CHECK (experience_level IN ('beginner', 'intermediate', 'advanced')),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- EXERCISES TABLE
-- ============================================
-- Master list of all exercises
CREATE TABLE exercises (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,    -- "Bench Press", "Squat", etc.
    
    -- Categorization (useful for recommendations)
    muscle_group VARCHAR(50) NOT NULL,    -- "chest", "back", "legs", etc.
    movement_type VARCHAR(50),            -- "push", "pull", "hinge", "squat"
    equipment VARCHAR(50),                -- "barbell", "dumbbell", "machine", "bodyweight"
    
    -- Is this a compound or isolation movement? (affects recommendations)
    is_compound BOOLEAN DEFAULT false,
    
    -- Instructions/notes
    description TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_exercises_muscle_group ON exercises(muscle_group);

-- ============================================
-- WORKOUTS TABLE
-- ============================================
-- A "workout" is a single training session
CREATE TABLE workouts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- When did this workout happen?
    workout_date DATE NOT NULL DEFAULT CURRENT_DATE,
    start_time TIME,
    end_time TIME,
    
    -- Optional metadata
    name VARCHAR(100),                    -- "Push Day", "Full Body A", etc.
    notes TEXT,
    
    -- How did you feel? (1-10 scale, useful for fatigue tracking)
    perceived_exertion INTEGER CHECK (perceived_exertion BETWEEN 1 AND 10),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Query workouts by date frequently
CREATE INDEX idx_workouts_date ON workouts(workout_date DESC);

-- ============================================
-- WORKOUT SETS TABLE
-- ============================================
-- Individual sets within a workout
-- This is the CORE data for tracking progress
CREATE TABLE workout_sets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workout_id UUID REFERENCES workouts(id) ON DELETE CASCADE,
    exercise_id UUID REFERENCES exercises(id) ON DELETE RESTRICT,
    
    -- The actual data we're tracking
    set_number INTEGER NOT NULL,          -- 1, 2, 3, etc.
    weight DECIMAL(7,2),                  -- Weight used (null for bodyweight)
    reps INTEGER NOT NULL,                -- Reps completed
    
    -- Was this a warmup or working set?
    set_type VARCHAR(20) DEFAULT 'working' 
        CHECK (set_type IN ('warmup', 'working', 'dropset', 'failure')),
    
    -- RPE (Rate of Perceived Exertion) - how hard was this set?
    rpe DECIMAL(3,1) CHECK (rpe BETWEEN 6 AND 10),
    
    -- For rest-pause or cluster sets
    rest_seconds INTEGER,
    
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_workout_sets_exercise ON workout_sets(exercise_id);
CREATE INDEX idx_workout_sets_workout ON workout_sets(workout_id);

-- ============================================
-- GOALS TABLE
-- ============================================
-- Your fitness goals
CREATE TABLE goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exercise_id UUID REFERENCES exercises(id) ON DELETE CASCADE,
    
    -- What's the goal?
    goal_type VARCHAR(50) NOT NULL 
        CHECK (goal_type IN ('weight', 'reps', 'one_rep_max', 'volume')),
    target_value DECIMAL(10,2) NOT NULL,
    
    -- Timeframe
    target_date DATE,
    
    -- Track completion
    achieved BOOLEAN DEFAULT false,
    achieved_date DATE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_goals_achieved ON goals(achieved);

-- ============================================
-- PERSONAL RECORDS TABLE
-- ============================================
-- Automatically tracked PRs
CREATE TABLE personal_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exercise_id UUID REFERENCES exercises(id) ON DELETE CASCADE,
    workout_set_id UUID REFERENCES workout_sets(id) ON DELETE SET NULL,
    
    -- Type of PR
    record_type VARCHAR(50) NOT NULL 
        CHECK (record_type IN ('weight', 'reps', 'estimated_1rm', 'volume')),
    record_value DECIMAL(10,2) NOT NULL,
    
    -- When was it set?
    record_date DATE NOT NULL,
    
    -- Is this still the current PR?
    is_current BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_pr_exercise ON personal_records(exercise_id, is_current);

-- ============================================
-- BODY WEIGHT LOG TABLE
-- ============================================
-- Track your body weight over time (useful for analysis)
CREATE TABLE body_weight_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    log_date DATE NOT NULL DEFAULT CURRENT_DATE,
    weight DECIMAL(5,2) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_body_weight_date ON body_weight_log(log_date);

-- ============================================
-- SEED DATA: Your Profile
-- ============================================
-- Create your profile (you can update these values)
INSERT INTO user_profile (display_name, weight_unit, experience_level) 
VALUES ('Mike', 'lbs', 'intermediate');

-- ============================================
-- SEED DATA: Common Exercises
-- ============================================
INSERT INTO exercises (name, muscle_group, movement_type, equipment, is_compound, description) VALUES
-- Chest
('Barbell Bench Press', 'chest', 'push', 'barbell', true, 'Primary chest compound movement'),
('Incline Dumbbell Press', 'chest', 'push', 'dumbbell', true, 'Upper chest focus'),
('Cable Flyes', 'chest', 'push', 'cable', false, 'Chest isolation'),
('Dips', 'chest', 'push', 'bodyweight', true, 'Chest and triceps compound'),

-- Back
('Barbell Row', 'back', 'pull', 'barbell', true, 'Primary back compound'),
('Pull-ups', 'back', 'pull', 'bodyweight', true, 'Vertical pulling movement'),
('Lat Pulldown', 'back', 'pull', 'cable', true, 'Lat focused pulling'),
('Seated Cable Row', 'back', 'pull', 'cable', true, 'Mid-back focus'),
('Deadlift', 'back', 'hinge', 'barbell', true, 'Full posterior chain compound'),

-- Legs
('Barbell Squat', 'legs', 'squat', 'barbell', true, 'Primary leg compound'),
('Romanian Deadlift', 'legs', 'hinge', 'barbell', true, 'Hamstring focus'),
('Leg Press', 'legs', 'squat', 'machine', true, 'Quad dominant machine compound'),
('Leg Curl', 'legs', 'pull', 'machine', false, 'Hamstring isolation'),
('Leg Extension', 'legs', 'push', 'machine', false, 'Quad isolation'),
('Calf Raise', 'legs', 'push', 'machine', false, 'Calf isolation'),
('Bulgarian Split Squat', 'legs', 'squat', 'dumbbell', true, 'Single leg compound'),
('Hip Thrust', 'legs', 'hinge', 'barbell', true, 'Glute focused'),

-- Shoulders
('Overhead Press', 'shoulders', 'push', 'barbell', true, 'Primary shoulder compound'),
('Dumbbell Shoulder Press', 'shoulders', 'push', 'dumbbell', true, 'Shoulder compound'),
('Lateral Raise', 'shoulders', 'pull', 'dumbbell', false, 'Side delt isolation'),
('Face Pulls', 'shoulders', 'pull', 'cable', false, 'Rear delt and rotator cuff'),
('Reverse Flyes', 'shoulders', 'pull', 'dumbbell', false, 'Rear delt isolation'),

-- Arms
('Barbell Curl', 'arms', 'pull', 'barbell', false, 'Bicep primary'),
('Dumbbell Curl', 'arms', 'pull', 'dumbbell', false, 'Bicep isolation'),
('Tricep Pushdown', 'arms', 'push', 'cable', false, 'Tricep isolation'),
('Skull Crushers', 'arms', 'push', 'barbell', false, 'Tricep compound'),
('Hammer Curl', 'arms', 'pull', 'dumbbell', false, 'Bicep and brachialis'),
('Overhead Tricep Extension', 'arms', 'push', 'dumbbell', false, 'Long head tricep'),

-- Core
('Plank', 'core', 'isometric', 'bodyweight', false, 'Core stability'),
('Cable Crunch', 'core', 'pull', 'cable', false, 'Weighted ab exercise'),
('Hanging Leg Raise', 'core', 'pull', 'bodyweight', false, 'Lower ab focus'),
('Ab Wheel Rollout', 'core', 'push', 'other', false, 'Full core engagement');

-- ============================================
-- USEFUL VIEWS
-- ============================================

-- View: Get workout history with total volume
CREATE VIEW workout_summary AS
SELECT 
    w.id as workout_id,
    w.workout_date,
    w.name as workout_name,
    COUNT(DISTINCT ws.exercise_id) as exercise_count,
    COUNT(ws.id) as total_sets,
    SUM(ws.weight * ws.reps) as total_volume,
    AVG(ws.rpe) as avg_rpe,
    w.perceived_exertion
FROM workouts w
LEFT JOIN workout_sets ws ON w.id = ws.workout_id
WHERE ws.set_type = 'working'
GROUP BY w.id, w.workout_date, w.name, w.perceived_exertion;

-- View: Exercise progress over time (for charts)
CREATE VIEW exercise_progress AS
SELECT 
    ws.exercise_id,
    e.name as exercise_name,
    e.muscle_group,
    w.workout_date,
    MAX(ws.weight) as max_weight,
    SUM(ws.weight * ws.reps) as exercise_volume,
    COUNT(ws.id) as set_count,
    AVG(ws.reps) as avg_reps
FROM workout_sets ws
JOIN workouts w ON ws.workout_id = w.id
JOIN exercises e ON ws.exercise_id = e.id
WHERE ws.set_type = 'working'
GROUP BY ws.exercise_id, e.name, e.muscle_group, w.workout_date;

-- View: Current PRs for each exercise
CREATE VIEW current_prs AS
SELECT 
    e.name as exercise_name,
    pr.record_type,
    pr.record_value,
    pr.record_date
FROM personal_records pr
JOIN exercises e ON pr.exercise_id = e.id
WHERE pr.is_current = true
ORDER BY e.name, pr.record_type;

-- View: Weekly volume by muscle group (great for balance analysis)
CREATE VIEW weekly_volume_by_muscle AS
SELECT 
    DATE_TRUNC('week', w.workout_date) as week_start,
    e.muscle_group,
    SUM(ws.weight * ws.reps) as total_volume,
    COUNT(DISTINCT w.id) as workout_count
FROM workout_sets ws
JOIN workouts w ON ws.workout_id = w.id
JOIN exercises e ON ws.exercise_id = e.id
WHERE ws.set_type = 'working'
GROUP BY DATE_TRUNC('week', w.workout_date), e.muscle_group
ORDER BY week_start DESC, e.muscle_group;
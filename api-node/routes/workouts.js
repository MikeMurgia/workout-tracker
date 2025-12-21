// routes/workouts.js
// Handles all /workouts endpoints
//
// ENDPOINTS:
//   GET    /workouts              - List all workouts
//   POST   /workouts              - Create a new workout
//   GET    /workouts/:id          - Get a workout with all its sets
//   PUT    /workouts/:id          - Update a workout
//   DELETE /workouts/:id          - Delete a workout
//   POST   /workouts/:id/sets     - Add sets to a workout
//   PUT    /workouts/:id/sets/:setId - Update a specific set
//   DELETE /workouts/:id/sets/:setId - Delete a specific set

const express = require('express');
const router = express.Router();
const { query, pool } = require('../db');

// ============================================
// GET /workouts
// ============================================
// List all workouts with summary info
//
// Query parameters:
//   ?limit=10         - Number of results (default: 20)
//   ?offset=0         - Pagination offset
//   ?from=2024-01-01  - Filter from date
//   ?to=2024-12-31    - Filter to date
router.get('/', async (req, res, next) => {
    try {
        const { limit = 20, offset = 0, from, to } = req.query;
        
        let sql = `
            SELECT 
                w.id,
                w.workout_date,
                w.name,
                w.notes,
                w.perceived_exertion,
                w.start_time,
                w.end_time,
                COUNT(DISTINCT ws.exercise_id) as exercise_count,
                COUNT(ws.id) as set_count,
                COALESCE(SUM(ws.weight * ws.reps) FILTER (WHERE ws.set_type = 'working'), 0) as total_volume
            FROM workouts w
            LEFT JOIN workout_sets ws ON w.id = ws.workout_id
            WHERE 1=1
        `;
        
        const params = [];
        let paramIndex = 1;
        
        if (from) {
            sql += ` AND w.workout_date >= $${paramIndex}`;
            params.push(from);
            paramIndex++;
        }
        
        if (to) {
            sql += ` AND w.workout_date <= $${paramIndex}`;
            params.push(to);
            paramIndex++;
        }
        
        sql += `
            GROUP BY w.id
            ORDER BY w.workout_date DESC, w.created_at DESC
            LIMIT $${paramIndex} OFFSET $${paramIndex + 1}
        `;
        params.push(parseInt(limit), parseInt(offset));
        
        const { rows } = await query(sql, params);
        
        res.json({
            count: rows.length,
            workouts: rows
        });
    } catch (err) {
        next(err);
    }
});

// ============================================
// POST /workouts
// ============================================
// Create a new workout
//
// Request body:
// {
//   "workout_date": "2024-01-15",  // Optional, defaults to today
//   "name": "Push Day",            // Optional
//   "notes": "Felt strong",        // Optional
//   "perceived_exertion": 7,       // Optional, 1-10
//   "start_time": "09:00",         // Optional
//   "end_time": "10:30"            // Optional
// }
router.post('/', async (req, res, next) => {
    try {
        const { 
            workout_date, 
            name, 
            notes, 
            perceived_exertion,
            start_time,
            end_time 
        } = req.body;
        
        // Validate perceived_exertion if provided
        if (perceived_exertion !== undefined && 
            (perceived_exertion < 1 || perceived_exertion > 10)) {
            return res.status(400).json({ 
                error: 'perceived_exertion must be between 1 and 10' 
            });
        }
        
        const { rows } = await query(
            `INSERT INTO workouts (workout_date, name, notes, perceived_exertion, start_time, end_time)
             VALUES (COALESCE($1, CURRENT_DATE), $2, $3, $4, $5, $6)
             RETURNING *`,
            [workout_date, name, notes, perceived_exertion, start_time, end_time]
        );
        
        res.status(201).json(rows[0]);
    } catch (err) {
        next(err);
    }
});

// ============================================
// GET /workouts/:id
// ============================================
// Get a single workout with all its sets
router.get('/:id', async (req, res, next) => {
    try {
        const { id } = req.params;
        
        // Get the workout
        const workoutResult = await query(
            'SELECT * FROM workouts WHERE id = $1',
            [id]
        );
        
        if (workoutResult.rows.length === 0) {
            return res.status(404).json({ error: 'Workout not found' });
        }
        
        const workout = workoutResult.rows[0];
        
        // Get all sets for this workout, grouped by exercise
        const setsResult = await query(
            `SELECT 
                ws.*,
                e.name as exercise_name,
                e.muscle_group,
                e.equipment
             FROM workout_sets ws
             JOIN exercises e ON ws.exercise_id = e.id
             WHERE ws.workout_id = $1
             ORDER BY ws.created_at, ws.set_number`,
            [id]
        );
        
        // Group sets by exercise for easier reading
        const exerciseMap = {};
        for (const set of setsResult.rows) {
            const exerciseId = set.exercise_id;
            if (!exerciseMap[exerciseId]) {
                exerciseMap[exerciseId] = {
                    exercise_id: exerciseId,
                    exercise_name: set.exercise_name,
                    muscle_group: set.muscle_group,
                    equipment: set.equipment,
                    sets: []
                };
            }
            exerciseMap[exerciseId].sets.push({
                id: set.id,
                set_number: set.set_number,
                weight: set.weight,
                reps: set.reps,
                set_type: set.set_type,
                rpe: set.rpe,
                rest_seconds: set.rest_seconds,
                notes: set.notes
            });
        }
        
        workout.exercises = Object.values(exerciseMap);
        
        res.json(workout);
    } catch (err) {
        next(err);
    }
});

// ============================================
// PUT /workouts/:id
// ============================================
// Update a workout's details
router.put('/:id', async (req, res, next) => {
    try {
        const { id } = req.params;
        const { 
            workout_date, 
            name, 
            notes, 
            perceived_exertion,
            start_time,
            end_time 
        } = req.body;
        
        const { rows } = await query(
            `UPDATE workouts 
             SET workout_date = COALESCE($1, workout_date),
                 name = COALESCE($2, name),
                 notes = COALESCE($3, notes),
                 perceived_exertion = COALESCE($4, perceived_exertion),
                 start_time = COALESCE($5, start_time),
                 end_time = COALESCE($6, end_time),
                 updated_at = NOW()
             WHERE id = $7
             RETURNING *`,
            [workout_date, name, notes, perceived_exertion, start_time, end_time, id]
        );
        
        if (rows.length === 0) {
            return res.status(404).json({ error: 'Workout not found' });
        }
        
        res.json(rows[0]);
    } catch (err) {
        next(err);
    }
});

// ============================================
// DELETE /workouts/:id
// ============================================
// Delete a workout and all its sets
router.delete('/:id', async (req, res, next) => {
    try {
        const { id } = req.params;
        
        const { rows } = await query(
            'DELETE FROM workouts WHERE id = $1 RETURNING id',
            [id]
        );
        
        if (rows.length === 0) {
            return res.status(404).json({ error: 'Workout not found' });
        }
        
        res.json({ message: 'Workout deleted', id: rows[0].id });
    } catch (err) {
        next(err);
    }
});

// ============================================
// POST /workouts/:id/sets
// ============================================
// Add one or more sets to a workout
//
// Request body (single set):
// {
//   "exercise_id": "uuid-here",
//   "set_number": 1,
//   "weight": 135,
//   "reps": 10,
//   "set_type": "working",
//   "rpe": 7.5,
//   "notes": "Felt easy"
// }
//
// Request body (multiple sets):
// {
//   "sets": [
//     { "exercise_id": "uuid", "set_number": 1, "weight": 135, "reps": 10 },
//     { "exercise_id": "uuid", "set_number": 2, "weight": 135, "reps": 8 },
//     { "exercise_id": "uuid", "set_number": 3, "weight": 135, "reps": 6 }
//   ]
// }
router.post('/:id/sets', async (req, res, next) => {
    try {
        const { id: workoutId } = req.params;
        
        // Check if workout exists
        const workoutCheck = await query(
            'SELECT id FROM workouts WHERE id = $1',
            [workoutId]
        );
        
        if (workoutCheck.rows.length === 0) {
            return res.status(404).json({ error: 'Workout not found' });
        }
        
        // Handle both single set and array of sets
        const sets = req.body.sets || [req.body];
        
        // Validate all sets
        for (const set of sets) {
            if (!set.exercise_id || !set.reps) {
                return res.status(400).json({ 
                    error: 'exercise_id and reps are required for each set' 
                });
            }
        }
        
        // Insert all sets
        const insertedSets = [];
        
        for (const set of sets) {
            const { rows } = await query(
                `INSERT INTO workout_sets 
                    (workout_id, exercise_id, set_number, weight, reps, set_type, rpe, rest_seconds, notes)
                 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                 RETURNING *`,
                [
                    workoutId,
                    set.exercise_id,
                    set.set_number || 1,
                    set.weight,
                    set.reps,
                    set.set_type || 'working',
                    set.rpe,
                    set.rest_seconds,
                    set.notes
                ]
            );
            insertedSets.push(rows[0]);
        }
        
        res.status(201).json({
            count: insertedSets.length,
            sets: insertedSets
        });
    } catch (err) {
        // Handle foreign key violation (invalid exercise_id)
        if (err.code === '23503') {
            return res.status(400).json({ error: 'Invalid exercise_id' });
        }
        next(err);
    }
});

// ============================================
// PUT /workouts/:id/sets/:setId
// ============================================
// Update a specific set
router.put('/:id/sets/:setId', async (req, res, next) => {
    try {
        const { id: workoutId, setId } = req.params;
        const { weight, reps, set_type, rpe, rest_seconds, notes } = req.body;
        
        const { rows } = await query(
            `UPDATE workout_sets 
             SET weight = COALESCE($1, weight),
                 reps = COALESCE($2, reps),
                 set_type = COALESCE($3, set_type),
                 rpe = COALESCE($4, rpe),
                 rest_seconds = COALESCE($5, rest_seconds),
                 notes = COALESCE($6, notes)
             WHERE id = $7 AND workout_id = $8
             RETURNING *`,
            [weight, reps, set_type, rpe, rest_seconds, notes, setId, workoutId]
        );
        
        if (rows.length === 0) {
            return res.status(404).json({ error: 'Set not found' });
        }
        
        res.json(rows[0]);
    } catch (err) {
        next(err);
    }
});

// ============================================
// DELETE /workouts/:id/sets/:setId
// ============================================
// Delete a specific set
router.delete('/:id/sets/:setId', async (req, res, next) => {
    try {
        const { id: workoutId, setId } = req.params;
        
        const { rows } = await query(
            'DELETE FROM workout_sets WHERE id = $1 AND workout_id = $2 RETURNING id',
            [setId, workoutId]
        );
        
        if (rows.length === 0) {
            return res.status(404).json({ error: 'Set not found' });
        }
        
        res.json({ message: 'Set deleted', id: rows[0].id });
    } catch (err) {
        next(err);
    }
});

module.exports = router;
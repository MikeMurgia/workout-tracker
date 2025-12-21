// routes/stats.js
// Handles statistics and progress endpoints
//
// ENDPOINTS:
//   GET /stats/progress/:exerciseId  - Get progress for an exercise over time
//   GET /stats/volume                - Get volume data by muscle group
//   GET /stats/prs                   - Get current personal records
//   GET /stats/summary               - Get overall training summary

const express = require('express');
const router = express.Router();
const { query } = require('../db');

// ============================================
// GET /stats/progress/:exerciseId
// ============================================
// Get progress data for a specific exercise
// Great for charts and tracking strength gains
//
// Query parameters:
//   ?days=90        - Number of days to look back (default: 90)
//
// Returns array of data points with date, max weight, volume, etc.
router.get('/progress/:exerciseId', async (req, res, next) => {
    try {
        const { exerciseId } = req.params;
        const { days = 90 } = req.query;
        
        // First verify the exercise exists
        const exerciseCheck = await query(
            'SELECT name, muscle_group FROM exercises WHERE id = $1',
            [exerciseId]
        );
        
        if (exerciseCheck.rows.length === 0) {
            return res.status(404).json({ error: 'Exercise not found' });
        }
        
        const exercise = exerciseCheck.rows[0];
        
        // Get progress data
        const { rows } = await query(
            `SELECT 
                w.workout_date,
                MAX(ws.weight) as max_weight,
                MAX(ws.reps) FILTER (WHERE ws.weight = (
                    SELECT MAX(weight) FROM workout_sets 
                    WHERE workout_id = w.id AND exercise_id = $1
                )) as reps_at_max_weight,
                SUM(ws.weight * ws.reps) FILTER (WHERE ws.set_type = 'working') as total_volume,
                SUM(ws.reps) FILTER (WHERE ws.set_type = 'working') as total_reps,
                COUNT(ws.id) FILTER (WHERE ws.set_type = 'working') as working_sets,
                AVG(ws.rpe) as avg_rpe
             FROM workout_sets ws
             JOIN workouts w ON ws.workout_id = w.id
             WHERE ws.exercise_id = $1
               AND w.workout_date >= CURRENT_DATE - $2::integer
             GROUP BY w.id, w.workout_date
             ORDER BY w.workout_date`,
            [exerciseId, parseInt(days)]
        );
        
        // Calculate estimated 1RM for each session using Epley formula
        // 1RM = weight × (1 + reps/30)
        const progressData = rows.map(row => ({
            ...row,
            estimated_1rm: row.max_weight && row.reps_at_max_weight 
                ? Math.round(row.max_weight * (1 + row.reps_at_max_weight / 30))
                : null
        }));
        
        res.json({
            exercise_name: exercise.name,
            muscle_group: exercise.muscle_group,
            days_included: parseInt(days),
            data_points: progressData.length,
            progress: progressData
        });
    } catch (err) {
        next(err);
    }
});

// ============================================
// GET /stats/volume
// ============================================
// Get weekly volume breakdown by muscle group
//
// Query parameters:
//   ?weeks=8        - Number of weeks to include (default: 8)
router.get('/volume', async (req, res, next) => {
    try {
        const { weeks = 8 } = req.query;
        
        const { rows } = await query(
            `SELECT 
                DATE_TRUNC('week', w.workout_date)::date as week_start,
                e.muscle_group,
                SUM(ws.weight * ws.reps) as total_volume,
                SUM(ws.reps) as total_reps,
                COUNT(DISTINCT w.id) as workouts,
                COUNT(ws.id) as total_sets
             FROM workout_sets ws
             JOIN workouts w ON ws.workout_id = w.id
             JOIN exercises e ON ws.exercise_id = e.id
             WHERE ws.set_type = 'working'
               AND w.workout_date >= CURRENT_DATE - ($1::integer * 7)
             GROUP BY DATE_TRUNC('week', w.workout_date), e.muscle_group
             ORDER BY week_start DESC, e.muscle_group`,
            [parseInt(weeks)]
        );
        
        // Reorganize data by week for easier charting
        const weeklyData = {};
        for (const row of rows) {
            const week = row.week_start.toISOString().split('T')[0];
            if (!weeklyData[week]) {
                weeklyData[week] = { week_start: week, muscle_groups: {} };
            }
            weeklyData[week].muscle_groups[row.muscle_group] = {
                volume: parseFloat(row.total_volume) || 0,
                reps: parseInt(row.total_reps) || 0,
                sets: parseInt(row.total_sets) || 0,
                workouts: parseInt(row.workouts) || 0
            };
        }
        
        res.json({
            weeks_included: parseInt(weeks),
            weekly_volume: Object.values(weeklyData)
        });
    } catch (err) {
        next(err);
    }
});

// ============================================
// GET /stats/prs
// ============================================
// Get current personal records
//
// Query parameters:
//   ?muscle_group=chest   - Filter by muscle group
router.get('/prs', async (req, res, next) => {
    try {
        const { muscle_group } = req.query;
        
        let sql = `
            SELECT 
                e.id as exercise_id,
                e.name as exercise_name,
                e.muscle_group,
                pr.record_type,
                pr.record_value,
                pr.record_date
            FROM personal_records pr
            JOIN exercises e ON pr.exercise_id = e.id
            WHERE pr.is_current = true
        `;
        
        const params = [];
        
        if (muscle_group) {
            sql += ' AND e.muscle_group = $1';
            params.push(muscle_group.toLowerCase());
        }
        
        sql += ' ORDER BY e.muscle_group, e.name, pr.record_type';
        
        const { rows } = await query(sql, params);
        
        // Group by exercise
        const prsByExercise = {};
        for (const row of rows) {
            if (!prsByExercise[row.exercise_name]) {
                prsByExercise[row.exercise_name] = {
                    exercise_id: row.exercise_id,
                    exercise_name: row.exercise_name,
                    muscle_group: row.muscle_group,
                    records: {}
                };
            }
            prsByExercise[row.exercise_name].records[row.record_type] = {
                value: parseFloat(row.record_value),
                date: row.record_date
            };
        }
        
        res.json({
            count: Object.keys(prsByExercise).length,
            personal_records: Object.values(prsByExercise)
        });
    } catch (err) {
        next(err);
    }
});

// ============================================
// GET /stats/summary
// ============================================
// Get overall training summary
//
// Query parameters:
//   ?days=30        - Number of days to summarize (default: 30)
router.get('/summary', async (req, res, next) => {
    try {
        const { days = 30 } = req.query;
        
        const { rows } = await query(
            `SELECT 
                COUNT(DISTINCT w.id) as total_workouts,
                COUNT(DISTINCT w.workout_date) as training_days,
                COUNT(ws.id) FILTER (WHERE ws.set_type = 'working') as total_sets,
                SUM(ws.reps) FILTER (WHERE ws.set_type = 'working') as total_reps,
                SUM(ws.weight * ws.reps) FILTER (WHERE ws.set_type = 'working') as total_volume,
                COUNT(DISTINCT ws.exercise_id) as unique_exercises,
                AVG(w.perceived_exertion) as avg_perceived_exertion,
                ROUND(AVG(ws.rpe)::numeric, 1) as avg_rpe
             FROM workouts w
             LEFT JOIN workout_sets ws ON w.id = ws.workout_id
             WHERE w.workout_date >= CURRENT_DATE - $1::integer`,
            [parseInt(days)]
        );
        
        const summary = rows[0];
        
        // Get most trained muscle groups
        const muscleGroupResult = await query(
            `SELECT 
                e.muscle_group,
                COUNT(ws.id) as set_count,
                SUM(ws.weight * ws.reps) as volume
             FROM workout_sets ws
             JOIN workouts w ON ws.workout_id = w.id
             JOIN exercises e ON ws.exercise_id = e.id
             WHERE ws.set_type = 'working'
               AND w.workout_date >= CURRENT_DATE - $1::integer
             GROUP BY e.muscle_group
             ORDER BY set_count DESC`,
            [parseInt(days)]
        );
        
        res.json({
            period_days: parseInt(days),
            workouts: parseInt(summary.total_workouts) || 0,
            training_days: parseInt(summary.training_days) || 0,
            total_sets: parseInt(summary.total_sets) || 0,
            total_reps: parseInt(summary.total_reps) || 0,
            total_volume: parseFloat(summary.total_volume) || 0,
            unique_exercises: parseInt(summary.unique_exercises) || 0,
            avg_perceived_exertion: summary.avg_perceived_exertion 
                ? parseFloat(summary.avg_perceived_exertion).toFixed(1) 
                : null,
            avg_rpe: summary.avg_rpe ? parseFloat(summary.avg_rpe) : null,
            muscle_group_breakdown: muscleGroupResult.rows.map(row => ({
                muscle_group: row.muscle_group,
                sets: parseInt(row.set_count),
                volume: parseFloat(row.volume) || 0
            }))
        });
    } catch (err) {
        next(err);
    }
});

module.exports = router;
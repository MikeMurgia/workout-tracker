// routes/profile.js
// Handles user profile endpoints
//
// ENDPOINTS:
//   GET  /profile              - Get your profile
//   PUT  /profile              - Update your profile
//   GET  /profile/bodyweight   - Get body weight history
//   POST /profile/bodyweight   - Log body weight

const express = require('express');
const router = express.Router();
const { query } = require('../db');

// ============================================
// GET /profile
// ============================================
// Get your profile settings
router.get('/', async (req, res, next) => {
    try {
        const { rows } = await query('SELECT * FROM user_profile LIMIT 1');
        
        if (rows.length === 0) {
            return res.status(404).json({ error: 'Profile not found' });
        }
        
        res.json(rows[0]);
    } catch (err) {
        next(err);
    }
});

// ============================================
// PUT /profile
// ============================================
// Update your profile
//
// Request body (all fields optional):
// {
//   "display_name": "Mike",
//   "weight_unit": "lbs",
//   "body_weight": 185,
//   "height_inches": 72,
//   "birth_date": "1995-06-15",
//   "gender": "male",
//   "experience_level": "intermediate"
// }
router.put('/', async (req, res, next) => {
    try {
        const { 
            display_name, 
            weight_unit, 
            body_weight, 
            height_inches,
            birth_date,
            gender,
            experience_level 
        } = req.body;
        
        // Validate weight_unit if provided
        if (weight_unit && !['lbs', 'kg'].includes(weight_unit)) {
            return res.status(400).json({ 
                error: 'weight_unit must be "lbs" or "kg"' 
            });
        }
        
        // Validate experience_level if provided
        if (experience_level && 
            !['beginner', 'intermediate', 'advanced'].includes(experience_level)) {
            return res.status(400).json({ 
                error: 'experience_level must be "beginner", "intermediate", or "advanced"' 
            });
        }
        
        const { rows } = await query(
            `UPDATE user_profile 
             SET display_name = COALESCE($1, display_name),
                 weight_unit = COALESCE($2, weight_unit),
                 body_weight = COALESCE($3, body_weight),
                 height_inches = COALESCE($4, height_inches),
                 birth_date = COALESCE($5, birth_date),
                 gender = COALESCE($6, gender),
                 experience_level = COALESCE($7, experience_level),
                 updated_at = NOW()
             RETURNING *`
            ,
            [display_name, weight_unit, body_weight, height_inches, birth_date, gender, experience_level]
        );
        
        res.json(rows[0]);
    } catch (err) {
        next(err);
    }
});

// ============================================
// GET /profile/bodyweight
// ============================================
// Get body weight history
//
// Query parameters:
//   ?days=90        - Number of days to include (default: 90)
router.get('/bodyweight', async (req, res, next) => {
    try {
        const { days = 90 } = req.query;
        
        const { rows } = await query(
            `SELECT log_date, weight, notes
             FROM body_weight_log
             WHERE log_date >= CURRENT_DATE - $1::integer
             ORDER BY log_date DESC`,
            [parseInt(days)]
        );
        
        // Calculate some stats
        let stats = null;
        if (rows.length > 0) {
            const weights = rows.map(r => parseFloat(r.weight));
            const latest = weights[0];
            const oldest = weights[weights.length - 1];
            
            stats = {
                current: latest,
                change: parseFloat((latest - oldest).toFixed(2)),
                min: Math.min(...weights),
                max: Math.max(...weights),
                avg: parseFloat((weights.reduce((a, b) => a + b, 0) / weights.length).toFixed(2))
            };
        }
        
        res.json({
            days_included: parseInt(days),
            entries: rows.length,
            stats,
            history: rows
        });
    } catch (err) {
        next(err);
    }
});

// ============================================
// POST /profile/bodyweight
// ============================================
// Log your body weight
//
// Request body:
// {
//   "weight": 185.5,
//   "log_date": "2024-01-15",  // Optional, defaults to today
//   "notes": "After breakfast"  // Optional
// }
router.post('/bodyweight', async (req, res, next) => {
    try {
        const { weight, log_date, notes } = req.body;
        
        if (!weight) {
            return res.status(400).json({ error: 'weight is required' });
        }
        
        // Use upsert to handle logging multiple times on same day
        // (updates instead of creating duplicate)
        const { rows } = await query(
            `INSERT INTO body_weight_log (log_date, weight, notes)
             VALUES (COALESCE($1, CURRENT_DATE), $2, $3)
             ON CONFLICT (log_date) 
             DO UPDATE SET weight = $2, notes = COALESCE($3, body_weight_log.notes)
             RETURNING *`,
            [log_date, weight, notes]
        );
        
        res.status(201).json(rows[0]);
    } catch (err) {
        next(err);
    }
});

module.exports = router;
// routes/exercises.js
// Handles all /exercises endpoints
//
// ENDPOINTS:
//   GET  /exercises          - List all exercises (with optional filters)
//   GET  /exercises/:id      - Get a single exercise by ID
//   POST /exercises          - Create a custom exercise

const express = require('express');
const router = express.Router();
const { query } = require('../db');

// ============================================
// GET /exercises
// ============================================
// List all exercises, with optional filtering
//
// Query parameters:
//   ?muscle_group=chest    - Filter by muscle group
//   ?equipment=barbell     - Filter by equipment
//   ?compound=true         - Only compound movements
//
// Example: GET /exercises?muscle_group=chest&equipment=barbell
router.get('/', async (req, res, next) => {
    try {
        // Extract query parameters
        const { muscle_group, equipment, compound } = req.query;
        
        // Build the query dynamically based on filters
        let sql = 'SELECT * FROM exercises WHERE 1=1';
        const params = [];
        let paramIndex = 1;
        
        if (muscle_group) {
            sql += ` AND muscle_group = $${paramIndex}`;
            params.push(muscle_group.toLowerCase());
            paramIndex++;
        }
        
        if (equipment) {
            sql += ` AND equipment = $${paramIndex}`;
            params.push(equipment.toLowerCase());
            paramIndex++;
        }
        
        if (compound !== undefined) {
            sql += ` AND is_compound = $${paramIndex}`;
            params.push(compound === 'true');
            paramIndex++;
        }
        
        sql += ' ORDER BY muscle_group, name';
        
        const { rows } = await query(sql, params);
        
        res.json({
            count: rows.length,
            exercises: rows
        });
    } catch (err) {
        next(err);  // Pass error to global error handler
    }
});

// ============================================
// GET /exercises/groups
// ============================================
// Get list of all muscle groups (useful for dropdowns)
router.get('/groups', async (req, res, next) => {
    try {
        const { rows } = await query(
            'SELECT DISTINCT muscle_group FROM exercises ORDER BY muscle_group'
        );
        
        res.json({
            groups: rows.map(row => row.muscle_group)
        });
    } catch (err) {
        next(err);
    }
});

// ============================================
// GET /exercises/:id
// ============================================
// Get a single exercise by ID
router.get('/:id', async (req, res, next) => {
    try {
        const { id } = req.params;
        
        const { rows } = await query(
            'SELECT * FROM exercises WHERE id = $1',
            [id]
        );
        
        if (rows.length === 0) {
            return res.status(404).json({ error: 'Exercise not found' });
        }
        
        res.json(rows[0]);
    } catch (err) {
        next(err);
    }
});

// ============================================
// POST /exercises
// ============================================
// Create a custom exercise
//
// Request body:
// {
//   "name": "Cable Lateral Raise",
//   "muscle_group": "shoulders",
//   "movement_type": "pull",
//   "equipment": "cable",
//   "is_compound": false,
//   "description": "Optional description"
// }
router.post('/', async (req, res, next) => {
    try {
        const { name, muscle_group, movement_type, equipment, is_compound, description } = req.body;
        
        // Validate required fields
        if (!name || !muscle_group) {
            return res.status(400).json({ 
                error: 'name and muscle_group are required' 
            });
        }
        
        const { rows } = await query(
            `INSERT INTO exercises (name, muscle_group, movement_type, equipment, is_compound, description)
             VALUES ($1, $2, $3, $4, $5, $6)
             RETURNING *`,
            [name, muscle_group, movement_type, equipment, is_compound || false, description]
        );
        
        res.status(201).json(rows[0]);
    } catch (err) {
        // Handle unique constraint violation (duplicate exercise name)
        if (err.code === '23505') {
            return res.status(409).json({ error: 'Exercise with this name already exists' });
        }
        next(err);
    }
});

// ============================================
// PUT /exercises/:id
// ============================================
// Update an exercise
router.put('/:id', async (req, res, next) => {
    try {
        const { id } = req.params;
        const { name, muscle_group, movement_type, equipment, is_compound, description } = req.body;
        
        const { rows } = await query(
            `UPDATE exercises 
             SET name = COALESCE($1, name),
                 muscle_group = COALESCE($2, muscle_group),
                 movement_type = COALESCE($3, movement_type),
                 equipment = COALESCE($4, equipment),
                 is_compound = COALESCE($5, is_compound),
                 description = COALESCE($6, description)
             WHERE id = $7
             RETURNING *`,
            [name, muscle_group, movement_type, equipment, is_compound, description, id]
        );
        
        if (rows.length === 0) {
            return res.status(404).json({ error: 'Exercise not found' });
        }
        
        res.json(rows[0]);
    } catch (err) {
        if (err.code === '23505') {
            return res.status(409).json({ error: 'Exercise with this name already exists' });
        }
        next(err);
    }
});

// ============================================
// DELETE /exercises/:id
// ============================================
// Delete an exercise (will fail if it has workout sets referencing it)
router.delete('/:id', async (req, res, next) => {
    try {
        const { id } = req.params;
        
        // Check if exercise has any sets
        const setsCheck = await query(
            'SELECT COUNT(*) as count FROM workout_sets WHERE exercise_id = $1',
            [id]
        );
        
        if (parseInt(setsCheck.rows[0].count) > 0) {
            return res.status(400).json({ 
                error: 'Cannot delete exercise with existing workout data. Delete the workout sets first.',
                sets_count: parseInt(setsCheck.rows[0].count)
            });
        }
        
        const { rows } = await query(
            'DELETE FROM exercises WHERE id = $1 RETURNING id, name',
            [id]
        );
        
        if (rows.length === 0) {
            return res.status(404).json({ error: 'Exercise not found' });
        }
        
        res.json({ message: 'Exercise deleted', id: rows[0].id, name: rows[0].name });
    } catch (err) {
        next(err);
    }
});

module.exports = router;
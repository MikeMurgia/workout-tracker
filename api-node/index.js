// index.js
// Main entry point for the Workout Tracker API
//
// ARCHITECTURE:
// - index.js: Server setup, middleware, route mounting
// - db.js: Database connection
// - routes/*.js: Route handlers grouped by resource

const express = require('express');
const cors = require('cors');
require('dotenv').config();

// Import routes
const exerciseRoutes = require('./routes/exercises');
const workoutRoutes = require('./routes/workouts');
const statsRoutes = require('./routes/stats');
const profileRoutes = require('./routes/profile');

// Create Express app
const app = express();
const PORT = process.env.PORT || 3000;

// ============================================
// MIDDLEWARE
// ============================================
// Middleware runs on EVERY request before your route handlers

// Parse JSON request bodies
// Without this, req.body would be undefined
app.use(express.json());

// Enable CORS (Cross-Origin Resource Sharing)
// Allows your frontend (running on a different port) to call this API
app.use(cors());

// Simple request logger
// Shows each request in the console - helpful for debugging
app.use((req, res, next) => {
    console.log(`${new Date().toISOString()} | ${req.method} ${req.path}`);
    next();  // Don't forget this! Passes control to the next middleware/route
});

// ============================================
// ROUTES
// ============================================
// Each route file handles a specific resource

// Health check endpoint - useful for checking if API is running
app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Mount route modules
// All exercise routes will be prefixed with /exercises
app.use('/exercises', exerciseRoutes);
app.use('/workouts', workoutRoutes);
app.use('/stats', statsRoutes);
app.use('/profile', profileRoutes);

// ============================================
// ERROR HANDLING
// ============================================

// 404 handler - runs if no route matched
app.use((req, res) => {
    res.status(404).json({ error: 'Endpoint not found' });
});

// Global error handler - catches any errors thrown in routes
// Must have 4 parameters for Express to recognize it as error handler
app.use((err, req, res, next) => {
    console.error('Error:', err.message);
    console.error(err.stack);
    
    res.status(err.status || 500).json({
        error: err.message || 'Internal server error'
    });
});

// ============================================
// START SERVER
// ============================================
app.listen(PORT, () => {
    console.log(`
========================================
  Workout Tracker API
  Running on http://localhost:${PORT}
  
  Endpoints:
    GET  /health          - Health check
    GET  /exercises       - List all exercises
    GET  /workouts        - List all workouts
    POST /workouts        - Create a workout
    GET  /stats/progress  - Get exercise progress
========================================
    `);
});
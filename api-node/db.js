// db.js
// Database connection pool
// 
// WHY A POOL?
// - Opening a new database connection is slow (~20-50ms)
// - A pool keeps connections open and reuses them
// - Much faster for handling multiple requests

const { Pool } = require('pg');
require('dotenv').config();

const pool = new Pool({
    host: process.env.DB_HOST,
    port: process.env.DB_PORT,
    database: process.env.DB_NAME,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    
    // Pool configuration
    max: 10,              // Maximum number of connections in the pool
    idleTimeoutMillis: 30000,  // Close idle connections after 30 seconds
    connectionTimeoutMillis: 2000,  // Return error if can't connect in 2 seconds
});

// Test the connection on startup
pool.on('connect', () => {
    console.log('Database connected successfully');
});

pool.on('error', (err) => {
    console.error('Unexpected database error:', err);
    process.exit(-1);
});

// Helper function for running queries
// Usage: const { rows } = await query('SELECT * FROM exercises');
const query = (text, params) => pool.query(text, params);

module.exports = { pool, query };
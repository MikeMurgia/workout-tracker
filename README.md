# Workout Tracker

Personal workout tracking application with data science features for progress prediction and recommendations.

## Tech Stack

- **API**: Node.js + Express
- **Analytics**: Python + FastAPI
- **Performance**: Rust
- **Database**: PostgreSQL

## Project Structure
```
workout-tracker/
├── api-node/        # REST API (Node.js)
├── analytics-python/ # Data science & ML (Python)
├── engine-rust/     # Performance calculations (Rust)
├── database/        # SQL schemas and migrations
├── docs/            # Documentation
└── scripts/         # Utility scripts
```

## Setup

### Database
1. Install PostgreSQL
2. Create database: `CREATE DATABASE workout_tracker;`
3. Run schema: `psql -U postgres -d workout_tracker -f database/schema.sql`

## Features (Planned)

- [ ] Log workouts and sets
- [ ] Track progress over time
- [ ] Predict future lifts
- [ ] Get exercise recommendations
- [ ] Analyze training volume by muscle group
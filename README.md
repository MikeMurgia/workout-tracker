# 💪 Workout Tracker

A full-stack personal fitness application combining software engineering with data science to provide intelligent workout tracking and ML-powered predictions.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Node](https://img.shields.io/badge/node-18%2B-green.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![PostgreSQL](https://img.shields.io/badge/postgresql-14%2B-blue.svg)

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [API Documentation](#-api-documentation)
- [Machine Learning Components](#-machine-learning-components)
- [Database Schema](#-database-schema)
- [Technical Decisions](#-technical-decisions)
- [Future Improvements](#-future-improvements)

## ✨ Features

### Core Functionality
- **Workout Logging** - Track exercises, sets, reps, and weights
- **Exercise Library** - 30+ pre-loaded exercises organized by muscle group
- **Progress Tracking** - Visualize strength gains over time
- **Personal Records** - Automatic PR detection and tracking

### AI-Powered Insights
- **Strength Predictions** - ML model forecasts future 1RM based on training history
- **Goal Calculator** - Predict when you'll reach a target weight
- **Anomaly Detection** - Identify unusual patterns (performance drops, fatigue signals)
- **Training Health Score** - 0-100 score analyzing consistency, progress, and recovery
- **Smart Recommendations** - Suggests what to train based on muscle group balance
- **Deload Advisor** - Recommends recovery weeks based on fatigue accumulation

## 🏗 Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│   Node.js API   │────▶│   PostgreSQL    │
│  (HTML/CSS/JS)  │     │   (Port 3000)   │     │    Database     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                              ▲
         │              ┌─────────────────┐             │
         └─────────────▶│ Python Analytics│─────────────┘
                        │   (Port 8000)   │
                        └─────────────────┘
```

| Service | Responsibility |
|---------|----------------|
| **Node.js API** | CRUD operations, data persistence, basic statistics |
| **Python Analytics** | ML predictions, anomaly detection, recommendations |
| **PostgreSQL** | Relational data storage with optimized indexing |
| **Frontend** | User interface with interactive charts |

## 🛠 Tech Stack

### Backend
- **Node.js** + Express.js - REST API
- **Python** + FastAPI - Analytics microservice
- **PostgreSQL** - Database
- **SQLAlchemy** - Python ORM

### Data Science
- **pandas** - Data manipulation
- **scikit-learn** - Machine learning
- **NumPy** - Numerical computing

### Frontend
- **Vanilla JavaScript** - No framework dependencies
- **Chart.js** - Data visualization
- **CSS3** - Custom styling with CSS variables

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL 14+

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/workout-tracker.git
   cd workout-tracker
   ```

2. **Set up the database**
   ```bash
   # Connect to PostgreSQL and create database
   psql -U postgres
   CREATE DATABASE workout_tracker;
   \q

   # Run schema
   psql -U postgres -d workout_tracker -f database/schema.sql
   ```

3. **Set up Node.js API**
   ```bash
   cd api-node
   npm install
   
   # Create .env file
   cp .env.example .env
   # Edit .env with your database credentials
   
   npm run dev
   ```

4. **Set up Python Analytics Service**
   ```bash
   cd analytics-python
   
   # Create virtual environment
   python -m venv venv
   
   # Activate (Windows)
   venv\Scripts\activate
   # Activate (Mac/Linux)
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Create .env file
   cp .env.example .env
   # Edit .env with your database credentials
   
   uvicorn main:app --reload --port 8000
   ```

5. **Open the frontend**
   ```bash
   # Simply open in browser
   open frontend/index.html
   
   # Or use a local server
   cd frontend
   python -m http.server 8080
   ```

### Environment Variables

Both services require a `.env` file:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=workout_tracker
DB_USER=postgres
DB_PASSWORD=your_password
```

## 📚 API Documentation

### Node.js API (Port 3000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/exercises` | GET | List all exercises |
| `/exercises?muscle_group=chest` | GET | Filter by muscle group |
| `/workouts` | GET | List workouts |
| `/workouts` | POST | Create workout |
| `/workouts/:id` | GET | Get workout with sets |
| `/workouts/:id/sets` | POST | Add sets to workout |
| `/stats/progress/:exerciseId` | GET | Get exercise progress |
| `/stats/summary` | GET | Training summary |
| `/stats/prs` | GET | Personal records |

### Python Analytics API (Port 8000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/predictions/strength/{exercise_id}` | GET | Predict future strength |
| `/predictions/goal/{exercise_id}` | GET | Predict goal achievement date |
| `/predictions/1rm/calculate` | GET | Calculate estimated 1RM |
| `/analysis/health` | GET | Training health score |
| `/analysis/anomalies` | GET | Detect training anomalies |
| `/recommendations/next-workout` | GET | Get workout recommendation |
| `/recommendations/balance` | GET | Muscle group balance analysis |
| `/recommendations/deload` | GET | Check if deload needed |

**Interactive API Docs:** http://localhost:8000/docs

## 🤖 Machine Learning Components

### 1. Strength Prediction Model

**Algorithm:** Ridge Regression (L2-regularized linear regression)

**Why Ridge Regression:**
- Handles multicollinearity between features
- L2 regularization prevents overfitting on small datasets
- Provides stable predictions with limited data points

**Feature Engineering:**

| Feature | Description | Rationale |
|---------|-------------|-----------|
| `days_since_start` | Numeric time representation | Captures linear progression |
| `session_number` | Sequential workout count | Accounts for training frequency |
| `cumulative_volume` | Total weight × reps to date | Proxy for training stimulus |
| `rolling_avg_1rm` | 3-session moving average | Smooths noise in data |
| `days_since_last` | Recovery time between sessions | Accounts for supercompensation |

**Model Selection:** Uses k-fold cross-validation (k=5) comparing Ridge vs Linear Regression, selecting based on Mean Absolute Error (MAE).

### 2. Estimated 1RM Calculation

Implements established biomechanical formulas:

| Formula | Equation | Best For |
|---------|----------|----------|
| **Epley** | `weight × (1 + reps/30)` | General use |
| **Brzycki** | `weight × (36 / (37 - reps))` | Low rep ranges (1-6) |
| **Lombardi** | `weight × reps^0.10` | Conservative estimates |
| **O'Conner** | `weight × (1 + reps/40)` | Higher rep ranges |

### 3. Anomaly Detection

**Method:** Statistical process control using Z-scores

**Process:**
1. Calculate rolling mean and standard deviation (5-session window)
2. Compute Z-score: `z = (value - rolling_mean) / rolling_std`
3. Flag sessions where |Z| > 2.0

**Why Z-scores over Isolation Forest/DBSCAN:**
- Interpretable results ("2.3 std below average")
- Works well with small, sequential datasets
- No hyperparameter tuning required

**Anomaly Types:**
- Performance drops (negative Z-score on 1RM)
- Performance spikes (positive Z-score)
- Volume anomalies
- Training gaps

### 4. Training Health Score

**Method:** Multi-factor weighted scoring (rule-based expert system)

| Component (0-25 pts) | Measurement |
|----------------------|-------------|
| **Consistency** | Variance in days between sessions |
| **Progress** | First-half vs second-half 1RM comparison |
| **Volume** | Training volume trend and consistency |
| **Recovery** | Consecutive high-exertion sessions |

### 5. Training Recommendations

**Method:** Rule-based system with data-driven inputs

**Logic:**
1. Calculate sets per muscle group (last 7 days)
2. Compare against evidence-based volume targets
3. Factor in recovery time per muscle group
4. Recommend undertrained + recovered muscles

## 🗄 Database Schema

### Core Tables

```sql
-- Exercises (pre-seeded library)
exercises (id, name, muscle_group, equipment, is_compound)

-- Workout sessions
workouts (id, workout_date, name, perceived_exertion, notes)

-- Individual sets
workout_sets (id, workout_id, exercise_id, set_number, weight, reps, set_type, rpe)

-- Personal records
personal_records (id, exercise_id, record_type, record_value, record_date)
```

### Design Decisions

- **UUIDs for primary keys** - Supports distributed systems, no ID collision
- **DECIMAL for weights** - Avoids floating-point precision errors
- **Individual sets stored separately** - Enables granular analysis
- **Indexes on query columns** - Optimized for workout_date, exercise_id, muscle_group

## 🎯 Technical Decisions

### Why separate Python service?

| Pros | Cons |
|------|------|
| Superior data science libraries | Added infrastructure complexity |
| Independent scaling | Network latency between services |
| Team specialization | More deployment steps |

### Why not deep learning?

- Dataset too small (individual user's history)
- Linear models perform well on structured, low-dimensional data
- Better interpretability
- Lower overfitting risk
- Faster training/inference

### Why PostgreSQL over NoSQL?

- Highly relational data (workouts → sets → exercises)
- Complex aggregation queries needed
- ACID compliance for data integrity
- Mature tooling and ecosystem

## 🔮 Future Improvements

- [ ] **Prediction uncertainty** - Bayesian approaches for confidence intervals
- [ ] **Time series models** - ARIMA/Prophet for longer training histories
- [ ] **Personalized 1RM formulas** - Learn from user's actual max attempts
- [ ] **Fatigue modeling** - Banister's fitness-fatigue model
- [ ] **Mobile app** - React Native implementation
- [ ] **Social features** - Compare with friends, share workouts
- [ ] **Workout templates** - Save and reuse workout structures
- [ ] **Data import** - Import from Strong, Hevy, etc.

## 📁 Project Structure

```
workout-tracker/
├── api-node/                 # Node.js REST API
│   ├── routes/
│   │   ├── exercises.js
│   │   ├── workouts.js
│   │   ├── stats.js
│   │   └── profile.js
│   ├── index.js
│   ├── db.js
│   └── package.json
│
├── analytics-python/         # Python Analytics Service
│   ├── services/
│   │   ├── strength_predictor.py
│   │   ├── anomaly_detector.py
│   │   └── recommender.py
│   ├── routers/
│   │   ├── predictions.py
│   │   ├── analysis.py
│   │   └── recommendations.py
│   ├── main.py
│   ├── database.py
│   └── requirements.txt
│
├── frontend/                 # Web UI
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   └── app.js
│   └── index.html
│
├── database/                 # Database scripts
│   └── schema.sql
│
└── README.md
```
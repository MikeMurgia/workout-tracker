"""
Workout Tracker Analytics Service
FastAPI application for ML-powered workout analysis

Run with: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers
from routers import predictions_router, analysis_router, recommendations_router

# Create FastAPI app
app = FastAPI(
    title="Workout Tracker Analytics",
    description="""
    ## ML-Powered Workout Analysis
    
    This service provides data science features for the Workout Tracker:
    
    ### Predictions
    - **Strength Forecasting**: Predict future 1RM based on training history
    - **Goal Date Estimation**: Predict when you'll reach a target weight
    - **1RM Calculator**: Calculate estimated 1RM using various formulas
    
    ### Analysis
    - **Anomaly Detection**: Identify unusual patterns (drops, spikes, fatigue)
    - **Training Health Score**: Overall assessment of your training quality
    
    ### Recommendations
    - **Next Workout**: Suggestions based on recovery and muscle balance
    - **Training Balance**: Analysis of muscle group distribution
    - **Deload Timing**: Recommendations for recovery weeks
    
    ---
    
    **Tech Stack**: Python, FastAPI, scikit-learn, pandas
    """,
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc alternative
)

# Configure CORS to allow requests from frontend and Node API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Node.js API
        "http://localhost:8080",   # Frontend dev server
        "http://127.0.0.1:5500",   # VS Code Live Server
        "null"                      # Local file:// access
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Check if the analytics service is running"""
    return {
        "status": "healthy",
        "service": "workout-tracker-analytics",
        "version": "1.0.0"
    }


# Include routers
app.include_router(predictions_router)
app.include_router(analysis_router)
app.include_router(recommendations_router)


# Root endpoint with service info
@app.get("/", tags=["Info"])
async def root():
    """Service information and available endpoints"""
    return {
        "service": "Workout Tracker Analytics",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "predictions": {
                "strength": "GET /predictions/strength/{exercise_id}",
                "goal": "GET /predictions/goal/{exercise_id}",
                "1rm_calculator": "GET /predictions/1rm/calculate"
            },
            "analysis": {
                "anomalies": "GET /analysis/anomalies/{exercise_id}",
                "all_anomalies": "GET /analysis/anomalies",
                "health_score": "GET /analysis/health"
            },
            "recommendations": {
                "next_workout": "GET /recommendations/next-workout",
                "balance": "GET /recommendations/balance",
                "deload": "GET /recommendations/deload",
                "exercises": "GET /recommendations/exercises"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
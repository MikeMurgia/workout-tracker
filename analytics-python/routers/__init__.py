"""
API Routers Package
"""

from .predictions import router as predictions_router
from .analysis import router as analysis_router
from .recommendations import router as recommendations_router

__all__ = ['predictions_router', 'analysis_router', 'recommendations_router']
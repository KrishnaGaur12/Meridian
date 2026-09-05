"""
Central API Router for Razorpay AI Risk Manager.
Includes routes for health, mode, system, webhooks, real-time events, transactions,
disputes, risk assessment, evidence engine, AI response generator, and chargeback package generator.
"""

from fastapi import APIRouter

from src.api.routes.health import router as health_router
from src.api.routes.mode import router as mode_router
from src.api.routes.system import router as system_router
from src.api.routes.webhooks import router as webhooks_router
from src.api.routes.events import router as events_router
from src.api.routes.transactions import router as transactions_router
from src.api.routes.disputes import router as disputes_router
from src.api.routes.risk import router as risk_router
from src.api.routes.evidence import router as evidence_router
from src.api.routes.response import router as response_router
from src.api.routes.package import router as package_router
from src.api.routes.demo import router as demo_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(mode_router)
api_router.include_router(system_router)
api_router.include_router(webhooks_router)
api_router.include_router(events_router)
api_router.include_router(transactions_router)
api_router.include_router(disputes_router)
api_router.include_router(risk_router)
api_router.include_router(evidence_router)
api_router.include_router(response_router)
api_router.include_router(package_router)
api_router.include_router(demo_router)

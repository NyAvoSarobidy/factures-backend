"""
Point d'entrée FastAPI pour le projet Factures.

Adapté pour le déploiement Render :
- La variable d'environnement PORT est utilisée si présente
- CORS ouvert en production (le frontend aura son propre domaine)
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import db
from app.routers import commission as commission_router
from app.routers import preconfirmation as preconfirmation_router
from app.routers import extract as extract_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pour Render : le port vient de la variable d'environnement PORT
PORT = int(os.environ.get("PORT", settings.APP_PORT))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Démarrage : vérifier la connexion à Supabase."""
    logger.info("Démarrage du backend Factures...")
    logger.info("Environnement : %s", settings.APP_ENV)

    if db.health_check():
        logger.info("Connexion Supabase : OK")
    else:
        logger.warning(
            "Connexion Supabase : ECHEC — "
            "vérifie SUPABASE_URL et SUPABASE_SERVICE_KEY dans .env"
        )

    yield
    logger.info("Arrêt du backend.")


app = FastAPI(
    title="Factures — Pré-confirmation de commission",
    description=(
        "Backend FastAPI pour la génération de pré-confirmations "
        "de commission aux apporteurs d'affaires."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://factures-frontend.vercel.app"
]

# En prod, autoriser le domaine Vercel exact
frontend_url = os.environ.get("FRONTEND_URL")
if frontend_url:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(commission_router.router)
app.include_router(preconfirmation_router.router)
app.include_router(preconfirmation_router.audit_router)
app.include_router(extract_router.router)


@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "environment": settings.APP_ENV,
        "database": "connected" if db.health_check() else "disconnected",
    }


@app.get("/", tags=["system"])
async def root():
    return {
        "service": "factures-backend",
        "docs": "/docs",
        "health": "/health",
    }

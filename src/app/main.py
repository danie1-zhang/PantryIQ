from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.exception_handlers import register_exception_handlers
from src.api.routes import auth, foods, health, meals, pantry, preferences, users
from src.app.settings import get_settings

API_PREFIX = "/api/v1"

app = FastAPI(title="Nutrition Optimizer API", version="0.1.0")
register_exception_handlers(app)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys([*settings.cors_origins, settings.frontend_origin])),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

for router in (
    health.router,
    auth.router,
    foods.router,
    users.router,
    pantry.router,
    preferences.router,
    meals.router,
):
    app.include_router(router, prefix=API_PREFIX)

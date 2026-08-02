from typing import Annotated

from fastapi import APIRouter, Depends

from src.ai.preference_provider import OpenAICompatiblePreferenceProvider, PreferenceProvider
from src.api.dependencies import AppSettings, CurrentUser
from src.schemas.preferences import PreferenceParseRequest, PreferenceParseResponse
from src.services.preference_service import interpretation_summary, parse_preferences

router = APIRouter(prefix="/preferences", tags=["preferences"])


def get_preference_provider(settings: AppSettings) -> PreferenceProvider:
    return OpenAICompatiblePreferenceProvider(settings)


PreferenceProviderDependency = Annotated[PreferenceProvider, Depends(get_preference_provider)]


@router.post("/parse", response_model=PreferenceParseResponse)
def parse_preference_text(
    payload: PreferenceParseRequest,
    user: CurrentUser,
    provider: PreferenceProviderDependency,
    settings: AppSettings,
) -> PreferenceParseResponse:
    preferences = parse_preferences(
        payload.text, provider, validation_retries=settings.llm_max_retries
    )
    return PreferenceParseResponse(
        preferences=preferences,
        interpretation_summary=interpretation_summary(preferences),
    )

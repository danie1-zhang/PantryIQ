from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.app.settings import Settings
from src.services.exceptions import ExternalServiceError

SYSTEM_PROMPT = """You convert a user's meal request into JSON only.
Extract only explicitly supported preferences. Distinguish prohibitions/allergies from soft dislikes.
Never invent allergies, medical rules, food IDs, or unsupported facts. Use lowercase normalized tags.
Use cuisine_mode compatible unless the user explicitly asks for strict or preference-only behavior.
If material ambiguity blocks safe interpretation, set clarification_needed and ask one concise question.
Return exactly the fields in this schema and no prose:
{"cuisines":[],"cuisine_mode":"compatible","required_food_ids":[],"preferred_food_ids":[],
"excluded_food_ids":[],"required_categories":[],"preferred_categories":[],
"excluded_categories":[],"preferred_ingredients":[],"avoid_ingredients":[],"allergens":[],
"dietary_rules":[],"spice_preference":null,"texture_preferences":[],"flavor_preferences":[],
"preparation_preferences":[],"hard_exclusions":[],"soft_dislikes":[],
"clarification_needed":false,"clarification_question":null}"""


class PreferenceProvider(Protocol):
    def parse(self, text: str) -> str: ...


@dataclass(frozen=True)
class OpenAICompatiblePreferenceProvider:
    settings: Settings

    def parse(self, text: str) -> str:
        if (
            self.settings.llm_api_key is None
            or not self.settings.llm_api_key.get_secret_value().strip()
        ):
            raise ExternalServiceError("Natural-language parsing is not configured")
        payload = json.dumps(
            {
                "model": self.settings.llm_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            }
        ).encode()
        request = Request(
            f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.settings.llm_api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        attempts = self.settings.llm_max_retries + 1
        for attempt in range(attempts):
            try:
                with urlopen(request, timeout=self.settings.llm_timeout_seconds) as response:
                    body = json.loads(response.read())
                return body["choices"][0]["message"]["content"]
            except (
                HTTPError,
                URLError,
                TimeoutError,
                KeyError,
                TypeError,
                json.JSONDecodeError,
            ) as exc:
                if attempt == attempts - 1:
                    raise ExternalServiceError(
                        "Preference parsing provider is unavailable"
                    ) from exc
        raise ExternalServiceError("Preference parsing provider is unavailable")

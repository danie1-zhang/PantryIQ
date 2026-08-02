# NLP preference layer

The language model is used only to translate a short meal request into a strict JSON contract. It receives the request text—not profile data, pantry contents, credentials, tokens, or database access. Pydantic rejects unknown fields, malformed JSON, invalid tags, oversized lists, and food IDs invented by the provider. The backend never turns provider text into SQL.

Deterministic application code enforces the validated result against trusted `Food` metadata. Hard restrictions remove foods before OR-Tools runs. Allergens, avoided ingredients, excluded categories and IDs, dietary rules, spice limits, and strict cuisine requirements cannot be outweighed by the optimizer. Required foods and categories become CP-SAT selection constraints.

Soft preferences produce a bounded score from cuisine, category, ingredient, flavor, and dislike matches. CP-SAT uses that score below nutrition feasibility and target-deviation priorities. This changes ties and near-equivalent choices without bypassing hard rules.

## Trusted metadata

The initial schema adds PostgreSQL arrays for cuisine, dietary, allergen, ingredient, and flavor tags, plus `spice_level` and `is_cuisine_neutral`. Arrays are the smallest useful change for the current catalog; normalized tag tables may be justified later when tags need administration, translations, or richer relationships.

Tags are lowercase identifiers. Foods can have several cuisines. Cuisine behavior is explicit:

- `strict`: only a requested cuisine tag is eligible.
- `compatible`: requested cuisine tags and trusted neutral staples are eligible. This is the default.
- `preference`: cuisine matches receive a soft score; other safe foods remain eligible.

Neutral compatibility is stored per food rather than inferred from its name. `data/food_preference_metadata.csv` contains a deliberately small reviewed starter set, including the Greek/peanut example. Untagged foods are not assumed safe for a dietary rule or compatible with a requested cuisine. Catalog metadata must be expanded and reviewed before broad production use.

## Provider behavior and privacy

`PreferenceProvider` isolates the parser from a vendor. The included implementation calls an OpenAI-compatible chat-completions endpoint with JSON output, a bounded timeout, and bounded retries. Missing configuration and provider failures return controlled errors. Raw prompts and keys are not logged.

Parsing is request-scoped and is never saved automatically. Ambiguous safety-relevant requests may return one clarification question. The frontend displays the structured interpretation and lets the user remove tags or change cuisine mode before generation.

## Limitations

Metadata quality determines enforcement quality. The parser cannot establish that an untagged food is allergen-safe. The current starter metadata is intentionally limited, texture and preparation fields are parsed but not yet backed by food metadata, and there is no permanent preference learning. Production should add provider monitoring, rate limiting, metadata review workflows, and appropriate privacy/vendor agreements.

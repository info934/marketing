# Creative Intelligence Memory

This app now stores each generation as a learning record:

product -> campaign -> creative -> rating -> performance -> recommendations

The current MVP uses local SQLite at `data/creative_memory.sqlite`. The schema is intentionally close to a future PostgreSQL + pgvector setup, so the storage layer can be replaced without changing the UI or generation workflow.

## Tables

- `products`: product name, category, market, language, facts, references, audience, positioning
- `campaigns`: platform, market, goal, creative strategy, session folder
- `creatives`: video/static/carousel records, angle, final prompt, negative prompt, model, asset URL, cost
- `ratings`: user rating, fidelity, realism, hook, brand fit, comment, approved/rejected
- `performance`: CTR, CPC, CPA, ROAS, spend, impressions, clicks, conversions
- `knowledge_items`: generated prompts, ratings, rejected notes and performance signals converted into retrievable learning items with tags, score and a vector-ready semantic fingerprint

## Runtime Flow

1. Product and prompt agents generate a creative set.
2. `creative_memory_db.retrieve_guidance()` looks for similar category/market/platform records and ranks them by score + semantic fingerprint similarity.
3. Guidance is injected into prompt-model payloads, Structured Prompt Architecture V2 and static image prompts as `creative_memory_guidance`.
4. After generation, `creative_memory_db.save_generation()` stores the full product/campaign/creative record.
5. The UI shows Creative Intelligence with rating controls.
6. Ratings and imported performance data become guidance for later generations.

## API

- `GET /creative-intelligence`: summary of memory counts, recommendations, recent creatives and performance leaders
- `POST /creative-rating`: save fidelity, realism, hook, brand fit, overall score and approve/reject state
- `POST /performance-import`: import ad metrics for a creative

## Learning Signals

- Approved ratings become `approved` knowledge.
- Rejected ratings become `rejected` knowledge and are used as avoid patterns.
- ROAS/CTR winners become `performance_winner` knowledge.
- Weak performance can become `performance_loser` knowledge.
- Generated prompts are still stored, but with lower score until rating/performance confirms them.

## Next Storage Upgrade

Recommended production path:

1. Move SQLite tables to PostgreSQL.
2. Add `pgvector`.
3. Store embeddings for prompts, comments, performance summaries and product facts.
4. Replace the current lexical retrieval in `retrieve_guidance()` with vector similarity plus filters:
   category, market, platform, audience, angle and product type.

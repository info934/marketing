-- PostgreSQL + pgvector target schema for Creative Intelligence Memory.
-- The local MVP currently uses SQLite, but these tables mirror the app storage model.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS products (
  product_id text PRIMARY KEY,
  product_name text NOT NULL,
  category text,
  market text,
  language text,
  product_facts jsonb,
  reference_images jsonb,
  target_audience text,
  positioning text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS campaigns (
  campaign_id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES products(product_id),
  platform text,
  market text,
  goal text,
  creative_strategy jsonb,
  session_folder text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS creatives (
  creative_id text PRIMARY KEY,
  campaign_id text NOT NULL REFERENCES campaigns(campaign_id),
  set_id text,
  type text,
  angle text,
  prompt text,
  negative_prompt text,
  model_used text,
  asset_url text,
  generation_cost numeric,
  status text,
  source_payload jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ratings (
  rating_id text PRIMARY KEY,
  creative_id text NOT NULL REFERENCES creatives(creative_id),
  user_rating int,
  fidelity_score int,
  realism_score int,
  hook_score int,
  brand_fit_score int,
  comment text,
  status text,
  reasons jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS performance (
  performance_id text PRIMARY KEY,
  creative_id text NOT NULL REFERENCES creatives(creative_id),
  ctr numeric,
  cpc numeric,
  cpa numeric,
  roas numeric,
  spend numeric,
  impressions int,
  clicks int,
  conversions int,
  platform text,
  date_range text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_items (
  item_id text PRIMARY KEY,
  source_type text NOT NULL,
  source_id text NOT NULL,
  product_id text REFERENCES products(product_id),
  campaign_id text REFERENCES campaigns(campaign_id),
  creative_id text REFERENCES creatives(creative_id),
  category text,
  market text,
  platform text,
  angle text,
  status text,
  content text NOT NULL,
  tags jsonb,
  score numeric,
  embedding vector(1536),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS knowledge_items_embedding_idx
  ON knowledge_items USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS knowledge_items_lookup_idx
  ON knowledge_items(category, market, platform, status, angle);

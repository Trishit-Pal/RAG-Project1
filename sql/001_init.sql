create extension if not exists vector;

create type source_kind as enum('upload', 'api');
create type doc_status as enum('pending', 'validated','quarantined','indexed', 'failed');

create table sources (
  id            uuid primary key default gen_random_uuid(),
  name          text not null unique,
  kind          source_kind not null,
  uri           text,
  quality_score real check (quality_score between 0 and 1),
  created_at    timestamptz not null default now()
);

create table documents (
  id             uuid primary key default gen_random_uuid(),
  source_id      uuid not null references sources(id) on delete cascade,
  content_sha256 char(64) not null unique,
  filename       text,
  mime_type      text not null,
  byte_size      integer not null check (byte_size >= 0),
  status         doc_status not null default 'pending',
  ingested_at    timestamptz not null default now()
);

create table chunks (
  id             bigint generated always as identity primary key,
  document_id    uuid not null references documents(id) on delete cascade,
  chunk_index    integer not null,
  content_sha256 char(64) not null,
  text           text not null,
  embedding      vector(768) not null,
  tsv            tsvector generated always as (to_tsvector('english', text)) stored,
  metadata       jsonb not null default '{}',
  unique (document_id, chunk_index)
);
create index chunks_embedding_hnsw on chunks using hnsw (embedding vector_cosine_ops);
create index chunks_tsv_gin        on chunks using gin (tsv);
create index chunks_content_sha    on chunks (content_sha256);

create table quarantine (
  id               bigint generated always as identity primary key,
  document_id      uuid not null references documents(id) on delete cascade,
  locator          text not null,
  rule             text not null,
  severity         text not null check (severity in ('error', 'warning')),
  reason           text not null,
  payload_redacted jsonb,
  created_at       timestamptz not null default now()
);

create table quality_runs (
  id              bigint generated always as identity primary key,
  source_id       uuid not null references sources(id) on delete cascade,
  run_at          timestamptz not null default now(),
  rows_in         integer not null,
  rows_passed     integer not null,
  completeness    real,
  duplicate_rate  real,
  freshness_hours real,
  drift_detected  boolean not null default false,
  score           real not null check (score between 0 and 1),
  details         jsonb not null default '{}'
);

create table query_traces (
  id            uuid primary key default gen_random_uuid(),
  question      text not null,
  answer        text,
  chunk_ids     bigint[] not null default '{}',
  provider      text not null,
  model         text not null,
  latency_ms    integer,
  input_tokens  integer,
  output_tokens integer,
  created_at    timestamptz not null default now()
);

create table eval_cases (
  id                  bigint generated always as identity primary key,
  question            text not null,
  expected_source_ids uuid[] not null,
  reference_answer    text
);

create table eval_runs (
  id      bigint generated always as identity primary key,
  git_sha text not null,
  run_at  timestamptz not null default now(),
  metrics jsonb not null,
  passed  boolean not null
);

alter table sources      enable row level security;
alter table documents    enable row level security;
alter table chunks       enable row level security;
alter table quarantine   enable row level security;
alter table quality_runs enable row level security;
alter table query_traces enable row level security;
alter table eval_cases   enable row level security;
alter table eval_runs    enable row level security;
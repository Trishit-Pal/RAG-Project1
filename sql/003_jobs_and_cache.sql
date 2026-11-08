-- Answer cache, embedding bookkeeping and the (not yet used) ingest job queue.
-- Copied from the live Supabase database. Safe to run more than once.

-- Which embedding model produced each document's vectors.
alter table documents add column if not exists embedding_model text    not null default 'gemini-embedding-2';
alter table documents add column if not exists embedding_dim   integer not null default 768;

-- One row that counts how many times the corpus changed.
-- core/ingest.py adds 1 after each successful ingest, which invalidates cached answers.
create table if not exists corpus_state (
  id             integer primary key check (id = 1),
  corpus_version bigint  not null default 0
);
insert into corpus_state (id, corpus_version) values (1, 0) on conflict (id) do nothing;

-- Cache lookup: same question, same corpus version.
alter table query_traces add column if not exists question_key   text;
alter table query_traces add column if not exists corpus_version bigint;
create index if not exists query_traces_cache on query_traces (question_key, corpus_version);

-- Background ingest jobs. Nothing writes to this table yet.
do $$ begin
  create type job_status as enum ('queued', 'running', 'done', 'failed');
exception when duplicate_object then null; end $$;

create table if not exists ingest_jobs (
  id           uuid primary key default gen_random_uuid(),
  kind         text not null check (kind in ('file', 'api_refresh')),
  source_id    uuid not null references sources(id) on delete cascade,
  storage_path text,
  status       job_status not null default 'queued',
  error        text,
  created_at   timestamptz not null default now(),
  started_at   timestamptz,
  finished_at  timestamptz
);

alter table corpus_state enable row level security;
alter table ingest_jobs  enable row level security;

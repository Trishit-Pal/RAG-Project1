-- Nearest-neighbour search used by core/retrieve.py.
-- Copied from the live Supabase database, so a fresh database matches it.
-- Safe to run more than once ("create or replace").
--
-- How it works:
--   1. Take the match_count * 4 closest chunks by cosine distance (fast, uses the HNSW index).
--   2. Drop chunks whose source has a quality score below min_quality.
--   3. Return the best match_count of what is left.
-- similarity = 1 - cosine distance, so 1.0 means identical direction.

create or replace function public.match_chunks(
  query_embedding vector,
  match_count     integer default 6,
  min_quality     real    default 0
)
returns table (
  chunk_id       bigint,
  document_id    uuid,
  text           text,
  similarity     real,
  source_quality real
)
language sql
stable
as $$
  with candidates as (
    select c.id, c.document_id, c.text,
           1 - (c.embedding <=> query_embedding) as similarity
    from chunks c
    order by c.embedding <=> query_embedding
    limit match_count * 4
  )
  select cand.id, cand.document_id, cand.text,
         cand.similarity::real, s.quality_score
  from candidates cand
  join documents d on d.id = cand.document_id
  join sources   s on s.id = d.source_id
  where coalesce(s.quality_score, 0) >= min_quality
  order by cand.similarity desc
  limit match_count;
$$;

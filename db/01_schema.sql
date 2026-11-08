-- Initial schema for the Acupressure Recommendation App.
-- Plain SQL, applied in file-name order by `make db-setup` (no migration framework).
-- Safe to re-run: objects are created only if missing.

create extension if not exists vector with schema extensions;

-- ---------------------------------------------------------------------------
-- Curated knowledge (read by authenticated users, written by backend/ingestion)
-- ---------------------------------------------------------------------------

create table if not exists public.symptom_categories (
    id          text primary key,              -- slug, e.g. 'headache'
    name        text not null,
    description text not null default ''
);

create table if not exists public.points (
    id                text primary key,        -- standard point code, e.g. 'LI4'
    name              text not null,
    location_text     text not null,           -- always present: fallback when there is no image
    image_path        text,                    -- Supabase Storage object path or permitted URL
    image_attribution text,                    -- required when image_path is set
    image_license     text,                    -- usage permission / licence for the image
    instructions      text[] not null check (cardinality(instructions) > 0), -- ordered steps
    duration          text,                    -- only when stated by the curated source
    pressure          text,                    -- only when stated by the curated source
    created_at        timestamptz not null default now(),
    constraint image_needs_attribution
        check (image_path is null or (image_attribution is not null and image_license is not null))
);

create table if not exists public.point_categories (
    point_id    text not null references public.points (id) on delete cascade,
    category_id text not null references public.symptom_categories (id) on delete cascade,
    primary key (point_id, category_id)
);

create table if not exists public.sources (
    id         bigint generated always as identity primary key,
    title      text not null,
    author     text,
    url        text,
    language   text not null default 'en',     -- ISO 639-1 code of the original document
    license    text,
    created_at timestamptz not null default now()
);

create table if not exists public.knowledge_chunks (
    id          bigint generated always as identity primary key,
    source_id   bigint not null references public.sources (id) on delete cascade,
    point_id    text references public.points (id) on delete set null,
    page        integer,                       -- page in the original document, when known
    language    text not null default 'en',    -- language of `content` (after translation)
    content     text not null,
    embedding   extensions.vector(1024) not null, -- Amazon Titan Text Embeddings V2
    created_at  timestamptz not null default now()
);

create index if not exists knowledge_chunks_embedding_idx
    on public.knowledge_chunks using hnsw (embedding extensions.vector_cosine_ops);

-- ---------------------------------------------------------------------------
-- User data (private to the owning user; removed when the user is deleted)
-- ---------------------------------------------------------------------------

create table if not exists public.recommendation_attempts (
    id                     uuid primary key default gen_random_uuid(),
    user_id                uuid not null references auth.users (id) on delete cascade,
    symptom_text           text not null,      -- stored exactly as entered
    clarification_question text,
    clarification_answer   text,
    category_ids           text[] not null default '{}',
    outcome                text not null default 'pending'
        check (outcome in ('pending', 'recommended', 'clarification_needed', 'no_match', 'failed')),
    created_at             timestamptz not null default now(),
    updated_at             timestamptz not null default now()
);

create index if not exists recommendation_attempts_user_idx
    on public.recommendation_attempts (user_id);

create table if not exists public.recommendation_points (
    attempt_id uuid not null references public.recommendation_attempts (id) on delete cascade,
    point_id   text not null references public.points (id),
    rank       smallint not null check (rank between 1 and 3),
    primary key (attempt_id, point_id),
    unique (attempt_id, rank)
);

create table if not exists public.point_ratings (
    attempt_id uuid not null,
    point_id   text not null,
    user_id    uuid not null references auth.users (id) on delete cascade,
    rating     smallint not null check (rating between 1 and 5),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (attempt_id, point_id),
    foreign key (attempt_id, point_id)
        references public.recommendation_points (attempt_id, point_id) on delete cascade
);

create index if not exists point_ratings_point_idx on public.point_ratings (point_id);

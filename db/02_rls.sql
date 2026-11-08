-- Row Level Security for all public tables.
--
-- * Curated content: readable by signed-in users; written only by privileged
--   backend/ingestion connections (postgres / service_role bypass RLS).
-- * User data: each user can read only their own rows. Users cannot write
--   through the Supabase API at all; the backend validates and writes on their
--   behalf, so the public anon key cannot be used to bypass API validation.
-- * The anon role has no policies, so it sees nothing.
-- Safe to re-run: policies are dropped and recreated.

alter table public.symptom_categories      enable row level security;
alter table public.points                  enable row level security;
alter table public.point_categories        enable row level security;
alter table public.sources                 enable row level security;
alter table public.knowledge_chunks        enable row level security;
alter table public.recommendation_attempts enable row level security;
alter table public.recommendation_points   enable row level security;
alter table public.point_ratings           enable row level security;

-- Curated content -----------------------------------------------------------

drop policy if exists "Signed-in users can read categories" on public.symptom_categories;
create policy "Signed-in users can read categories" on public.symptom_categories
    for select to authenticated using (true);

drop policy if exists "Signed-in users can read points" on public.points;
create policy "Signed-in users can read points" on public.points
    for select to authenticated using (true);

drop policy if exists "Signed-in users can read point categories" on public.point_categories;
create policy "Signed-in users can read point categories" on public.point_categories
    for select to authenticated using (true);

drop policy if exists "Signed-in users can read sources" on public.sources;
create policy "Signed-in users can read sources" on public.sources
    for select to authenticated using (true);

drop policy if exists "Signed-in users can read knowledge chunks" on public.knowledge_chunks;
create policy "Signed-in users can read knowledge chunks" on public.knowledge_chunks
    for select to authenticated using (true);

-- User data -----------------------------------------------------------------

drop policy if exists "Users can read their own attempts" on public.recommendation_attempts;
create policy "Users can read their own attempts" on public.recommendation_attempts
    for select to authenticated using (user_id = (select auth.uid()));

drop policy if exists "Users can read their own recommendation points" on public.recommendation_points;
create policy "Users can read their own recommendation points" on public.recommendation_points
    for select to authenticated using (
        exists (
            select 1 from public.recommendation_attempts a
            where a.id = attempt_id and a.user_id = (select auth.uid())
        )
    );

drop policy if exists "Users can read their own ratings" on public.point_ratings;
create policy "Users can read their own ratings" on public.point_ratings
    for select to authenticated using (user_id = (select auth.uid()));

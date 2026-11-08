-- Storage bucket for curated point-location images.
-- Images are curated, non-personal content, so the bucket is public-read;
-- uploads require the service role (backend/ingestion only).
-- Safe to re-run.

insert into storage.buckets (id, name, public)
values ('point-images', 'point-images', true)
on conflict (id) do nothing;

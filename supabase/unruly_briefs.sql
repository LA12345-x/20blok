-- Unruly Reels: creative briefs + client files. Run once in Supabase → SQL Editor (20 Blok project).
-- Briefs are sent from unrulyreels.com/brief after a client pays the deposit.
-- Clients get a quiet anonymous session (Turnstile-checked) so they can upload into their own folder.
-- Only admins (is_admin(), from comments.sql) can read or delete briefs and files.

-- Briefs
create table if not exists public.briefs (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null default auth.uid(),
  brand      text check (char_length(brand) <= 120),
  name       text check (char_length(name) <= 120),
  email      text check (char_length(email) <= 254),
  answers    jsonb not null default '{}'::jsonb,
  files      jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  constraint briefs_answers_size check (pg_column_size(answers) < 30000)
);
alter table public.briefs enable row level security;
drop policy if exists "clients send briefs" on public.briefs;
drop policy if exists "admins read briefs" on public.briefs;
drop policy if exists "admins delete briefs" on public.briefs;
create policy "clients send briefs" on public.briefs for insert to authenticated with check (user_id = auth.uid());
create policy "admins read briefs" on public.briefs for select to authenticated using (public.is_admin());
create policy "admins delete briefs" on public.briefs for delete to authenticated using (public.is_admin());

-- One brief every 30 seconds per visitor
create or replace function public.briefs_rate_limit() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if exists (select 1 from public.briefs b where b.user_id = new.user_id and b.created_at > now() - interval '30 seconds') then
    raise exception 'slow down';
  end if;
  return new;
end $$;
drop trigger if exists briefs_rate_limit on public.briefs;
create trigger briefs_rate_limit before insert on public.briefs for each row execute function public.briefs_rate_limit();

-- Private file storage: 50 MB per file (the free plan's cap), any file type
insert into storage.buckets (id, name, public, file_size_limit)
values ('unruly-briefs', 'unruly-briefs', false, 52428800)
on conflict (id) do update set public = false, file_size_limit = 52428800;

drop policy if exists "clients upload brief files" on storage.objects;
drop policy if exists "admins read brief files" on storage.objects;
drop policy if exists "admins delete brief files" on storage.objects;
create policy "clients upload brief files" on storage.objects for insert to authenticated
  with check (bucket_id = 'unruly-briefs' and (storage.foldername(name))[1] = auth.uid()::text);
create policy "admins read brief files" on storage.objects for select to authenticated
  using (bucket_id = 'unruly-briefs' and public.is_admin());
create policy "admins delete brief files" on storage.objects for delete to authenticated
  using (bucket_id = 'unruly-briefs' and public.is_admin());

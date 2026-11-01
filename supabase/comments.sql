-- 20 Blok: comments (Pass 2). Run once in Supabase → SQL Editor.
-- Who can comment: signed-in, verified readers only (Google or email link). No anonymous comments.
-- Admins (delete any comment, block people): listed in is_admin() below.

-- Admin check
create or replace function public.is_admin() returns boolean
language sql stable as $$
  select coalesce(auth.jwt() ->> 'email', '') in ('soundsoflife@gmail.com', 'lennybusinessnow@gmail.com')
     and coalesce((auth.jwt() ->> 'is_anonymous')::boolean, false) = false;
$$;

-- People blocked from commenting
create table if not exists public.blocked (
  user_id    uuid primary key,
  note       text,
  created_at timestamptz not null default now()
);
alter table public.blocked enable row level security;
drop policy if exists "admins manage blocks" on public.blocked;
create policy "admins manage blocks" on public.blocked for all to authenticated using (public.is_admin()) with check (public.is_admin());

-- Comments
create table if not exists public.comments (
  id         uuid primary key default gen_random_uuid(),
  issue      int  not null,
  blok       text not null check (char_length(blok) between 1 and 40),
  user_id    uuid not null default auth.uid(),
  name       text not null check (char_length(name) between 1 and 40),
  body       text not null check (char_length(body) between 1 and 600),
  created_at timestamptz not null default now()
);
create index if not exists comments_blok_idx on public.comments (issue, blok, created_at);
alter table public.comments enable row level security;

drop policy if exists "read comments" on public.comments;
drop policy if exists "verified readers comment" on public.comments;
drop policy if exists "delete own or admin" on public.comments;
create policy "read comments" on public.comments for select using (true);
create policy "verified readers comment" on public.comments for insert to authenticated with check (
  user_id = auth.uid()
  and coalesce((auth.jwt() ->> 'is_anonymous')::boolean, false) = false
  and coalesce(auth.jwt() ->> 'email', '') <> ''
  and not exists (select 1 from public.blocked b where b.user_id = auth.uid())
);
create policy "delete own or admin" on public.comments for delete to authenticated using (user_id = auth.uid() or public.is_admin());

-- Slow down spam: one comment every 15 seconds per person
create or replace function public.comments_rate_limit() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if exists (select 1 from public.comments c where c.user_id = new.user_id and c.created_at > now() - interval '15 seconds') then
    raise exception 'slow down';
  end if;
  return new;
end $$;
drop trigger if exists comments_rate_limit on public.comments;
create trigger comments_rate_limit before insert on public.comments for each row execute function public.comments_rate_limit();

-- Live updates on the page
do $$ begin
  alter publication supabase_realtime add table public.comments;
exception when duplicate_object then null; end $$;

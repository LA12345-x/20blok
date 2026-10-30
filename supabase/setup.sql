-- 20 Blok: votes (Pass 1). Run once in Supabase → SQL Editor.
create table if not exists public.votes (
  issue      int  not null,
  blok       text not null check (char_length(blok) between 1 and 40),
  voter      uuid not null default auth.uid(),
  created_at timestamptz not null default now(),
  primary key (issue, blok, voter)
);
alter table public.votes enable row level security;
drop policy if exists "read votes" on public.votes;
drop policy if exists "vote as yourself" on public.votes;
drop policy if exists "remove your own vote" on public.votes;
create policy "read votes" on public.votes for select using (true);
create policy "vote as yourself" on public.votes for insert to authenticated with check (voter = auth.uid());
create policy "remove your own vote" on public.votes for delete to authenticated using (voter = auth.uid());
alter publication supabase_realtime add table public.votes;

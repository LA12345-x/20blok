-- 20 Blok: feedback box + contact page messages. Run once in Supabase → SQL Editor.
-- Anyone can send (no sign-in needed). Only admins can read or delete.
create table if not exists public.messages (
  id         uuid primary key default gen_random_uuid(),
  kind       text not null check (kind in ('feedback','inquiry')),
  topic      text check (char_length(topic) <= 40),
  read_freq  text check (char_length(read_freq) <= 20),
  name       text check (char_length(name) <= 80),
  email      text check (char_length(email) <= 254),
  body       text check (char_length(body) <= 3000),
  pitch      boolean not null default false,
  sender     uuid default auth.uid(),
  created_at timestamptz not null default now(),
  check (email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$')
);
alter table public.messages enable row level security;
drop policy if exists "anyone can send" on public.messages;
drop policy if exists "admins read" on public.messages;
drop policy if exists "admins delete" on public.messages;
create policy "anyone can send" on public.messages for insert to anon, authenticated with check (true);
create policy "admins read" on public.messages for select to authenticated using (public.is_admin());
create policy "admins delete" on public.messages for delete to authenticated using (public.is_admin());

create or replace function public.messages_rate_limit() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.sender is not null and exists (select 1 from public.messages m where m.sender = new.sender and m.created_at > now() - interval '20 seconds') then
    raise exception 'slow down';
  end if;
  return new;
end $$;
drop trigger if exists messages_rate_limit on public.messages;
create trigger messages_rate_limit before insert on public.messages for each row execute function public.messages_rate_limit();

-- Added Nov 1: which bloks the reader enjoys (feedback page picker)
alter table public.messages add column if not exists bloks text[];
do $$ declare c text; begin
  for c in select conname from pg_constraint where conrelid = 'public.messages'::regclass and contype = 'c'
           and pg_get_constraintdef(oid) like '%body%' and pg_get_constraintdef(oid) like '%read_freq%' loop
    execute format('alter table public.messages drop constraint %I', c);
  end loop;
end $$;
alter table public.messages drop constraint if exists messages_has_content;
alter table public.messages add constraint messages_has_content check (coalesce(body,'') <> '' or coalesce(read_freq,'') <> '' or coalesce(array_length(bloks,1),0) > 0);

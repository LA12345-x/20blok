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
  check (coalesce(body,'') <> '' or coalesce(read_freq,'') <> ''),
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

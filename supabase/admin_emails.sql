-- 20 Blok: let the admin page show each commenter's email (admins only). Run once in Supabase → SQL Editor.
create or replace function public.admin_comment_emails(ids uuid[])
returns table(user_id uuid, email text)
language sql stable security definer set search_path = public, auth as $$
  select u.id, u.email::text from auth.users u where public.is_admin() and u.id = any(ids);
$$;
revoke all on function public.admin_comment_emails(uuid[]) from public, anon;
grant execute on function public.admin_comment_emails(uuid[]) to authenticated;

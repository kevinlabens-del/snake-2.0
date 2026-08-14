begin;

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

create table if not exists private.snake2_level_runs (
  run_id uuid primary key,
  visitor_id uuid not null,
  session_id uuid not null,
  level integer not null check (level between 1 and 2147483647),
  is_daily boolean not null default false,
  client_started_at timestamptz not null,
  started_at timestamptz not null default now(),
  completion_event_id uuid unique,
  client_completed_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table private.snake2_level_runs enable row level security;
revoke all on table private.snake2_level_runs from public, anon, authenticated;

create index if not exists snake2_level_runs_visitor_completed_idx
  on private.snake2_level_runs (visitor_id, completed_at desc);
create index if not exists snake2_level_runs_visitor_client_completed_idx
  on private.snake2_level_runs (visitor_id, client_completed_at desc)
  where client_completed_at is not null;
create index if not exists snake2_level_runs_started_idx
  on private.snake2_level_runs (started_at);
create index if not exists snake2_presence_last_seen_idx
  on public.snake2_presence (last_seen);

create or replace function public.snake2_stats_json()
returns jsonb
language sql
stable
security invoker
set search_path = ''
as $function$
  select coalesce(
    (
      select jsonb_build_object(
        'visitors', coalesce(total_visitors, 0),
        'games', coalesce(total_games, 0),
        'online', coalesce(total_online, 0)
      )
      from public.snake2_stats
      where id = 1
    ),
    jsonb_build_object('visitors', 0, 'games', 0, 'online', 0)
  );
$function$;

create or replace function public.snake2_get_stats()
returns jsonb
language sql
stable
security invoker
set search_path = ''
as $function$
  select public.snake2_stats_json();
$function$;

create or replace function public.snake2_register_visitor(p_visitor_id text)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
declare
  inserted_count integer := 0;
begin
  if p_visitor_id is null or p_visitor_id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' then
    raise exception using errcode = '22023', message = 'invalid visitor id';
  end if;

  insert into public.snake2_visitors(visitor_id)
  values (lower(p_visitor_id))
  on conflict (visitor_id) do nothing;
  get diagnostics inserted_count = row_count;

  if inserted_count > 0 then
    update public.snake2_stats
    set total_visitors = total_visitors + 1,
        updated_at = now()
    where id = 1;
  end if;

  return public.snake2_stats_json();
end;
$function$;

create or replace function public.snake2_recompute_online()
returns bigint
language plpgsql
security definer
set search_path = ''
as $function$
declare
  online_count bigint := 0;
begin
  delete from public.snake2_presence
  where visitor_id is null
     or last_seen < now() - interval '45 seconds';

  select count(distinct visitor_id)::bigint
  into online_count
  from public.snake2_presence
  where visitor_id is not null
    and last_seen >= now() - interval '45 seconds';

  update public.snake2_stats
  set total_online = coalesce(online_count, 0),
      updated_at = now()
  where id = 1
    and total_online is distinct from coalesce(online_count, 0);

  delete from private.snake2_level_runs
  where (completed_at is null and started_at < now() - interval '7 days')
     or (completed_at < now() - interval '180 days');

  return coalesce(online_count, 0);
end;
$function$;

create or replace function public.snake2_heartbeat(
  p_session_id text,
  p_visitor_id text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
begin
  if p_session_id is null or p_session_id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' then
    raise exception using errcode = '22023', message = 'invalid session id';
  end if;
  if p_visitor_id is null or p_visitor_id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' then
    raise exception using errcode = '22023', message = 'invalid visitor id';
  end if;

  perform public.snake2_register_visitor(lower(p_visitor_id));

  insert into public.snake2_presence(session_id, visitor_id, last_seen)
  values (lower(p_session_id), lower(p_visitor_id), now())
  on conflict (session_id) do update
  set visitor_id = excluded.visitor_id,
      last_seen = excluded.last_seen;

  perform public.snake2_recompute_online();
  return public.snake2_stats_json();
end;
$function$;

create or replace function public.snake2_leave(
  p_session_id text,
  p_visitor_id text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
begin
  if p_session_id is null or p_session_id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' then
    raise exception using errcode = '22023', message = 'invalid session id';
  end if;
  if p_visitor_id is null or p_visitor_id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' then
    raise exception using errcode = '22023', message = 'invalid visitor id';
  end if;

  delete from public.snake2_presence
  where session_id = lower(p_session_id)
    and visitor_id = lower(p_visitor_id);

  perform public.snake2_recompute_online();
  return public.snake2_stats_json();
end;
$function$;

create or replace function public.snake2_level_started(
  p_run_id uuid,
  p_session_id uuid,
  p_visitor_id uuid,
  p_level integer,
  p_is_daily boolean,
  p_mark_online boolean,
  p_client_started_at timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
declare
  inserted_count integer := 0;
  existing_run private.snake2_level_runs%rowtype;
begin
  if p_run_id is null or p_session_id is null or p_visitor_id is null then
    raise exception using errcode = '22023', message = 'missing level identifiers';
  end if;
  if p_level is null or p_level < 1 then
    raise exception using errcode = '22023', message = 'invalid level';
  end if;
  if p_client_started_at is null
     or p_client_started_at < now() - interval '30 days'
     or p_client_started_at > now() + interval '10 minutes' then
    raise exception using errcode = '22023', message = 'invalid level start time';
  end if;

  if coalesce(p_mark_online, false) then
    perform public.snake2_heartbeat(p_session_id::text, p_visitor_id::text);
  else
    perform public.snake2_register_visitor(p_visitor_id::text);
  end if;

  insert into private.snake2_level_runs(
    run_id, visitor_id, session_id, level, is_daily, client_started_at
  ) values (
    p_run_id, p_visitor_id, p_session_id, p_level, coalesce(p_is_daily, false), p_client_started_at
  )
  on conflict (run_id) do nothing;
  get diagnostics inserted_count = row_count;

  if inserted_count = 0 then
    select * into existing_run
    from private.snake2_level_runs
    where run_id = p_run_id;

    if existing_run.visitor_id is distinct from p_visitor_id
       or existing_run.session_id is distinct from p_session_id
       or existing_run.level is distinct from p_level
       or existing_run.is_daily is distinct from coalesce(p_is_daily, false)
       or existing_run.client_started_at is distinct from p_client_started_at then
      return public.snake2_stats_json() || jsonb_build_object(
        'accepted', false,
        'duplicate', false,
        'reason', 'run_mismatch'
      );
    end if;
  end if;

  return public.snake2_stats_json() || jsonb_build_object(
    'accepted', true,
    'duplicate', inserted_count = 0,
    'run_id', p_run_id
  );
end;
$function$;

create or replace function public.snake2_level_completed(
  p_run_id uuid,
  p_event_id uuid,
  p_session_id uuid,
  p_visitor_id uuid,
  p_level integer,
  p_is_daily boolean,
  p_client_started_at timestamptz,
  p_client_completed_at timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
declare
  run_record private.snake2_level_runs%rowtype;
  completed_last_day integer := 0;
begin
  if p_run_id is null or p_event_id is null or p_session_id is null or p_visitor_id is null then
    raise exception using errcode = '22023', message = 'missing completion identifiers';
  end if;
  if p_level is null or p_level < 1 then
    raise exception using errcode = '22023', message = 'invalid level';
  end if;
  if p_client_started_at is null or p_client_completed_at is null
     or p_client_completed_at <= p_client_started_at
     or p_client_completed_at - p_client_started_at < interval '1 second'
     or p_client_completed_at - p_client_started_at > interval '7 days'
     or p_client_completed_at < now() - interval '30 days'
     or p_client_completed_at > now() + interval '10 minutes' then
    return public.snake2_stats_json() || jsonb_build_object(
      'accepted', false,
      'duplicate', false,
      'reason', 'invalid_duration'
    );
  end if;

  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(p_visitor_id::text, 0));

  select * into run_record
  from private.snake2_level_runs
  where run_id = p_run_id
  for update;

  if not found then
    return public.snake2_stats_json() || jsonb_build_object(
      'accepted', false,
      'duplicate', false,
      'reason', 'run_not_found'
    );
  end if;

  if run_record.visitor_id is distinct from p_visitor_id
     or run_record.session_id is distinct from p_session_id
     or run_record.level is distinct from p_level
     or run_record.is_daily is distinct from coalesce(p_is_daily, false)
     or run_record.client_started_at is distinct from p_client_started_at then
    return public.snake2_stats_json() || jsonb_build_object(
      'accepted', false,
      'duplicate', false,
      'reason', 'run_mismatch'
    );
  end if;

  if run_record.completed_at is not null then
    return public.snake2_stats_json() || jsonb_build_object(
      'accepted', true,
      'duplicate', true,
      'run_id', p_run_id
    );
  end if;

  if exists (
    select 1
    from private.snake2_level_runs
    where completion_event_id = p_event_id
      and run_id <> p_run_id
  ) then
    return public.snake2_stats_json() || jsonb_build_object(
      'accepted', false,
      'duplicate', false,
      'reason', 'event_conflict'
    );
  end if;

  if exists (
    select 1
    from private.snake2_level_runs
    where visitor_id = p_visitor_id
      and client_completed_at between p_client_completed_at - interval '1 second'
                                  and p_client_completed_at + interval '1 second'
  ) then
    return public.snake2_stats_json() || jsonb_build_object(
      'accepted', false,
      'duplicate', false,
      'reason', 'rate_limited'
    );
  end if;

  select count(*) into completed_last_day
  from private.snake2_level_runs
  where visitor_id = p_visitor_id
    and completed_at >= now() - interval '24 hours';

  if completed_last_day >= 500 then
    return public.snake2_stats_json() || jsonb_build_object(
      'accepted', false,
      'duplicate', false,
      'reason', 'daily_limit'
    );
  end if;

  update private.snake2_level_runs
  set completion_event_id = p_event_id,
      client_completed_at = p_client_completed_at,
      completed_at = now(),
      updated_at = now()
  where run_id = p_run_id;

  update public.snake2_stats
  set total_games = total_games + 1,
      updated_at = now()
  where id = 1;

  return public.snake2_stats_json() || jsonb_build_object(
    'accepted', true,
    'duplicate', false,
    'run_id', p_run_id
  );
end;
$function$;

drop function if exists public.snake2_heartbeat(text);
drop function if exists public.snake2_game_started();

revoke all on function public.snake2_stats_json() from public, anon, authenticated, service_role;
revoke all on function public.snake2_get_stats() from public, anon, authenticated, service_role;
revoke all on function public.snake2_register_visitor(text) from public, anon, authenticated, service_role;
revoke all on function public.snake2_recompute_online() from public, anon, authenticated, service_role;
revoke all on function public.snake2_heartbeat(text, text) from public, anon, authenticated, service_role;
revoke all on function public.snake2_leave(text, text) from public, anon, authenticated, service_role;
revoke all on function public.snake2_level_started(uuid, uuid, uuid, integer, boolean, boolean, timestamptz) from public, anon, authenticated, service_role;
revoke all on function public.snake2_level_completed(uuid, uuid, uuid, uuid, integer, boolean, timestamptz, timestamptz) from public, anon, authenticated, service_role;

grant execute on function public.snake2_get_stats() to anon, service_role;
grant execute on function public.snake2_register_visitor(text) to anon, service_role;
grant execute on function public.snake2_heartbeat(text, text) to anon, service_role;
grant execute on function public.snake2_leave(text, text) to anon, service_role;
grant execute on function public.snake2_level_started(uuid, uuid, uuid, integer, boolean, boolean, timestamptz) to anon, service_role;
grant execute on function public.snake2_level_completed(uuid, uuid, uuid, uuid, integer, boolean, timestamptz, timestamptz) to anon, service_role;

create extension if not exists pg_cron with schema pg_catalog;

do $cron$
declare
  existing_job bigint;
begin
  for existing_job in
    select jobid from cron.job where jobname = 'snake2-presence-cleanup-v2'
  loop
    perform cron.unschedule(existing_job);
  end loop;

  perform cron.schedule(
    'snake2-presence-cleanup-v2',
    '15 seconds',
    'select public.snake2_recompute_online();'
  );
end;
$cron$;

select public.snake2_recompute_online();

commit;

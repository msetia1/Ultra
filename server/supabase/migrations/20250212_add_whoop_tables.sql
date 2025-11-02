-- Create WHOOP integration tables for minimal data syncing (cycles, recoveries, sleep, workouts)

create table if not exists public.whoop_cycles (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public."Users"(id) on delete cascade,
    whoop_cycle_id text not null unique,
    cycle_start timestamptz not null,
    cycle_end timestamptz,
    strain numeric,
    average_heart_rate integer,
    max_heart_rate integer,
    kilojoule numeric,
    raw_data jsonb,
    synced_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create index if not exists idx_whoop_cycles_user_synced
    on public.whoop_cycles (user_id, synced_at desc);

create table if not exists public.whoop_recoveries (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public."Users"(id) on delete cascade,
    whoop_cycle_id text not null unique,
    score_state text,
    recovery_score numeric,
    resting_heart_rate numeric,
    hrv_rmssd_milli numeric,
    spo2_percentage numeric,
    skin_temp_celsius numeric,
    raw_data jsonb,
    synced_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create index if not exists idx_whoop_recoveries_user_synced
    on public.whoop_recoveries (user_id, synced_at desc);

create table if not exists public.whoop_sleep (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public."Users"(id) on delete cascade,
    whoop_sleep_id text not null unique,
    whoop_cycle_id text,
    start_time timestamptz not null,
    end_time timestamptz not null,
    nap boolean not null default false,
    score_state text,
    sleep_performance_percentage numeric,
    respiratory_rate numeric,
    light_sleep_milli integer,
    slow_wave_sleep_milli integer,
    rem_sleep_milli integer,
    raw_data jsonb,
    synced_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create index if not exists idx_whoop_sleep_user_synced
    on public.whoop_sleep (user_id, synced_at desc);

create table if not exists public.whoop_workouts (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public."Users"(id) on delete cascade,
    whoop_workout_id text not null unique,
    start_time timestamptz not null,
    end_time timestamptz,
    sport_name text,
    score_state text,
    strain numeric,
    average_heart_rate integer,
    max_heart_rate integer,
    kilojoule numeric,
    zone_zero_milli integer,
    zone_one_milli integer,
    zone_two_milli integer,
    zone_three_milli integer,
    zone_four_milli integer,
    zone_five_milli integer,
    raw_data jsonb,
    synced_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create index if not exists idx_whoop_workouts_user_synced
    on public.whoop_workouts (user_id, synced_at desc);

create table if not exists public.whoop_sync_state (
    user_id uuid primary key references public."Users"(id) on delete cascade,
    last_backfill_start timestamptz,
    last_backfill_end timestamptz,
    last_synced_at timestamptz not null default now(),
    cursor_state jsonb
);


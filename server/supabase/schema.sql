-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.Users (
  id uuid NOT NULL,
  display_name text,
  timezone text,
  has_whoop boolean NOT NULL DEFAULT false,
  has_github boolean NOT NULL DEFAULT false,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT Users_pkey PRIMARY KEY (id)
);
CREATE TABLE public.github_commit_files (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  commit_sha text NOT NULL,
  path text NOT NULL,
  change_type text,
  additions integer,
  deletions integer,
  patch text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT github_commit_files_pkey PRIMARY KEY (id),
  CONSTRAINT github_commit_files_commit_sha_fkey FOREIGN KEY (commit_sha) REFERENCES public.github_commits(sha)
);
CREATE TABLE public.github_commits (
  sha text NOT NULL,
  user_id uuid NOT NULL,
  repo_full_name text NOT NULL,
  branch text,
  authored_at timestamp with time zone NOT NULL,
  committed_at timestamp with time zone,
  message_headline text NOT NULL,
  message_body text,
  additions integer,
  deletions integer,
  total_changes integer,
  raw_payload jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT github_commits_pkey PRIMARY KEY (sha),
  CONSTRAINT github_commits_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(id)
);
CREATE TABLE public.github_integrations (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL UNIQUE,
  github_login text NOT NULL,
  access_token text NOT NULL,
  avatar_url text,
  profile_url text,
  last_synced_at timestamp with time zone NOT NULL DEFAULT now(),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT github_integrations_pkey PRIMARY KEY (id),
  CONSTRAINT github_integrations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(id)
);
CREATE TABLE public.github_repositories (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  repo_full_name text NOT NULL,
  default_branch text,
  include boolean NOT NULL DEFAULT true,
  last_synced_at timestamp with time zone,
  raw_payload jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT github_repositories_pkey PRIMARY KEY (id),
  CONSTRAINT github_repositories_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(id)
);
CREATE TABLE public.whoop (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  whoop_user_id text NOT NULL,
  access_token text NOT NULL,
  refresh_token text NOT NULL,
  expires_at timestamp with time zone NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT whoop_pkey PRIMARY KEY (id),
  CONSTRAINT whoop_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(id)
);
CREATE TABLE public.whoop_cycles (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  whoop_cycle_id text NOT NULL UNIQUE,
  cycle_start timestamp with time zone NOT NULL,
  cycle_end timestamp with time zone,
  strain numeric,
  average_heart_rate integer,
  max_heart_rate integer,
  kilojoule numeric,
  raw_data jsonb,
  synced_at timestamp with time zone NOT NULL DEFAULT now(),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT whoop_cycles_pkey PRIMARY KEY (id),
  CONSTRAINT whoop_cycles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(id)
);
CREATE TABLE public.whoop_recoveries (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  whoop_cycle_id text NOT NULL UNIQUE,
  score_state text,
  recovery_score numeric,
  resting_heart_rate numeric,
  hrv_rmssd_milli numeric,
  spo2_percentage numeric,
  skin_temp_celsius numeric,
  raw_data jsonb,
  synced_at timestamp with time zone NOT NULL DEFAULT now(),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT whoop_recoveries_pkey PRIMARY KEY (id),
  CONSTRAINT whoop_recoveries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(id)
);
CREATE TABLE public.whoop_sleep (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  whoop_sleep_id text NOT NULL UNIQUE,
  whoop_cycle_id text,
  start_time timestamp with time zone NOT NULL,
  end_time timestamp with time zone NOT NULL,
  nap boolean NOT NULL DEFAULT false,
  score_state text,
  sleep_performance_percentage numeric,
  respiratory_rate numeric,
  light_sleep_milli integer,
  slow_wave_sleep_milli integer,
  rem_sleep_milli integer,
  raw_data jsonb,
  synced_at timestamp with time zone NOT NULL DEFAULT now(),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT whoop_sleep_pkey PRIMARY KEY (id),
  CONSTRAINT whoop_sleep_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(id)
);
CREATE TABLE public.whoop_sync_state (
  user_id uuid NOT NULL,
  last_backfill_start timestamp with time zone,
  last_backfill_end timestamp with time zone,
  last_synced_at timestamp with time zone NOT NULL DEFAULT now(),
  cursor_state jsonb,
  CONSTRAINT whoop_sync_state_pkey PRIMARY KEY (user_id),
  CONSTRAINT whoop_sync_state_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(id)
);
CREATE TABLE public.whoop_workouts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  whoop_workout_id text NOT NULL UNIQUE,
  start_time timestamp with time zone NOT NULL,
  end_time timestamp with time zone,
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
  synced_at timestamp with time zone NOT NULL DEFAULT now(),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT whoop_workouts_pkey PRIMARY KEY (id),
  CONSTRAINT whoop_workouts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(id)
);
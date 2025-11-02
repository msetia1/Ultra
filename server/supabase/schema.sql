-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.Users (
  id uuid NOT NULL,
  display_name text,
  timezone text,
  has_whoop boolean NOT NULL DEFAULT false,
  has_github boolean NOT NULL DEFAULT false,
  has_linear boolean NOT NULL DEFAULT false,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT Users_pkey PRIMARY KEY (id),
  CONSTRAINT Users_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id)
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

-- Linear OAuth credentials
CREATE TABLE public.linear_auth (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL UNIQUE,
  linear_user_id text NOT NULL,
  access_token text NOT NULL,
  refresh_token text NOT NULL,
  expires_at timestamp with time zone NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT linear_auth_pkey PRIMARY KEY (id),
  CONSTRAINT linear_auth_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(id)
);

-- Synced Linear issues (denormalized for performance)
CREATE TABLE public.linear_issues (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  linear_issue_id text NOT NULL UNIQUE,
  identifier text NOT NULL,
  title text NOT NULL,
  description text,
  priority integer,
  state_name text,
  state_type text,
  assignee_id text,
  assignee_name text,
  team_id text,
  team_name text,
  project_id text,
  project_name text,
  due_date timestamp with time zone,
  created_at_linear timestamp with time zone,
  updated_at_linear timestamp with time zone,
  completed_at timestamp with time zone,
  canceled_at timestamp with time zone,
  raw_data jsonb,
  synced_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT linear_issues_pkey PRIMARY KEY (id),
  CONSTRAINT linear_issues_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(id)
);

CREATE INDEX idx_linear_issues_user_id ON public.linear_issues(user_id);
CREATE INDEX idx_linear_issues_state_type ON public.linear_issues(user_id, state_type);
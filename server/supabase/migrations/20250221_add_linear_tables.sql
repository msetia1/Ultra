-- Adds Linear integration support: OAuth credentials and synced issues

-- Add has_linear flag to Users table
ALTER TABLE public."Users" 
ADD COLUMN IF NOT EXISTS has_linear boolean NOT NULL DEFAULT false;

-- Linear OAuth credentials table
CREATE TABLE IF NOT EXISTS public.linear_auth (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL UNIQUE,
  linear_user_id text NOT NULL,
  access_token text NOT NULL,
  refresh_token text NOT NULL,
  expires_at timestamp with time zone NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT linear_auth_pkey PRIMARY KEY (id),
  CONSTRAINT linear_auth_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."Users"(id) ON DELETE CASCADE
);

-- Synced Linear issues (denormalized for performance)
CREATE TABLE IF NOT EXISTS public.linear_issues (
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
  CONSTRAINT linear_issues_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."Users"(id) ON DELETE CASCADE
);

-- Indexes for Linear issues
CREATE INDEX IF NOT EXISTS idx_linear_issues_user_id ON public.linear_issues(user_id);
CREATE INDEX IF NOT EXISTS idx_linear_issues_state_type ON public.linear_issues(user_id, state_type);


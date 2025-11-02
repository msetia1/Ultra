-- Adds GitHub integration tables for commits and per-file diffs.

CREATE TABLE public.github_integrations (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  github_login text NOT NULL,
  access_token text NOT NULL,
  avatar_url text,
  profile_url text,
  last_synced_at timestamp with time zone NOT NULL DEFAULT now(),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT github_integrations_pkey PRIMARY KEY (id),
  CONSTRAINT github_integrations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."Users" (id),
  CONSTRAINT github_integrations_user_id_key UNIQUE (user_id)
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
  CONSTRAINT github_commits_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."Users" (id)
);

CREATE INDEX github_commits_user_id_idx ON public.github_commits (user_id);
CREATE INDEX github_commits_repo_idx ON public.github_commits (repo_full_name);

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
  CONSTRAINT github_commit_files_commit_sha_fkey FOREIGN KEY (commit_sha) REFERENCES public.github_commits (sha) ON DELETE CASCADE,
  CONSTRAINT github_commit_files_commit_sha_path_key UNIQUE (commit_sha, path)
);

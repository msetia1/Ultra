-- Creates table to store user-selected GitHub repositories for syncing.

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
  CONSTRAINT github_repositories_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."Users" (id) ON DELETE CASCADE,
  CONSTRAINT github_repositories_user_repo_key UNIQUE (user_id, repo_full_name)
);

CREATE INDEX github_repositories_user_id_idx ON public.github_repositories (user_id);

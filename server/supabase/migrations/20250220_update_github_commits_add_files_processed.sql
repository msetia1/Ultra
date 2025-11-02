-- Adds metadata for tracking commit file ingestion state.

ALTER TABLE public.github_commits
ADD COLUMN IF NOT EXISTS files_processed_at timestamp with time zone,
ADD COLUMN IF NOT EXISTS files_processed_error text;

CREATE INDEX IF NOT EXISTS github_commits_files_pending_idx
ON public.github_commits (user_id, repo_full_name)
WHERE files_processed_at IS NULL;

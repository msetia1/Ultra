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
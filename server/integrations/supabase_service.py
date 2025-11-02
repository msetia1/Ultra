"""Supabase client factory utilities."""

import os
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

_SUPABASE_CLIENT: Optional[Client] = None


def get_supabase() -> Client:
	"""Return a singleton Supabase client configured from environment variables."""
	global _SUPABASE_CLIENT
	if _SUPABASE_CLIENT is None:
		supabase_url = os.environ["SUPABASE_URL"]
		supabase_service_role_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
		_SUPABASE_CLIENT = create_client(supabase_url, supabase_service_role_key)
	return _SUPABASE_CLIENT



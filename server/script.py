from integrations.supabase_service import get_supabase

supabase = get_supabase()

# 1. Create an auth user (skip email if you don't care)
admin_res = supabase.auth.admin.create_user(
	{"email": "dev@example.com", "password": "dev-password"}
)
user_id = admin_res.user.id

# 2. Mirror the row into your Profiles table
supabase.table("Users").insert({
	"id": user_id,
	"display_name": "Dev User",
	"timezone": "America/Los_Angeles",
}).execute()
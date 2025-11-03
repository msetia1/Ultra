# Trayne Integration Setup Guide

This guide walks you through setting up the Trayne OAuth integration for Ultra Calendar.

## Quick Links

- **Main Plan**: `TRAYNE_INTEGRATION_PLAN.md` - Full technical implementation plan
- **Trayne Project**: `/Users/liamkauffman/Trayne-Mono-Dir/`
- **Ultra Project**: `/Users/liamkauffman/YC-Agent-Jam/`

## Prerequisites

- Trayne local Supabase instance running
- Ultra backend and frontend development environments set up
- Python 3 with bcrypt installed: `pip install bcrypt`

## Step-by-Step Setup

### Step 1: Generate OAuth Credentials for Ultra

Navigate to Trayne project and run the credential generator:

```bash
cd /Users/liamkauffman/Trayne-Mono-Dir/trainwithai-ai-chat-editing/trainwithai
python3 scripts/generate_oauth_credentials.py
```

This will output:
- Client ID: `ultra-calendar-yc-jam`
- Client Secret: `<random secure string>`
- Bcrypt Hash: `<hash for database>`

**⚠️ Save these credentials securely!**

### Step 2: Update Trayne Database Migration

1. Open the migration file:
   ```bash
   code supabase/migrations/register_ultra_oauth_client.sql
   ```

2. Replace two placeholders:
   - `<CLIENT_SECRET_BCRYPT_HASH>` → Paste the bcrypt hash from Step 1
   - `<YOUR_USER_ID>` → Your Trayne user ID (get from Supabase dashboard or auth.users table)

3. Save the file

### Step 3: Get Your Trayne User ID

Option A - Using Supabase CLI:
```bash
cd /Users/liamkauffman/Trayne-Mono-Dir/trainwithai-ai-chat-editing/trainwithai
supabase db query "SELECT id, email FROM auth.users LIMIT 5;"
```

Option B - Using Supabase Studio:
1. Visit http://127.0.0.1:54323 (local Supabase Studio)
2. Go to Authentication → Users
3. Copy your user ID

### Step 4: Run Migration in Trayne

Make sure Trayne's local Supabase is running:

```bash
cd /Users/liamkauffman/Trayne-Mono-Dir/trainwithai-ai-chat-editing/trainwithai

# Check if Supabase is running
supabase status

# If not running, start it
supabase start

# Run the migration
supabase migration up
```

Verify the client was created:
```bash
supabase db query "SELECT client_id, name, status, scopes FROM oauth_clients WHERE client_id = 'ultra-calendar-yc-jam';"
```

You should see output like:
```
 client_id              | name           | status | scopes
------------------------+----------------+--------+-----------------------------------------------
 ultra-calendar-yc-jam  | Ultra Calendar | active | {read:training_plans,read:training_sessions}
```

### Step 5: Configure Ultra Backend

1. Add credentials to Ultra's `.env` file:
   ```bash
   cd /Users/liamkauffman/YC-Agent-Jam/server
   ```

2. Add these lines to `.env`:
   ```bash
   # Trayne Integration
   TRAYNE_CLIENT_ID=ultra-calendar-yc-jam
   TRAYNE_CLIENT_SECRET=<plaintext secret from Step 1>
   TRAYNE_API_BASE_URL=http://localhost:8002
   TRAYNE_CALLBACK_URL=http://localhost:8000/auth/trayne/callback
   ```

### Step 6: Verify Trayne API is Accessible

Test that Trayne's OAuth endpoints are reachable:

```bash
# Check if Trayne backend is running
curl http://localhost:8002/health

# Test OAuth authorize endpoint (should return 401 since not authenticated)
curl http://localhost:8002/integrations/external/authorize
```

If Trayne backend isn't running, start it:
```bash
cd /Users/liamkauffman/Trayne-Mono-Dir/trainwithai-ai-chat-editing/train-with-ai-data
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8002
```

## Implementation Checklist

Now follow the implementation plan in `TRAYNE_INTEGRATION_PLAN.md`:

### Backend Tasks
- [ ] Create `server/integrations/trayne_service.py` (see Phase 2.1)
- [ ] Update `server/app.py` with OAuth routes (see Phase 2.2)
- [ ] Create database migration for Ultra (see Phase 2.3)
- [ ] Run migration: `cd server && supabase migration up`

### Frontend Tasks
- [ ] Update `integrationsApi.ts` with `startTrayneOAuth()` (see Phase 3.1)
- [ ] Update `IntegrationsScreen.tsx` to handle Trayne clicks (see Phase 3.2)
- [ ] Update `Onboarding.tsx` callback handler (see Phase 3.3)

### Testing
- [ ] Start both Trayne and Ultra backends
- [ ] Navigate to Ultra onboarding page
- [ ] Click "Connect" on Trayne card
- [ ] Log into Trayne if needed
- [ ] Authorize Ultra
- [ ] Verify redirect back with "Connected" state
- [ ] Test `/trayne/plans` and `/trayne/sessions` endpoints

## Architecture Diagram

```
┌─────────────────────┐
│  Ultra Frontend     │
│  localhost:5173     │
└──────────┬──────────┘
           │ 1. User clicks "Connect Trayne"
           ▼
┌─────────────────────┐
│  Ultra Backend      │
│  localhost:8000     │
│  /auth/trayne/start │
└──────────┬──────────┘
           │ 2. Redirect to Trayne OAuth
           ▼
┌─────────────────────────────────────┐
│  Trayne Backend (OAuth Provider)    │
│  localhost:8002                      │
│  /integrations/external/authorize    │
└──────────┬──────────────────────────┘
           │ 3. User authorizes (must be logged into Trayne)
           │ 4. Issues authorization code
           ▼
┌─────────────────────┐
│  Ultra Backend      │
│  /auth/trayne/      │
│  callback           │
└──────────┬──────────┘
           │ 5. Exchange code for access token
           │ 6. Store token in Ultra's DB
           ▼
┌─────────────────────┐
│  Trayne Backend     │
│  /integrations/     │
│  external/token     │
└──────────┬──────────┘
           │ 7. Returns access_token
           ▼
┌─────────────────────┐
│  Ultra Backend      │
│  /trayne/plans      │
│  /trayne/sessions   │
└──────────┬──────────┘
           │ 8. Use token to fetch data
           ▼
┌─────────────────────────────────────┐
│  Trayne Public API                   │
│  /integrations/external/public-api/* │
└──────────────────────────────────────┘
```

## Troubleshooting

### OAuth Flow Fails

**Problem**: Clicking "Connect" doesn't redirect to Trayne

**Solutions**:
- Check Ultra backend is running on port 8000
- Check Trayne backend is running on port 8002
- Verify `TRAYNE_API_BASE_URL` in Ultra's `.env`
- Check browser console for errors

### Authorization Page Shows Error

**Problem**: "Invalid client_id" error on Trayne authorization page

**Solutions**:
- Verify oauth_client was inserted in Trayne database
- Check `TRAYNE_CLIENT_ID` matches database value
- Run verification query from Step 4

### Token Exchange Fails

**Problem**: Callback returns error

**Solutions**:
- Verify `TRAYNE_CLIENT_SECRET` is plaintext (not hash)
- Check client_secret_hash in database matches
- Verify callback URL matches registered redirect_uri
- Check Trayne backend logs for errors

### API Calls Return 401

**Problem**: `/trayne/plans` returns "Invalid token"

**Solutions**:
- Check token was stored in Ultra's database
- Verify token hasn't expired (30 days)
- Test token manually with curl:
  ```bash
  curl -H "Authorization: Bearer <token>" \
    http://localhost:8002/integrations/external/public-api/training-plans
  ```

### User Not Logged Into Trayne

**Problem**: OAuth flow asks for Trayne login

**Solution**: This is expected! User must have a Trayne account and be logged in.
- Sign up/login at Trayne first
- Then initiate OAuth flow from Ultra

## Development Tips

### Quick Reset

If you need to start over:

```bash
# Delete Ultra's Trayne integration
cd /Users/liamkauffman/YC-Agent-Jam/server
supabase db query "DELETE FROM trayne_integrations WHERE user_id = '<your-ultra-user-id>';"

# Delete OAuth client from Trayne
cd /Users/liamkauffman/Trayne-Mono-Dir/trainwithai-ai-chat-editing/trainwithai
supabase db query "DELETE FROM oauth_clients WHERE client_id = 'ultra-calendar-yc-jam';"
supabase db query "DELETE FROM oauth_access_tokens WHERE client_id IN (SELECT id FROM oauth_clients WHERE client_id = 'ultra-calendar-yc-jam');"

# Re-run setup from Step 1
```

### Testing Token Manually

Get your stored token from Ultra:
```bash
cd /Users/liamkauffman/YC-Agent-Jam/server
supabase db query "SELECT access_token FROM trayne_integrations WHERE user_id = '<your-user-id>';"
```

Test it against Trayne API:
```bash
TOKEN="<your-token>"
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8002/integrations/external/public-api/training-plans
```

### Viewing Logs

**Ultra Backend:**
```bash
cd /Users/liamkauffman/YC-Agent-Jam/server
# Logs will show in terminal where backend is running
```

**Trayne Backend:**
```bash
cd /Users/liamkauffman/Trayne-Mono-Dir/trainwithai-ai-chat-editing/train-with-ai-data
# Logs will show in terminal where backend is running
```

**Frontend:**
- Open browser DevTools → Console tab
- Look for `[Onboarding]` and `[IntegrationsScreen]` logs

## Next Steps After Setup

Once the integration is working:

1. **Test Data Fetching**: Call `/trayne/plans` and `/trayne/sessions` to verify data flows
2. **UI Integration**: Display training plans/sessions in Ultra's calendar view
3. **Sync Strategy**: Implement periodic refresh or manual sync button
4. **Error Handling**: Add user-friendly messages for expired tokens
5. **Production**: Update redirect URIs and environment variables for production deployment

## Support

If you encounter issues:
1. Check this guide's Troubleshooting section
2. Review `TRAYNE_INTEGRATION_PLAN.md` for technical details
3. Verify all services are running (Trayne backend, Ultra backend, both Supabase instances)
4. Check logs in both backend terminals

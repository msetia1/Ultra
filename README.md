# Ultra
AI Scheduling Agent

## Setup

1. Install dependencies:
```bash
cd server
pip install -r requirements.txt
```

2. Configure environment variables in `server/.env`:
```
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
WHOOP_CLIENT_ID=your_whoop_client_id
WHOOP_CLIENT_SECRET=your_whoop_client_secret
WHOOP_API_HOSTNAME=https://api.prod.whoop.com
WHOOP_CALLBACK_URL=http://localhost:8000/auth/whoop/callback
TEST_USER_ID=your_test_user_uuid
```

3. Register callback URL in WHOOP Developer Dashboard:
   - Go to https://developer-dashboard.whoop.com
   - Add `http://localhost:8000/auth/whoop/callback` as a redirect URI

## Running the Application

```bash
cd server
uvicorn app:app --reload
```

Application runs at http://localhost:8000

## Usage

1. Visit http://localhost:8000
2. Click "Connect WHOOP" to authorize integration
3. After authorization, view your recovery and activity data
4. Use the data to optimize your schedule

## API Endpoints

- `GET /` - Frontend application
- `GET /api` - API information
- `GET /auth/whoop/start` - Start WHOOP OAuth flow
- `GET /auth/whoop/callback` - OAuth callback handler
- `GET /whoop/cycles?days=7` - Fetch WHOOP cycle data
- `GET /health` - Health check

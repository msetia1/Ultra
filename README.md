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
LINEAR_CLIENT_ID=your_linear_client_id
LINEAR_CLIENT_SECRET=your_linear_client_secret
LINEAR_CALLBACK_URL=http://localhost:8000/auth/linear/callback
TEST_USER_ID=your_test_user_uuid
```

3. Register callback URLs in integration developer dashboards:

   **WHOOP:**
   - Go to https://developer-dashboard.whoop.com
   - Add `http://localhost:8000/auth/whoop/callback` as a redirect URI

   **Linear:**
   - Go to https://linear.app/settings/api
   - Create new OAuth2 application
   - Add `http://localhost:8000/auth/linear/callback` as callback URL
   - Set scopes: `read`, `write`, `issues:create`

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

### General
- `GET /` - Frontend application
- `GET /api` - API information
- `GET /health` - Health check

### WHOOP Integration
- `GET /auth/whoop/start` - Start WHOOP OAuth flow
- `GET /auth/whoop/callback` - WHOOP OAuth callback handler
- `GET /whoop/cycles?days=7` - Fetch WHOOP cycle data

### Linear Integration
- `GET /auth/linear/start` - Start Linear OAuth flow
- `GET /auth/linear/callback` - Linear OAuth callback handler
- `GET /linear/teams` - Fetch Linear teams
- `GET /linear/issues?team_id=&state=&assignee=` - Fetch Linear issues with filters
- `GET /linear/projects` - Fetch Linear projects
- `POST /linear/issues` - Create a new Linear issue

## Integration Setup

### WHOOP
1. Visit http://localhost:8000/auth/whoop/start
2. Authorize the application
3. Access WHOOP data via `/whoop/cycles`

### Linear
1. Visit http://localhost:8000/auth/linear/start
2. Authorize the application
3. Access Linear data via `/linear/teams`, `/linear/issues`, `/linear/projects`
4. Create issues programmatically via `POST /linear/issues`

For detailed integration documentation, see:
- WHOOP: `server/integrations/feature_specs/whoop_integration.md` (if exists)
- Linear: `server/integrations/feature_specs/linear_integration.md`

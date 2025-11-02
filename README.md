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

---

## AWS App Runner Deployment

This application is configured for deployment to AWS App Runner with the custom domain **ultra-calendar.com**.

### Architecture

The deployment uses a single App Runner service that:
- Serves the React frontend as static files
- Hosts the FastAPI backend API
- Automatically scales based on traffic
- Provides HTTPS via AWS-managed certificates

### Prerequisites

1. AWS Account (Trayne AWS account)
2. AWS CLI configured with appropriate credentials
3. Docker installed locally (for testing)
4. Domain `ultra-calendar.com` hosted in Route 53 or accessible DNS

### Deployment Steps

#### 1. Build and Test Docker Image Locally

```bash
# Build the Docker image
docker build -t ultra-calendar .

# Test the container locally
docker run -p 8000:8000 \
  -e SUPABASE_URL=your_supabase_url \
  -e SUPABASE_SERVICE_ROLE_KEY=your_key \
  -e WHOOP_CLIENT_ID=your_whoop_id \
  -e WHOOP_CLIENT_SECRET=your_whoop_secret \
  -e WHOOP_API_HOSTNAME=https://api.prod.whoop.com \
  -e WHOOP_CALLBACK_URL=https://ultra-calendar.com/auth/whoop/callback \
  -e LINEAR_CLIENT_ID=your_linear_id \
  -e LINEAR_CLIENT_SECRET=your_linear_secret \
  -e LINEAR_CALLBACK_URL=https://ultra-calendar.com/auth/linear/callback \
  -e TEST_USER_ID=your_test_user_uuid \
  -e ENVIRONMENT=production \
  ultra-calendar

# Visit http://localhost:8000
```

#### 2. Push to Amazon ECR

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <your-aws-account-id>.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository
aws ecr create-repository --repository-name ultra-calendar --region us-east-1

# Tag the image
docker tag ultra-calendar:latest <your-aws-account-id>.dkr.ecr.us-east-1.amazonaws.com/ultra-calendar:latest

# Push to ECR
docker push <your-aws-account-id>.dkr.ecr.us-east-1.amazonaws.com/ultra-calendar:latest
```

#### 3. Create App Runner Service

Using AWS Console:

1. Navigate to AWS App Runner in the AWS Console
2. Click "Create service"
3. **Source**:
   - Repository type: Container registry
   - Provider: Amazon ECR
   - Container image URI: `<your-aws-account-id>.dkr.ecr.us-east-1.amazonaws.com/ultra-calendar:latest`
   - Deployment trigger: Manual or Automatic
4. **Service settings**:
   - Service name: `ultra-calendar`
   - Port: `8000`
   - CPU: 1 vCPU
   - Memory: 2 GB
5. **Environment variables** (add all required variables):
   ```
   ENVIRONMENT=production
   SUPABASE_URL=<your-supabase-url>
   SUPABASE_SERVICE_ROLE_KEY=<your-key>
   WHOOP_CLIENT_ID=<your-whoop-id>
   WHOOP_CLIENT_SECRET=<your-whoop-secret>
   WHOOP_API_HOSTNAME=https://api.prod.whoop.com
   WHOOP_CALLBACK_URL=https://ultra-calendar.com/auth/whoop/callback
   LINEAR_CLIENT_ID=<your-linear-id>
   LINEAR_CLIENT_SECRET=<your-linear-secret>
   LINEAR_CALLBACK_URL=https://ultra-calendar.com/auth/linear/callback
   TEST_USER_ID=<your-test-user-uuid>
   ```
6. **Health check**:
   - Path: `/health`
   - Interval: 30 seconds
   - Timeout: 5 seconds
7. Click "Create & deploy"

Using AWS CLI:

```bash
aws apprunner create-service \
  --service-name ultra-calendar \
  --source-configuration file://apprunner-source-config.json \
  --instance-configuration file://apprunner-instance-config.json \
  --region us-east-1
```

#### 4. Configure Custom Domain

1. In App Runner console, select your service
2. Go to "Custom domains" tab
3. Click "Link domain"
4. Enter `ultra-calendar.com`
5. Follow instructions to add CNAME records to your DNS:
   ```
   CNAME: ultra-calendar.com -> <your-apprunner-domain>.awsapprunner.com
   ```
6. Optionally add `www.ultra-calendar.com` as well
7. Wait for domain validation (5-10 minutes)

#### 5. Update OAuth Callback URLs

After domain is configured, update your OAuth applications:

**WHOOP:**
- Go to https://developer-dashboard.whoop.com
- Update redirect URI to: `https://ultra-calendar.com/auth/whoop/callback`

**Linear:**
- Go to https://linear.app/settings/api
- Update callback URL to: `https://ultra-calendar.com/auth/linear/callback`

### Deployment Updates

To deploy updates:

```bash
# Build new image
docker build -t ultra-calendar .

# Tag and push to ECR
docker tag ultra-calendar:latest <your-aws-account-id>.dkr.ecr.us-east-1.amazonaws.com/ultra-calendar:latest
docker push <your-aws-account-id>.dkr.ecr.us-east-1.amazonaws.com/ultra-calendar:latest

# Trigger new deployment in App Runner
aws apprunner start-deployment --service-arn <your-service-arn>
```

### Monitoring

- **App Runner Dashboard**: View metrics, logs, and deployment history
- **CloudWatch Logs**: All application logs are automatically sent to CloudWatch
- **Health Check**: Monitor `/health` endpoint status

### Cost Estimation

AWS App Runner pricing (us-east-1):
- **Provisioned container**: ~$0.007/hour for 1 vCPU + 2 GB memory
- **Active container**: ~$0.064/hour for 1 vCPU + 2 GB memory
- **Data transfer**: Standard AWS rates

Estimated monthly cost: $50-100 for low to moderate traffic.

### Troubleshooting

**Container fails to start:**
- Check CloudWatch logs for errors
- Verify all environment variables are set correctly
- Ensure ECR image is accessible

**Domain not working:**
- Verify CNAME records are correctly configured
- Wait for DNS propagation (up to 48 hours)
- Check App Runner domain status

**OAuth redirects failing:**
- Ensure callback URLs are updated in OAuth provider dashboards
- Verify CORS settings include production domain
- Check ENVIRONMENT variable is set to "production"

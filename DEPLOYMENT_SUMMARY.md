# Ultra Calendar - AWS Deployment Summary

## ✅ Deployment Completed

Your Ultra Calendar application has been successfully deployed to AWS App Runner on the Trayne account!

### Deployment Details

**AWS Account**: 477391720355 (Trayne)
**Region**: us-east-1
**Service Name**: ultra-calendar
**Service URL**: https://pkt42pghrd.us-east-1.awsapprunner.com
**Service ARN**: arn:aws:apprunner:us-east-1:477391720355:service/ultra-calendar/e1cb01006eb94e60b790d4ef6fd6e5e2
**ECR Repository**: 477391720355.dkr.ecr.us-east-1.amazonaws.com/ultra-calendar
**Image Digest**: sha256:b8e200ba7d277bbb9f9656624cae5ff10bf41b734ef7e34d0693eef9b9b056d6

**Status**: Deploying (typically takes 3-5 minutes for first deployment)

---

## 🔧 Required Configuration Steps

### 1. Add Environment Variables

The service is currently deployed with minimal environment variables. You need to add the following via AWS Console or CLI:

```bash
# Navigate to App Runner service in AWS Console
# Go to: Configuration → Environment variables

# Required variables:
ENVIRONMENT=production
PORT=8000
SUPABASE_URL=<your-supabase-url>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
WHOOP_CLIENT_ID=<your-whoop-id>
WHOOP_CLIENT_SECRET=<your-whoop-secret>
WHOOP_API_HOSTNAME=https://api.prod.whoop.com
WHOOP_CALLBACK_URL=https://ultra-calendar.com/auth/whoop/callback
LINEAR_CLIENT_ID=<your-linear-id>
LINEAR_CLIENT_SECRET=<your-linear-secret>
LINEAR_CALLBACK_URL=https://ultra-calendar.com/auth/linear/callback
TEST_USER_ID=<your-test-user-uuid>
```

**Using AWS CLI**:
```bash
aws apprunner update-service \
  --service-arn arn:aws:apprunner:us-east-1:477391720355:service/ultra-calendar/e1cb01006eb94e60b790d4ef6fd6e5e2 \
  --source-configuration file://updated-source-config.json \
  --profile trayne \
  --region us-east-1
```

### 2. Configure Custom Domain (ultra-calendar.com)

Once the service is **RUNNING**, configure the custom domain:

**Option A: AWS Console**
1. Go to App Runner → Services → ultra-calendar
2. Click "Custom domains" tab
3. Click "Link domain"
4. Enter: `ultra-calendar.com`
5. AWS will provide validation records

**Option B: AWS CLI**
```bash
aws apprunner associate-custom-domain \
  --service-arn arn:aws:apprunner:us-east-1:477391720355:service/ultra-calendar/e1cb01006eb94e60b790d4ef6fd6e5e2 \
  --domain-name ultra-calendar.com \
  --enable-www-subdomain \
  --profile trayne \
  --region us-east-1
```

**DNS Configuration** (after domain association):
```
# Add these CNAME records to your DNS provider:

Type: CNAME
Name: _<validation-string>
Value: <provided-by-aws>

Type: CNAME
Name: ultra-calendar.com (or @)
Value: pkt42pghrd.us-east-1.awsapprunner.com

Type: CNAME
Name: www
Value: pkt42pghrd.us-east-1.awsapprunner.com
```

### 3. Update OAuth Callback URLs

Update your OAuth applications with production URLs:

**WHOOP**:
- Dashboard: https://developer-dashboard.whoop.com
- Add redirect URI: `https://ultra-calendar.com/auth/whoop/callback`

**Linear**:
- Settings: https://linear.app/settings/api
- Update callback URL: `https://ultra-calendar.com/auth/linear/callback`

**GitHub** (if applicable):
- Settings: https://github.com/settings/applications
- Update callback URL: `https://ultra-calendar.com/auth/github/callback`

---

## 📊 Service Configuration

### Instance Details
- **CPU**: 1 vCPU
- **Memory**: 2 GB
- **Port**: 8000
- **Auto-scaling**: Enabled (default configuration)
- **Health Check**: HTTP GET /health every 10 seconds

### Cost Estimate
- **Provisioned**: ~$0.007/hour
- **Active**: ~$0.064/hour
- **Monthly estimate**: $50-100 (low-moderate traffic)

---

## 🚀 Deployment Commands

### Check Service Status
```bash
aws apprunner describe-service \
  --service-arn arn:aws:apprunner:us-east-1:477391720355:service/ultra-calendar/e1cb01006eb94e60b790d4ef6fd6e5e2 \
  --profile trayne \
  --region us-east-1 \
  --query 'Service.Status'
```

### View Service URL
```bash
aws apprunner describe-service \
  --service-arn arn:aws:apprunner:us-east-1:477391720355:service/ultra-calendar/e1cb01006eb94e60b790d4ef6fd6e5e2 \
  --profile trayne \
  --region us-east-1 \
  --query 'Service.ServiceUrl' \
  --output text
```

### Deploy Updates
```bash
# 1. Rebuild Docker image
docker build -t ultra-calendar:latest .

# 2. Tag and push to ECR
docker tag ultra-calendar:latest 477391720355.dkr.ecr.us-east-1.amazonaws.com/ultra-calendar:latest

# Authenticate if needed
aws ecr get-login-password --region us-east-1 --profile trayne | \
  docker login --username AWS --password-stdin 477391720355.dkr.ecr.us-east-1.amazonaws.com

# Push
docker push 477391720355.dkr.ecr.us-east-1.amazonaws.com/ultra-calendar:latest

# 3. Trigger deployment (if auto-deploy is off)
aws apprunner start-deployment \
  --service-arn arn:aws:apprunner:us-east-1:477391720355:service/ultra-calendar/e1cb01006eb94e60b790d4ef6fd6e5e2 \
  --profile trayne \
  --region us-east-1
```

---

## 📝 Monitoring & Logs

### View Logs
```bash
# App Runner automatically sends logs to CloudWatch
# Go to: CloudWatch → Log groups → /aws/apprunner/ultra-calendar/...
```

### Service Metrics
Available in App Runner Console:
- Request count
- Response time
- 4xx/5xx errors
- Active instances
- CPU/Memory utilization

---

## ⚙️ Next Steps

1. **Wait for deployment** (3-5 minutes)
   - Check status: `aws apprunner describe-service ...`
   - Once status shows `RUNNING`, proceed to next steps

2. **Add environment variables** via AWS Console or CLI

3. **Test the service**:
   ```bash
   curl https://pkt42pghrd.us-east-1.awsapprunner.com/health
   curl https://pkt42pghrd.us-east-1.awsapprunner.com/api
   ```

4. **Configure custom domain** (ultra-calendar.com)

5. **Update OAuth callbacks** in WHOOP, Linear, GitHub dashboards

6. **Test production deployment**:
   - Visit https://ultra-calendar.com
   - Test OAuth flows
   - Verify integrations

---

## 🔗 Useful Links

- **App Runner Console**: https://console.aws.amazon.com/apprunner/home?region=us-east-1#/services/ultra-calendar
- **ECR Repository**: https://console.aws.amazon.com/ecr/repositories/private/477391720355/ultra-calendar?region=us-east-1
- **CloudWatch Logs**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups
- **Service URL**: https://pkt42pghrd.us-east-1.awsapprunner.com

---

## 📞 Support

For issues or questions:
- Check CloudWatch logs for errors
- Review App Runner service events
- Verify environment variables are set correctly
- Ensure OAuth callbacks are updated

**Generated**: 2025-11-02

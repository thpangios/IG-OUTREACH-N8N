# n8n Workflow Automation Setup

This directory contains the n8n v1.106.0 configuration for automating real estate lead processing and outreach workflows.

## 🚀 Quick Setup

### 1. Start n8n
```bash
cd n8n
docker-compose up -d
```

### 2. Access Dashboard
- URL: `http://localhost:5678`
- Username: `admin`
- Password: `changeme` (change this in production!)

### 3. Import Workflow
1. Click "+" → "Import from File"
2. Select `workflows/instagram_scrape_workflow.json`
3. Activate the workflow

## 🔧 Configuration

### Required Credentials

#### OpenAI API
1. Go to Settings → Credentials → New Credential
2. Select "OpenAI API"
3. Add your API key from OpenAI

#### Instagram Automation Service (Optional)
For automated DM sending, configure:
1. API endpoint URL
2. Authorization token
3. Rate limiting parameters

#### Slack Webhook (Optional)
1. Create webhook in Slack workspace
2. Add webhook URL to workflow
3. Customize notification format

#### Gmail API (Optional)
1. Enable Gmail API in Google Cloud Console
2. Create service account and download credentials
3. Configure in n8n Gmail node

### Environment Variables

Update `docker-compose.yml` for production:
```yaml
environment:
  # Change default credentials
  - N8N_BASIC_AUTH_USER=your_admin_user
  - N8N_BASIC_AUTH_PASSWORD=your_secure_password
  
  # Database (for production)
  - DB_TYPE=postgresdb
  - DB_POSTGRESDB_HOST=postgres
  - DB_POSTGRESDB_DATABASE=n8n
  - DB_POSTGRESDB_USER=n8n
  - DB_POSTGRESDB_PASSWORD=your_db_password
  
  # Security
  - N8N_SECURE_COOKIE=true
  - N8N_JWT_AUTH_ENABLED=true
  
  # Webhook settings
  - WEBHOOK_URL=https://your-domain.com/
```

## 📋 Workflow Details

### Main Workflow: Instagram Lead Processing

**Trigger**: Webhook endpoint `/webhook/instagram-leads`

**Flow**:
1. **Webhook Trigger** → Receives lead data from Python scraper
2. **Process Leads** → Filters and prioritizes qualified leads
3. **Priority Routing** → Routes based on lead scores
4. **Message Generation** → Creates personalized outreach using GPT-4
5. **Multi-Channel Actions** → Sends DMs, notifications, emails
6. **Statistics** → Compiles job performance metrics

### Node Configuration

#### Webhook Node
- **Path**: `instagram-leads`
- **Method**: POST
- **Response Mode**: Using 'Respond to Webhook' node

#### Code Nodes
- **Process Lead Data**: Filters qualified leads, calculates priorities
- **Add to Daily Batch**: Queues medium priority leads
- **Mark for Manual Review**: Flags low priority leads
- **Compile Statistics**: Generates performance reports

#### OpenAI Node
- **Model**: gpt-4
- **Temperature**: 0.7
- **Max Tokens**: 250
- **System Prompt**: Optimized for real estate professional outreach

#### HTTP Request Nodes
- **Queue High Priority DM**: Sends to Instagram automation service
- **Save Batch to Database**: Stores leads for batch processing
- **Slack Notification**: Posts to team channel

## 🔄 Additional Workflows

### Daily Batch Processor
```json
{
  "name": "Daily Lead Batch Processor",
  "trigger": "schedule",
  "schedule": "0 9 * * *"
}
```

**Purpose**: Processes medium priority leads daily at 9 AM

**Steps**:
1. Fetch pending batch leads from database
2. Generate personalized messages for each lead
3. Queue DMs with random delays (60-180 minutes)
4. Update lead status to "contacted"
5. Send daily report to team

### Performance Analytics
```json
{
  "name": "Weekly Performance Report",
  "trigger": "schedule", 
  "schedule": "0 10 * * 1"
}
```

**Generates**:
- Lead qualification rates by source
- Outreach response rates
- Top performing keywords
- ROI metrics and trends

## 📊 Webhook Payload Format

### Expected Input from Python Scraper
```json
{
  "timestamp": "2025-01-07T23:00:00Z",
  "job_name": "Real Estate Post Scraping",
  "total_leads": 25,
  "leads": [
    {
      "username": "miami_luxury_agent",
      "profile_url": "https://instagram.com/miami_luxury_agent",
      "keyword_score": 85,
      "gpt_score": 90,
      "confidence": "high",
      "agent_type": "realtor",
      "market_focus": "luxury",
      "matched_keywords": ["realtor", "luxury homes", "miami"],
      "reasoning": "Bio mentions luxury real estate specialization",
      "is_qualified": true
    }
  ]
}
```

### Response Format
```json
{
  "status": "success",
  "message": "Leads processed successfully", 
  "statistics": {
    "total_leads_processed": 25,
    "high_priority": 5,
    "medium_priority": 12,
    "low_priority": 8,
    "average_score": 73,
    "processing_time": "2025-01-07T23:05:00Z"
  },
  "leads_breakdown": {
    "high_priority": "5 leads - immediate outreach initiated",
    "medium_priority": "12 leads - added to daily batch", 
    "low_priority": "8 leads - marked for manual review"
  }
}
```

## 🛠️ Customization

### Message Templates
Edit the GPT-4 system prompt in the "Generate Personalized Message" node:

```
You are an expert at writing personalized Instagram DMs for real estate professionals. 

Guidelines:
1. Reference their specialization subtly
2. Offer value (lead generation, automation tools)
3. Be conversational, not salesy
4. Include a soft call-to-action
5. Keep under 150 words

Create a message for:
- Agent Type: {{ $json.agent_type }}
- Market Focus: {{ $json.market_focus }}
- Keywords: {{ $json.matched_keywords.join(', ') }}
```

### Priority Thresholds
Modify conditions in "High Priority Lead?" and "Medium Priority Lead?" nodes:

```javascript
// High Priority: 80+ combined score
$json.keyword_score + ($json.gpt_score || 0) >= 160

// Medium Priority: 60-79 combined score  
$json.keyword_score + ($json.gpt_score || 0) >= 120
```

### Notification Channels
Add new notification methods:
- **Discord**: HTTP Request to Discord webhook
- **Microsoft Teams**: Teams webhook integration
- **SMS**: Twilio API for urgent leads
- **CRM**: Direct integration with Salesforce/HubSpot

## 📈 Monitoring & Analytics

### Built-in Metrics
- Lead processing success rates
- Message generation response times  
- Webhook delivery status
- Node execution statistics

### Custom Analytics
Add nodes to track:
- Lead source performance
- Geographic distribution
- Agent type breakdown
- Seasonal trends

### Logging
Enable detailed logging in `docker-compose.yml`:
```yaml
environment:
  - N8N_LOG_LEVEL=debug
  - N8N_LOG_OUTPUT=file
```

Logs location: `./n8n_data/logs/`

## 🔒 Security Considerations

### Production Deployment
1. **Change default credentials**
2. **Enable HTTPS** with SSL certificates
3. **Configure firewall rules** (only necessary ports)
4. **Regular security updates** for Docker images
5. **Backup workflow configurations** regularly

### Webhook Security
```yaml
environment:
  # Add webhook authentication
  - N8N_WEBHOOK_AUTH_TOKEN=your-secure-token
  
  # IP whitelist for webhooks
  - N8N_WEBHOOK_ALLOWED_IPS=192.168.1.0/24,10.0.0.0/8
```

### Data Privacy
- **Encrypt sensitive data** in transit and at rest
- **Implement data retention policies**
- **Log access for compliance auditing**
- **Regular credential rotation**

## 🚨 Troubleshooting

### Common Issues

**Workflow Import Errors**
```
Error: Missing credential type 'openAiApi'
Solution: Install OpenAI credential type first
```

**Webhook Not Triggering**
```
Check: 
- Webhook URL format: http://localhost:5678/webhook/instagram-leads
- Workflow is activated
- Firewall settings allow port 5678
```

**OpenAI API Errors**
```
Error: Rate limit exceeded
Solution: Check OpenAI usage limits and tier
```

**Docker Container Issues**
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs n8n

# Restart container
docker-compose restart n8n
```

### Debug Mode
Enable workflow execution debugging:
1. Go to workflow settings
2. Enable "Save manual executions"
3. Set log level to "Debug"
4. View execution logs in real-time

## 📚 Additional Resources

- [n8n Documentation](https://docs.n8n.io/)
- [n8n Community Forum](https://community.n8n.io/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Instagram Basic Display API](https://developers.facebook.com/docs/instagram-basic-display-api)

## 🆙 Upgrading n8n

### Update to Latest Version
```bash
# Pull latest image
docker-compose pull n8n

# Restart with new image
docker-compose up -d
```

### Backup Before Upgrade
```bash
# Backup n8n data directory
tar -czf n8n_backup_$(date +%Y%m%d).tar.gz n8n_data/

# Export workflows
# Use n8n interface: Settings → Import/Export → Export
```

---

**💡 Pro Tips**:
- Test workflows with sample data before production use
- Monitor execution logs regularly for optimization opportunities  
- Use environment-specific configurations for dev/staging/production
- Implement proper error handling and retry logic for external API calls

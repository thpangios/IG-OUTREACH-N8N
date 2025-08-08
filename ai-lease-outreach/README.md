# AI Real Estate Lead Outreach System

An enterprise-grade automation system that combines Python + Selenium Instagram scraping with n8n workflow automation to discover, qualify, and engage real estate professionals on Instagram.

## 🎯 Overview

This system automatically:
- **Discovers** real estate professionals from Instagram posts and profiles
- **Qualifies** leads using keyword analysis and GPT-4 scoring  
- **Personalizes** outreach messages using AI
- **Automates** multi-channel engagement workflows
- **Tracks** performance and ROI metrics

## 🏗️ Architecture

```
Instagram Scraper (Python + Selenium)
↓
Lead Qualification Engine (Keywords + GPT-4)
↓ 
n8n Workflow Automation (v1.106.0)
↓
Multi-Channel Outreach (Instagram DMs, Email, etc.)
```

## 📋 Prerequisites

### System Requirements
- Python 3.9+
- Docker & Docker Compose
- Chrome/Chromium browser
- 4GB+ RAM recommended
- Stable internet connection

### Required Accounts & API Keys
- Instagram account (dedicated automation account recommended)
- OpenAI API key (for GPT-4 lead scoring)
- n8n instance (self-hosted via Docker)
- Optional: Slack webhook, Gmail API, Instagram automation service

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/your-username/ai-lease-outreach.git
cd ai-lease-outreach
```

### 2. Setup Python Environment
```bash
cd scraper
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env with your credentials
```

Required variables:
```env
# Instagram Credentials
INSTAGRAM_USERNAME=your_automation_account
INSTAGRAM_PASSWORD=your_password

# OpenAI for lead scoring
OPENAI_API_KEY=sk-your-openai-key

# n8n Webhook URL (after setup)
N8N_WEBHOOK_URL=http://localhost:5678/webhook/instagram-leads

# Optional: Run headless
HEADLESS=false
```

### 4. Start n8n
```bash
cd n8n
docker-compose up -d
```

Access n8n at `http://localhost:5678` (admin/changeme)

### 5. Import Workflow
1. Open n8n dashboard
2. Click "+" → "Import from File"
3. Select `n8n/workflows/instagram_scrape_workflow.json`
4. Configure webhook URL in the scraper

### 6. Test Run
```bash
cd scraper
python run_scraper.py --post-url "https://instagram.com/p/EXAMPLE" --max-users 50
```

## 📖 Detailed Usage

### Scraping from Instagram Posts
```bash
# Scrape likers and commenters from a specific post
python run_scraper.py \
  --post-url "https://instagram.com/p/ABC123" \
  --max-users 200 \
  --output "leads_$(date +%Y%m%d).csv"
```

### Scraping Account Followers
```bash
# Scrape followers from a real estate account
python run_scraper.py \
  --account "luxuryrealtor" \
  --max-users 500 \
  --job-name "Luxury Realtor Followers"
```

### Custom Configuration
Create `config.json` for advanced settings:
```json
{
  "scraping": {
    "include_likers": true,
    "include_commenters": true,
    "max_likers": 200,
    "max_commenters": 100
  },
  "filtering": {
    "min_keyword_score": 40,
    "min_gpt_score": 60,
    "use_gpt_analysis": true
  },
  "export": {
    "csv_enabled": true,
    "webhook_enabled": true
  }
}
```

## 🧠 Lead Qualification System

### Keyword-Based Scoring (0-100 points)
- **Primary Keywords** (20 pts each): "realtor", "real estate agent", "broker"
- **Secondary Keywords** (10 pts each): "homes", "listings", "properties"
- **Company Indicators** (15 pts each): "RE/MAX", "Keller Williams", "Century 21"
- **Industry Terms** (5 pts each): "CRS", "GRI", "luxury homes"

### GPT-4 Analysis
- Analyzes bio context and professional language
- Identifies agent type (realtor, broker, investor, etc.)
- Determines market focus (residential, commercial, luxury)
- Provides confidence rating and detailed reasoning

### Combined Scoring
- **High Priority** (80+ score): Immediate personalized outreach
- **Medium Priority** (60-79 score): Added to daily batch campaigns  
- **Low Priority** (40-59 score): Manual review queue
- **Disqualified** (<40 score): Filtered out

## 🔄 n8n Workflow Features

### Automatic Processing
- **Webhook Trigger**: Receives qualified leads from Python scraper
- **Priority Routing**: Routes leads based on qualification scores
- **Message Generation**: Creates personalized DMs using GPT-4
- **Multi-Channel Alerts**: Slack notifications, email alerts

### Lead Management
- **High Priority**: Immediate outreach + team notifications
- **Medium Priority**: Batched for daily campaigns
- **Low Priority**: Flagged for manual review
- **Performance Tracking**: Success rates, response tracking

### Integrations
- **OpenAI GPT-4**: Message personalization
- **Slack**: Real-time notifications
- **Gmail**: Alert emails
- **Instagram APIs**: Automated DM sending
- **CRM Systems**: Lead data sync

## 📊 Output Formats

### CSV Export
Columns include:
- `username`, `profile_url`, `keyword_score`, `gpt_score`
- `agent_type`, `market_focus`, `confidence`, `matched_keywords`
- `reasoning`, `key_indicators`

### Webhook Payload
```json
{
  "timestamp": "2025-01-07T23:00:00Z",
  "total_leads": 15,
  "leads": [
    {
      "username": "miami_realtor_pro",
      "profile_url": "https://instagram.com/miami_realtor_pro",
      "keyword_score": 85,
      "gpt_score": 92,
      "confidence": "high",
      "agent_type": "realtor",
      "market_focus": "luxury",
      "matched_keywords": ["realtor", "luxury homes", "miami"]
    }
  ]
}
```

## ⚖️ Safety & Rate Limiting

### Instagram Rate Limits
- **Followers/Following**: Max 200 per hour
- **Post Interactions**: Max 100 per hour  
- **Profile Views**: Max 500 per hour
- **Random Delays**: 2-5 seconds between actions

### Best Practices
1. **Use dedicated Instagram accounts** for automation
2. **Rotate multiple accounts** for high-volume scraping
3. **Implement proxy rotation** for IP diversity
4. **Monitor Instagram's Terms of Service**
5. **Start with small batches** (50-100 users)
6. **Gradually increase volume** based on success rates

### Detection Avoidance
- **Undetected ChromeDriver**: Bypasses basic bot detection
- **Human-like delays**: Random intervals between actions
- **Browser fingerprint randomization**: Different viewports, user agents
- **Cookie persistence**: Maintains login sessions
- **Error handling**: Graceful recovery from rate limits

## 🛠️ Troubleshooting

### Common Issues

**Login Failed**
```bash
# Check credentials and try manual login
# Enable 2FA if required
# Use app-specific password
```

**Chrome Driver Issues**
```bash
# Update Chrome and ChromeDriver
pip install --upgrade undetected-chromedriver
```

**Rate Limited**
```bash
# Reduce max_users parameters
# Increase delays in code
# Wait 24 hours before retrying
```

**n8n Workflow Errors**
- Check webhook URL configuration
- Verify OpenAI API key
- Review node credentials

### Debug Mode
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
python run_scraper.py --post-url "..." --max-users 10
```

## 📈 Performance Optimization

### Scaling Tips
1. **Multi-account setup**: Use 3-5 Instagram accounts with rotation
2. **Proxy integration**: Rotate IP addresses for larger volumes  
3. **Database integration**: Store results in PostgreSQL for analytics
4. **Caching**: Cache profile data to avoid re-scraping
5. **Parallel processing**: Run multiple scraper instances

### Monitoring
- Track qualification rates by source
- Monitor Instagram account health
- Analyze outreach response rates
- A/B test message templates

## 🔒 Security & Compliance

### Data Protection
- Store credentials in environment variables
- Use secure webhook endpoints (HTTPS)
- Implement rate limiting on webhooks
- Regular security updates

### Legal Considerations  
- Respect Instagram's Terms of Service
- Implement GDPR compliance for EU users
- Obtain consent for outreach where required
- Maintain data retention policies

## 🆘 Support

### Documentation
- [Python Scraper API](./scraper/README.md)
- [n8n Workflow Guide](./n8n/README.md)  
- [Instagram API Limits](https://developers.facebook.com/docs/instagram-api)

### Issues & Feature Requests
Create issues on GitHub with:
- Error logs and screenshots
- System specifications  
- Steps to reproduce
- Expected vs actual behavior

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch  
5. Create a Pull Request

---

**⚠️ Disclaimer**: This tool is for educational and legitimate business purposes only. Users are responsible for complying with Instagram's Terms of Service and applicable laws.

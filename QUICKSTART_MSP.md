# Quick Start Guide for MSP/ConnectWise Integration

This guide will help you set up the ChatGPT Retrieval Plugin with ConnectWise Manage integration for your MSP business.

## 🎯 What You'll Build

A searchable knowledge base of all your ConnectWise tickets that you can query with natural language:
- "How did we fix email issues for Acme Corp?"
- "Show me all printer problems resolved last month"
- "What's the fastest way to migrate to Office 365?"

## 📋 Prerequisites

1. **ConnectWise Manage** account with API access
2. **OpenAI API** key
3. **Python 3.10+** installed
4. **Vector database** (choose one):
   - Pinecone (easiest for beginners - cloud managed)
   - Postgres with pgvector (self-hosted)
   - Qdrant, Weaviate, etc.

## 🚀 Setup Steps

### 1. Clone and Install

```bash
git clone https://github.com/openai/chatgpt-retrieval-plugin.git
cd chatgpt-retrieval-plugin
pip install poetry
poetry env use python3.10
poetry shell
poetry install
```

### 2. Get ConnectWise API Credentials

1. Log into ConnectWise Manage
2. Go to **System > Members > API Members**
3. Create new API member (or use existing)
4. Save your Company ID, Public Key, Private Key
5. Get Client ID from: https://developer.connectwise.com/ClientID

### 3. Choose a Vector Database

**Option A: Pinecone (Recommended for Beginners)**
```bash
# Sign up at https://www.pinecone.io (free tier available)
# Create an index named "msp-tickets" with dimension 1536
export PINECONE_API_KEY="your-key"
export PINECONE_ENVIRONMENT="your-env"
export PINECONE_INDEX="msp-tickets"
```

**Option B: Postgres with pgvector (Self-Hosted)**
```bash
# Install PostgreSQL and pgvector extension
# Create database
export PG_HOST="localhost"
export PG_PORT="5432"
export PG_USER="postgres"
export PG_PASSWORD="your-password"
export PG_DATABASE="msp_kb"
```

### 4. Set Environment Variables

```bash
# Copy the example file
cp scripts/connectwise_import/.env.example .env

# Edit .env with your values
nano .env
```

Required variables:
```bash
# ConnectWise
CW_COMPANY_ID="yourcompany"
CW_PUBLIC_KEY="your-public-key"
CW_PRIVATE_KEY="your-private-key"
CW_CLIENT_ID="your-client-id"
CW_API_URL="https://api-na.myconnectwise.net"

# OpenAI
OPENAI_API_KEY="sk-..."

# Retrieval Plugin
DATASTORE="pinecone"  # or postgres, qdrant, etc.
BEARER_TOKEN="your-secret-token"  # Generate with: openssl rand -hex 32

# Your vector database credentials (Pinecone, Postgres, etc.)
```

Load the environment:
```bash
source .env  # or: export $(cat .env | xargs)
```

### 5. Test ConnectWise Connection

```bash
cd scripts/connectwise_import
python -c "
from connectwise_importer import ConnectWiseImporter
import os

importer = ConnectWiseImporter(
    company_id=os.getenv('CW_COMPANY_ID'),
    public_key=os.getenv('CW_PUBLIC_KEY'),
    private_key=os.getenv('CW_PRIVATE_KEY'),
    api_url=os.getenv('CW_API_URL'),
    client_id=os.getenv('CW_CLIENT_ID')
)

tickets = importer.get_closed_tickets(days_back=7)
print(f'✅ Success! Found {len(tickets)} tickets from last 7 days')
"
```

### 6. Start the Retrieval Plugin API

```bash
# From the root directory
poetry run start
```

The API will be available at http://localhost:8000

Test it: http://localhost:8000/docs

### 7. Import Your First Tickets

**Test with small batch first:**
```bash
cd scripts/connectwise_import
python example_usage.py 7  # Import last 7 days
```

**Import full history:**
```bash
python example_usage.py 365  # Import last year
```

This will:
1. Fetch tickets from ConnectWise
2. Convert them to searchable documents
3. Generate embeddings with OpenAI
4. Store in your vector database

### 8. Test Searching

```bash
python example_usage.py search
```

Or use the API directly:
```bash
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [{
      "query": "how to fix email sync issues",
      "top_k": 3
    }]
  }'
```

## 💰 Cost Estimation

### OpenAI Embedding Costs
- Cost: ~$0.0001 per 1,000 tokens
- Average ticket: ~500 tokens
- **10,000 tickets**: ~$0.50
- **New ticket indexed**: ~$0.00005 each

### Vector Database Costs
- **Pinecone**: Free tier (1 million vectors), then $70-140/month
- **Postgres**: Self-hosted (free) or cloud ($15-50/month)
- **Qdrant**: Self-hosted (free) or cloud ($25+/month)

### Example Monthly Cost
- 500 new tickets/month: $0.025 in embeddings
- Vector database: $0-140 depending on provider
- **Total**: $0-140/month (mostly database, not OpenAI)

## 📊 Usage Patterns

### Daily Automated Import
```bash
# Add to crontab (runs at 2 AM daily)
0 2 * * * cd /path/to/chatgpt-retrieval-plugin/scripts/connectwise_import && python example_usage.py 1
```

### Search Examples
```python
# Find similar tickets
"Email migration to Office 365 best practices"

# Client-specific
"All network issues for Acme Corp"

# Error code lookup
"What does error 0x80070005 mean?"

# Tech performance
"Show tickets resolved by John Smith"

# Time-based
"Printer issues from last week"
```

## 🔧 Advanced: Real-Time Sync

To automatically index tickets as they're closed:

1. **Add webhook endpoint** to `server/main.py`
2. **Configure webhook** in ConnectWise
3. **Set trigger**: "When ticket status = Closed"
4. **URL**: `https://your-domain.com/connectwise-webhook`

See `scripts/connectwise_import/README.md` for details.

## 🎨 Building a Chat UI

Now that you have the API running, you can build a simple chat interface:

**Option 1: Use existing ChatGPT plugin system**
- Deploy your API to cloud (Heroku, Fly.io, etc.)
- Register as ChatGPT plugin
- Use directly in ChatGPT interface

**Option 2: Build custom chat UI**
- React/Vue frontend
- Calls your `/query` endpoint
- Displays ticket suggestions as tech types

**Option 3: Slack/Teams Bot**
- Integrate with Slack/Teams
- Techs can query knowledge base from chat
- Example: "@bot how to fix VPN issues?"

## 📈 Next Steps

1. **Import all historical tickets** (start with 30 days, then expand)
2. **Test search relevance** (adjust chunking if needed)
3. **Add client documentation** (network diagrams, procedures)
4. **Index vendor KB articles** (Microsoft, Cisco, etc.)
5. **Set up automated daily imports**
6. **Build chat UI** for techs
7. **Add webhook** for real-time sync
8. **Train team** on how to use it

## 🐛 Troubleshooting

### "Authentication Failed"
- Verify Company ID (lowercase)
- Check API keys are correct
- Ensure API member has permissions

### "No tickets found"
- Check date range (try days_back=7 first)
- Verify tickets exist with those filters
- Check API member has access to board/tickets

### "OpenAI API Error"
- Verify OPENAI_API_KEY is set
- Check API key has credits
- Rate limits: slow down batch size

### "Vector database connection failed"
- Check database credentials
- Verify database is running
- Test connection separately

## 📞 Support

- **ConnectWise API**: https://developer.connectwise.com
- **OpenAI API**: https://platform.openai.com/docs
- **Retrieval Plugin**: https://github.com/openai/chatgpt-retrieval-plugin

## 🎉 Success Metrics

After 30 days, you should see:
- ✅ Faster ticket resolution (less searching old tickets)
- ✅ Better knowledge retention (documented solutions)
- ✅ Easier onboarding (new techs can search KB)
- ✅ Reduced escalations (find similar resolved tickets)
- ✅ Improved consistency (same solution for same issue)

## 🔒 Security Checklist

- [ ] Use HTTPS for API endpoints
- [ ] Keep BEARER_TOKEN secret
- [ ] Rotate API keys regularly
- [ ] Don't commit .env to git
- [ ] Restrict API member permissions (read-only)
- [ ] Use firewall rules for database
- [ ] Enable audit logging
- [ ] Encrypt sensitive client data
- [ ] Review PII in tickets before indexing

---

**You're all set!** You now have a searchable knowledge base of your ConnectWise tickets. Your techs can query it with natural language and get instant answers from past resolutions.

Questions? Open an issue or check the detailed documentation in `scripts/connectwise_import/README.md`

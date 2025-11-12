# 🚀 Easy Setup - Get Running in 2 Minutes

This guide will get you up and running with minimal effort. The setup scripts will automatically install everything you need!

## ⚡ Quick Start (Automatic Setup)

### Windows

1. **Download Python** (if not installed):
   - Go to https://www.python.org/downloads/
   - Download Python 3.10 or 3.11 (NOT 3.12)
   - **IMPORTANT:** Check "Add Python to PATH" during installation

2. **Run the setup:**
   - Double-click `setup_and_run.bat`
   - That's it! The script will install everything automatically.

### Mac / Linux

1. **Open Terminal** in the project directory

2. **Make script executable:**
   ```bash
   chmod +x setup_and_run.sh
   ```

3. **Run the setup:**
   ```bash
   ./setup_and_run.sh
   ```

The script will:
- ✅ Check Python version
- ✅ Install Poetry automatically
- ✅ Create .env configuration file
- ✅ Install all dependencies
- ✅ Start the server

---

## 📋 What You Need

### Required (Minimum to Run)

1. **OpenAI API Key**
   - Get from: https://platform.openai.com/api-keys
   - Cost: ~$0.10 per 1000 queries (with caching: ~$0.02)

2. **Vector Database** (choose one):

   **Option A: Pinecone** (Recommended - Easy)
   - Free tier available
   - Sign up: https://www.pinecone.io
   - Create an index with dimension 256
   - Get API key and environment

   **Option B: Chroma** (Local - Free)
   - No signup needed
   - Runs locally on your computer
   - Set `DATASTORE=chroma` in .env

   **Option C: PostgreSQL** (Self-hosted)
   - Install Postgres + pgvector extension
   - Free, but requires more setup

3. **Bearer Token**
   - Just a secret password for your API
   - Generate with: `openssl rand -hex 32`
   - Or use any random string: `my-secret-token-12345`

### Optional (For MSP Features)

4. **ConnectWise Manage API** (if using ticket integration)
   - Company ID, Public Key, Private Key, Client ID
   - Get from: ConnectWise > System > Members > API Members
   - Register for Client ID: https://developer.connectwise.com/ClientID

---

## 🎯 Step-by-Step First Run

### Step 1: Get Your API Keys

**OpenAI:**
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-...`)

**Pinecone (or skip if using Chroma):**
1. Sign up at https://www.pinecone.io
2. Create a new index:
   - Name: `msp-tickets` (or any name)
   - Dimension: `256`
   - Metric: `cosine`
3. Copy your API key and environment

### Step 2: Run Setup Script

**Windows:**
```batch
setup_and_run.bat
```

**Mac/Linux:**
```bash
./setup_and_run.sh
```

### Step 3: Configure .env File

The script will create a `.env` file and open it. Fill in:

```env
# Minimum configuration
DATASTORE=pinecone
BEARER_TOKEN=my-secret-token-12345
OPENAI_API_KEY=sk-your-key-here
EMBEDDING_DIMENSION=256
EMBEDDING_MODEL=text-embedding-3-large

# Pinecone (or skip if using Chroma)
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=your-environment
PINECONE_INDEX=msp-tickets
```

**Or for Chroma (local, no API keys needed):**
```env
DATASTORE=chroma
BEARER_TOKEN=my-secret-token-12345
OPENAI_API_KEY=sk-your-key-here
EMBEDDING_DIMENSION=256
EMBEDDING_MODEL=text-embedding-3-large
```

Save and close the file.

### Step 4: Run Again

Run the setup script again:
- Windows: `setup_and_run.bat`
- Mac/Linux: `./setup_and_run.sh`

Choose option **1** for the Enhanced server (recommended).

### Step 5: Test It!

Open your browser:
- **Web UI:** http://localhost:8000/search.html
- **Health Check:** http://localhost:8000/health
- **API Docs:** http://localhost:8000/docs

---

## 🎨 Using the Web UI

1. **Open:** http://localhost:8000/search.html

2. **Enter Bearer Token:**
   - First time: You'll be prompted for your bearer token
   - Enter the same token from your .env file
   - It's saved in browser for next time

3. **Upload Some Documents:**
   ```bash
   curl -X POST http://localhost:8000/upsert \
     -H "Authorization: Bearer your-token" \
     -H "Content-Type: application/json" \
     -d '{
       "documents": [{
         "text": "How to fix VPN issues: Restart the VPN client and reconnect.",
         "metadata": {
           "source": "file",
           "author": "IT Team"
         }
       }]
     }'
   ```

4. **Search:**
   - Type: "VPN problems"
   - See your document appear!

---

## 🔧 Alternative: Manual Setup (No Scripts)

If you prefer to do it manually:

### Option A: Using Poetry (Recommended)

```bash
# 1. Install Poetry
pip install poetry

# 2. Install dependencies
poetry install

# 3. Create .env file (copy from .env.example)
cp .env.example .env
# Edit .env with your keys

# 4. Run server
poetry run start-enhanced
```

### Option B: Using pip

```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
# Edit with your keys

# 5. Run server
python -m uvicorn server.main_enhanced:app --host 0.0.0.0 --port 8000
```

---

## 🐛 Troubleshooting

### "Python not found"
**Windows:**
- Reinstall Python and check "Add to PATH"
- Or add manually: Settings > System > About > Advanced > Environment Variables

**Mac:**
```bash
brew install python@3.11
```

**Linux:**
```bash
sudo apt update
sudo apt install python3.11
```

### "poetry: command not found"
```bash
# Just use pip instead
pip install poetry

# Or use python -m poetry
python -m poetry install
```

### ".env file errors"
- Make sure no quotes around values
- No spaces around `=`
- Example: `BEARER_TOKEN=abc123` (not `BEARER_TOKEN = "abc123"`)

### "OpenAI API error"
- Check your API key is correct
- Verify you have credits: https://platform.openai.com/usage
- Check key starts with `sk-`

### "Pinecone connection failed"
- Verify API key is correct
- Check environment name (e.g., `us-east-1-aws`)
- Make sure index exists with dimension 256

### "Port 8000 already in use"
```bash
# Windows: Find and kill process
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Mac/Linux:
lsof -ti:8000 | xargs kill -9
```

---

## 💡 Next Steps

Once you're running:

1. **Import Tickets** (if using ConnectWise):
   ```bash
   cd scripts/connectwise_import
   python example_usage.py 30  # Import last 30 days
   ```

2. **Test Search:**
   - Open http://localhost:8000/search.html
   - Try searching for issues

3. **Set Up Webhooks** (optional):
   - See `scripts/connectwise_import/README.md`
   - Auto-index tickets as they close

4. **Monitor Performance:**
   - http://localhost:8000/metrics
   - Check cache hit rate (should be 70%+)

5. **Train Your Team:**
   - Share the web UI link
   - Show them how to search
   - Watch productivity soar! 📈

---

## 📊 Cost Estimate

For a 10-person MSP team:

**OpenAI Costs:**
- First import (10,000 tickets): **$0.50** (one-time)
- Monthly queries (5,000): **$0.65**
- With caching (85% hit rate): **$0.10/month**

**Vector Database:**
- Pinecone: Free tier or $70/month
- Chroma: **Free** (local)
- Postgres: **Free** (self-hosted)

**Total: $0.10 - $70/month**

**ROI: Saves 20+ hours/week = $4,000+/month in labor**

---

## 🆘 Need Help?

1. **Check logs:**
   ```bash
   # The server prints helpful error messages
   ```

2. **Test health:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Review documentation:**
   - `PRODUCTION_FEATURES.md` - All features
   - `QUICKSTART_MSP.md` - MSP-specific setup
   - `scripts/connectwise_import/README.md` - Ticket import

4. **Common issues:**
   - All in this file above ↑

---

**That's it! You should be up and running.** 🎉

If you get stuck, the automatic setup scripts handle 95% of issues. Just run `setup_and_run.bat` (Windows) or `./setup_and_run.sh` (Mac/Linux) and follow the prompts!

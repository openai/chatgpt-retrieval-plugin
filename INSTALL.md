# Installation Methods

Choose the method that works best for you:

## 🚀 Method 1: Automatic Setup (Recommended)

**This is the easiest way!** Just run one file and everything is installed automatically.

### Windows
```batch
# Double-click this file:
setup_and_run.bat
```

### Mac / Linux
```bash
chmod +x setup_and_run.sh && ./setup_and_run.sh
```

The script will:
- ✅ Check Python version
- ✅ Install Poetry
- ✅ Install all dependencies
- ✅ Create .env file
- ✅ Start the server

**Done!** See [EASY_SETUP.md](EASY_SETUP.md) for detailed guide.

---

## 📦 Method 2: Poetry (Manual)

If you prefer to control each step:

```bash
# 1. Install Poetry
pip install poetry

# 2. Install dependencies
poetry install

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Run the server
poetry run start-enhanced
```

---

## 🐍 Method 3: pip + venv

If you don't want to use Poetry:

```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate it
source venv/bin/activate  # Mac/Linux
# OR
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 5. Run the server
python -m uvicorn server.main_enhanced:app --host 0.0.0.0 --port 8000
```

---

## 🐳 Method 4: Docker (Coming Soon)

```bash
# Build image
docker build -t msp-retrieval .

# Run container
docker run -p 8000:8000 --env-file .env msp-retrieval
```

---

## 🌐 Method 5: One-Line Cloud Deploy

### Deploy to Heroku
```bash
# Coming soon
heroku create my-retrieval-plugin
git push heroku main
```

### Deploy to Fly.io
```bash
# Coming soon
fly launch
fly deploy
```

---

## ⚙️ Configuration

After installation, you need to configure your `.env` file:

### Minimum Configuration

```env
DATASTORE=chroma  # or pinecone, postgres, etc.
BEARER_TOKEN=your-secret-token
OPENAI_API_KEY=sk-your-openai-key
EMBEDDING_DIMENSION=256
EMBEDDING_MODEL=text-embedding-3-large
```

### For Pinecone
```env
PINECONE_API_KEY=your-key
PINECONE_ENVIRONMENT=your-env
PINECONE_INDEX=your-index
```

### For Chroma (Local)
```env
CHROMA_COLLECTION=documents
CHROMA_IN_MEMORY=false
CHROMA_PERSISTENCE_DIR=./chroma_data
```

### For ConnectWise Integration
```env
CW_COMPANY_ID=yourcompany
CW_PUBLIC_KEY=your-key
CW_PRIVATE_KEY=your-key
CW_CLIENT_ID=your-client-id
```

See `.env.example` for all options.

---

## 🎯 Quick Test

After installation:

```bash
# 1. Check health
curl http://localhost:8000/health

# 2. Open web UI
open http://localhost:8000/search.html

# 3. View API docs
open http://localhost:8000/docs
```

---

## 🆘 Troubleshooting

### Python Not Found
- **Windows:** Reinstall Python, check "Add to PATH"
- **Mac:** `brew install python@3.11`
- **Linux:** `sudo apt install python3.11`

### Poetry Install Fails
```bash
# Try alternative installation
curl -sSL https://install.python-poetry.org | python3 -
```

### Dependencies Install Fails
```bash
# Clear cache and retry
poetry cache clear pypi --all
poetry install
```

### Port Already in Use
```bash
# Change port in command
uvicorn server.main_enhanced:app --port 8001
```

---

## 📚 Next Steps

- **Quick Start:** [EASY_SETUP.md](EASY_SETUP.md)
- **MSP Features:** [QUICKSTART_MSP.md](QUICKSTART_MSP.md)
- **Production Deployment:** [PRODUCTION_FEATURES.md](PRODUCTION_FEATURES.md)
- **ConnectWise Setup:** [scripts/connectwise_import/README.md](scripts/connectwise_import/README.md)

---

**Need help?** See [EASY_SETUP.md](EASY_SETUP.md) for detailed troubleshooting guide!

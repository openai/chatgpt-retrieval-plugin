#!/usr/bin/env python3
"""
Automatic setup and launcher for ChatGPT Retrieval Plugin
Checks dependencies and installs them if missing
Works on Windows, Mac, and Linux
"""
import sys
import subprocess
import os
import platform
from pathlib import Path

# Minimum Python version required
MIN_PYTHON_VERSION = (3, 10)
MAX_PYTHON_VERSION = (3, 11, 99)  # Exclude 3.12+ due to compatibility issues

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info[:2]

    if version < MIN_PYTHON_VERSION:
        print(f"❌ Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+ required")
        print(f"   You have Python {version[0]}.{version[1]}")
        print(f"\n📥 Download Python from: https://www.python.org/downloads/")
        sys.exit(1)

    if version >= (3, 12):
        print(f"⚠️  Warning: Python 3.12+ has compatibility issues")
        print(f"   You have Python {version[0]}.{version[1]}")
        print(f"   Recommended: Python 3.10 or 3.11")
        response = input("\n   Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)

    print(f"✓ Python {version[0]}.{version[1]} - OK")
    return True


def check_poetry():
    """Check if Poetry is installed, install if missing"""
    try:
        result = subprocess.run(
            ['poetry', '--version'],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            print(f"✓ Poetry installed - OK")
            return True
    except FileNotFoundError:
        pass

    print("📦 Poetry not found - installing...")

    # Install Poetry using pip
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'poetry'],
            check=True
        )
        print("✓ Poetry installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install Poetry")
        print("   Please install manually: https://python-poetry.org/docs/#installation")
        sys.exit(1)


def check_env_file():
    """Check if .env file exists, create from example if not"""
    env_file = Path('.env')
    env_example = Path('.env.example')

    if env_file.exists():
        print("✓ .env file found - OK")
        return True

    if env_example.exists():
        print("📝 Creating .env file from template...")
        env_example.read_text()
        # Copy example to .env
        with open(env_file, 'w') as f:
            f.write(env_example.read_text())

        print("⚠️  Please edit .env file with your API keys:")
        print("   - OPENAI_API_KEY")
        print("   - BEARER_TOKEN")
        print("   - DATASTORE configuration")
        print("\n   Edit .env and run this script again.")

        # Open .env in default editor
        if platform.system() == 'Windows':
            os.system(f'notepad {env_file}')
        elif platform.system() == 'Darwin':  # macOS
            os.system(f'open -t {env_file}')
        else:  # Linux
            os.system(f'xdg-open {env_file} || nano {env_file}')

        return False

    print("⚠️  No .env.example file found")
    print("   Creating basic .env template...")

    basic_env = """# ChatGPT Retrieval Plugin Configuration

# Required
DATASTORE=pinecone
BEARER_TOKEN=your-secret-token-here
OPENAI_API_KEY=sk-your-openai-key-here
EMBEDDING_DIMENSION=256
EMBEDDING_MODEL=text-embedding-3-large

# Pinecone (if using Pinecone)
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=your-environment
PINECONE_INDEX=your-index-name

# Optional: Logging
LOG_LEVEL=INFO
JSON_LOGS=false

# Optional: ConnectWise (for MSP features)
# CW_COMPANY_ID=yourcompany
# CW_PUBLIC_KEY=your-public-key
# CW_PRIVATE_KEY=your-private-key
# CW_CLIENT_ID=your-client-id
# CW_API_URL=https://api-na.myconnectwise.net
"""

    with open(env_file, 'w') as f:
        f.write(basic_env)

    print(f"✓ Created {env_file}")
    print("\n⚠️  Please edit .env file with your actual API keys")
    return False


def install_dependencies():
    """Install project dependencies using Poetry"""
    print("\n📦 Installing dependencies...")
    print("   This may take a few minutes...\n")

    try:
        # Use poetry to install dependencies
        subprocess.run(
            ['poetry', 'install'],
            check=True
        )
        print("\n✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("\n❌ Failed to install dependencies")
        print("   Try running manually: poetry install")
        sys.exit(1)


def check_dependencies_installed():
    """Check if dependencies are already installed"""
    try:
        result = subprocess.run(
            ['poetry', 'run', 'python', '-c', 'import fastapi'],
            capture_output=True,
            check=False
        )
        return result.returncode == 0
    except:
        return False


def run_server(mode='enhanced'):
    """Run the server"""
    print("\n🚀 Starting server...\n")

    if mode == 'enhanced':
        cmd = ['poetry', 'run', 'start-enhanced']
        print("   Using ENHANCED server with production features")
    else:
        cmd = ['poetry', 'run', 'start']
        print("   Using STANDARD server")

    print(f"\n   Server will be available at: http://localhost:8000")
    print(f"   Web UI: http://localhost:8000/search.html")
    print(f"   API Docs: http://localhost:8000/docs")
    print(f"   Health: http://localhost:8000/health\n")
    print("   Press Ctrl+C to stop\n")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
    except subprocess.CalledProcessError:
        print("\n❌ Server failed to start")
        print("   Check your .env file configuration")
        sys.exit(1)


def main():
    """Main setup and launch function"""
    print("=" * 60)
    print("  ChatGPT Retrieval Plugin - Auto Setup & Launch")
    print("=" * 60)
    print()

    # Check Python version
    check_python_version()

    # Check/install Poetry
    check_poetry()

    # Check/create .env file
    env_ready = check_env_file()
    if not env_ready:
        print("\n⏸️  Setup paused - configure .env file and run again")
        sys.exit(0)

    # Check if dependencies are installed
    if not check_dependencies_installed():
        print("\n📦 Dependencies not found")
        install_dependencies()
    else:
        print("✓ Dependencies already installed")

    print("\n" + "=" * 60)
    print("  Setup Complete!")
    print("=" * 60)

    # Ask which server to run
    print("\nWhich server would you like to start?")
    print("  1. Enhanced (with logging, caching, monitoring, webhooks)")
    print("  2. Standard (original server)")
    print("  3. Exit")

    choice = input("\nEnter choice (1-3) [1]: ").strip() or "1"

    if choice == "1":
        run_server('enhanced')
    elif choice == "2":
        run_server('standard')
    else:
        print("\n👋 Goodbye!")
        sys.exit(0)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled")
        sys.exit(0)

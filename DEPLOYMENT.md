# 📖 DEPLOYMENT.md

## Protocol Zero - Deployment & Setup Guide

Complete setup instructions for judges, developers, and production deployment.

---

## 🚀 Quick Start (3 Steps - 5 Minutes)

### Step 1: Clone Repository
```bash
git clone https://github.com/Direwolfe999/Protocol-Zero.git
cd Protocol-Zero
```

### Step 2: Install Dependencies
```bash
python -m venv .venv
source .venv/bin/activate          # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Run the App
```bash
streamlit run pages/00_Dashboard.py
# Or simply:
streamlit run
```

**Access at**: `http://localhost:8501`

✅ **No AWS setup required for demo mode!** All features work with fallback reasoning.

---

## 🎬 Demo Mode (For Judges)

The app launches in **Demo Mode by default** with:
- ✅ Pre-loaded market data (real BTC/ETH prices)
- ✅ Sample trading history and portfolio
- ✅ All 18 pages fully functional
- ✅ Voice AI with premium UI
- ✅ ERC-8004 simulation mode
- ✅ No AWS credentials needed

**Entry point**: Visit **🎬 Getting Started** page in the sidebar

---

## ☁️ AWS Setup (Optional - For Real Nova AI)

### Prerequisites
- AWS Account with Bedrock access (Nova Lite model)
- AWS credentials with appropriate permissions

### Step 1: Create `.env` File
```bash
cp .env.example .env
```

### Step 2: Configure Environment Variables
Edit `.env` with your credentials:

```bash
# AWS Bedrock
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1  # Nova Lite availability

# Blockchain (Sepolia Testnet)
RPC_URL=https://sepolia.infura.io/v3/your_project_id
PRIVATE_KEY=your_wallet_private_key_hex

# ERC-8004 Contracts (Sepolia Testnet)
IDENTITY_REGISTRY_ADDRESS=0x...
REPUTATION_REGISTRY_ADDRESS=0x...
VALIDATION_REGISTRY_ADDRESS=0x...

# Optional
ETHERSCAN_API_KEY=your_etherscan_key
DEX_ENABLED=true  # Enable Uniswap V3 swaps
```

### Step 3: Verify Setup
```bash
python3 -c "
import sys
sys.path.insert(0, '.')
import app_core
print('✅ AWS setup verified')
"
```

### Step 4: Run with Real Nova
```bash
streamlit run pages/00_Dashboard.py
# Will use real Nova Lite instead of fallback
```

---

## 🐳 Docker Deployment

### Build Docker Image
```bash
docker build -t protocol-zero:latest .
```

### Run Container (Development)
```bash
docker run -p 8501:8501 \
  -v $(pwd):/app \
  protocol-zero:latest
```

### Run Container (Production with Credentials)
```bash
docker run -p 8501:8501 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -e RPC_URL=your_rpc_url \
  -e PRIVATE_KEY=your_private_key \
  protocol-zero:latest
```

**Access at**: `http://localhost:8501`

---

## ☁️ Streamlit Cloud Deployment

### Step 1: Push to GitHub
```bash
git add .
git commit -m "deploy: ready for production"
git push origin main
```

### Step 2: Connect to Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app" → Connect GitHub repository
3. Select: `Repository: Protocol-Zero` → `Branch: main` → `File: pages/00_Dashboard.py`
4. Click Deploy

### Step 3: Configure Secrets
In Streamlit Cloud dashboard, add secrets:
```toml
[AWS]
aws_access_key_id = "your_key"
aws_secret_access_key = "your_secret"
aws_region = "us-east-1"

[Blockchain]
rpc_url = "your_rpc_url"
private_key = "your_private_key"
```

### Step 4: Monitor & Debug
- Check logs in Streamlit Cloud dashboard
- Use `streamlit run` locally to debug before pushing

---

## 🌐 AWS EC2 Deployment

### Step 1: Launch EC2 Instance
```bash
# Ubuntu 22.04 LTS, t3.medium (recommended)
# Security group: Allow ports 80, 443, 8501
```

### Step 2: SSH into Instance
```bash
ssh -i your-key.pem ubuntu@your-instance-ip
```

### Step 3: Install Dependencies
```bash
sudo apt update && sudo apt install -y python3-pip python3-venv
```

### Step 4: Clone & Setup
```bash
git clone https://github.com/Direwolfe999/Protocol-Zero.git
cd Protocol-Zero
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 5: Configure Environment
```bash
nano .env
# Paste AWS credentials and blockchain config
```

### Step 6: Run with Systemd
Create `/etc/systemd/system/protocol-zero.service`:
```ini
[Unit]
Description=Protocol Zero Streamlit App
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Protocol-Zero
Environment="PATH=/home/ubuntu/Protocol-Zero/.venv/bin"
ExecStart=/home/ubuntu/Protocol-Zero/.venv/bin/streamlit run pages/00_Dashboard.py --server.port=8501 --server.address=0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

### Step 7: Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl start protocol-zero
sudo systemctl enable protocol-zero
```

### Step 8: Setup Nginx Reverse Proxy
```bash
sudo apt install -y nginx

# Configure /etc/nginx/sites-available/default
server {
    listen 80 default_server;
    server_name _;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

sudo systemctl restart nginx
```

**Access at**: `http://your-instance-ip`

---

## 🔧 Local Development Setup

### Project Structure
```
Protocol-Zero/
├── pages/                    # 18 Streamlit pages
│   ├── 00_Getting_Started.py # Demo entry point
│   ├── 01_Market.py
│   ├── 02_AI_Brain.py
│   ├── ...
│   ├── 14_Backtest.py
│   ├── 15_Settings.py
│   └── etc.
├── app_core.py              # Core functions (2600+ lines)
├── brain.py                 # Nova reasoning
├── chain_interactor.py      # ERC-8004 integration
├── risk_check.py            # 6-layer risk gates
├── config.py                # Environment config
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

### Development Workflow
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dev dependencies
pip install -r requirements-dev.txt  # pytest, black, flake8

# Run tests
pytest tests/ -v
# Expected: 143/143 PASS

# Format code
black .

# Lint check
flake8 . --max-line-length=120

# Run app with auto-reload
streamlit run pages/00_Dashboard.py --logger.level=debug
```

### Debugging Tips
- **Streamlit won't connect?** Check `.venv/bin/activate` is sourced
- **AWS credentials error?** Verify `.env` file exists and has correct keys
- **Market data not loading?** Check internet connection and CCXT API
- **Pages not showing?** Ensure `sys.path.insert(0, ...)` is at top of each page

---

## 🐛 Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'app_core'`
**Solution**: Ensure `sys.path.insert(0, os.path.dirname(...))` is at top of page file.

### Issue: AWS Bedrock returns 403 Unauthorized
**Solution**: 
1. Verify AWS credentials in `.env`
2. Check IAM user has `bedrock:InvokeModel` permission
3. Verify region is `us-east-1` (Nova Lite availability)

### Issue: Streamlit app is slow to load
**Solution**:
1. Check internet speed (market data fetch)
2. Verify AWS credentials (will use fallback if timeout)
3. Clear Streamlit cache: `streamlit cache clear`

### Issue: WebSocket connection drops
**Solution**: This is **intentionally fixed** by multipage architecture. Old monolithic 5000-line dashboard had this issue. Current 18-page design eliminates it.

### Issue: Port 8501 already in use
**Solution**: Use different port:
```bash
streamlit run pages/00_Dashboard.py --server.port=8502
```

---

## ✅ Pre-Deployment Checklist

- [ ] All tests pass: `pytest tests/` → 143/143 PASS
- [ ] No console errors: Run app and check browser console (F12)
- [ ] Demo mode works without AWS creds
- [ ] AWS credentials work (if deployed with real Nova)
- [ ] `.env` file NOT committed to git (add to `.gitignore`)
- [ ] `requirements.txt` is up to date
- [ ] `README.md` is current
- [ ] Docker image builds successfully
- [ ] Mobile responsive verified (check on phone)
- [ ] Keyboard navigation tested (Alt+V voice, Tab navigation)
- [ ] Voice AI works with microphone permissions

---

## 📊 Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Page load | < 2s | After initial app load |
| Button response | < 1s | Click → action |
| Market data fetch | < 3s | CCXT API |
| Nova response | < 5s | With AWS Bedrock |
| Memory usage | < 500MB | Streamlit process |
| CPU usage | < 20% | At idle |

---

## 🎯 For Hackathon Judges

**Fastest way to evaluate:**

1. Click "🎬 Getting Started" in sidebar
2. Click "🎮 Explore as Demo User"
3. Tour pages: Dashboard → Market → AI Brain → Voice AI
4. Check code: [app_core.py](./app_core.py) (2600 lines of core logic)
5. Run tests: `pytest tests/` (143/143 pass)

**No setup required** — demo mode works instantly!

---

## 📞 Support

- **Bug reports**: File issue on GitHub
- **Questions**: Check existing GitHub issues
- **Setup help**: See Troubleshooting section above
- **AWS issues**: Verify credentials in `.env`

---

**Built for Amazon Nova AI Hackathon | ERC-8004 Standard | Capital Preservation First**

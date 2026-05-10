# 🛡️ Guardian: AI Financial Immune System

Guardian is a premium, multi-agent AI platform designed to audit your financial life. It goes beyond simple tracking by acting as an "immune system" for your money—detecting anomalies, identifying reward leaks, and orchestrating a personalized strategy to hit your financial goals.

![Guardian Dashboard](https://raw.githubusercontent.com/VarunxS/Guardian-AI-Financial-System/main/frontend/public/guardian_preview.png)

## 🚀 Key Features

### 🧠 1. Strategic Financial Intelligence
*   **Agentic Audit**: Guardian's multi-agent pipeline (Insights, Rewards, and Strategy agents) analyzes your bank statements to find hidden subscriptions, unusual spending patterns, and double-charges.
*   **Behavioral Friction Analysis**: Understand exactly how much your "coffee habits" or impulse buys are delaying your long-term goals (Home, Car, Emergency Fund).
*   **Dynamic Forecasts**: Real-time spending projections based on your historical data, giving you a clear view of your next month's surplus.

### 💳 2. Reward & Benefit Optimization
*   **Card Intelligence**: Guardian cross-references your spending against a database of Indian credit card benefits (HDFC, ICICI, Amex, SBI, etc.).
*   **Hindsight Engine**: It shows you exactly how much money you *lost* by using the wrong card for a specific transaction and recommends the "Alpha Card" for your profile.

### 💬 3. AskGuardian (Chat Assistant)
*   **RAG-Powered Conversations**: Chat with your financial data using Retrieval-Augmented Generation. Ask questions like *"Can I afford a MacBook next month?"* or *"Why is my grocery spend increasing?"*.
*   **Web Research Integration**: Powered by **Exa AI**, Guardian can search the web for the latest financial news, card offers, and investment trends to give you up-to-date advice.

### 🔐 4. Privacy-First "BYOK" Architecture
*   **Bring Your Own Key**: You have total control over the AI providers. Use Google Gemini, OpenAI, or OpenRouter with your own API keys.
*   **Secure Persistence**: All data is stored in your private Supabase instance, with a one-click **Purge System Data** option to wipe everything instantly.

## 🛠️ Technology Stack

*   **Frontend**: React (Vite), Tailwind CSS, Framer Motion (for premium animations).
*   **Backend**: FastAPI (Python), LangChain, LangGraph.
*   **Intelligence**: OpenAI (GPT-4o), Google Gemini (1.5 Pro/Flash), Exa AI (Search).
*   **Memory**: Supabase (PostgreSQL), ChromaDB (Vector Store).

## 📥 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/VarunxS/Guardian-AI-Financial-System.git
cd Guardian-AI-Financial-System
```

### 2. Backend Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure .env
cp .env.example .env # Fill in your Supabase & AI keys
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 🏗️ Architecture Idle
Guardian uses a **Supervisor Agent** to coordinate between specialized nodes:
1.  **Insights Agent**: Scans for anomalies and unusual payments.
2.  **Rewards Agent**: Optimizes card benefits and cashback.
3.  **Budget & Goals Agent**: Calculates surplus and goal timelines.
4.  **Consultant Agent**: Provides the final executive summary and recommendations.

---

Built with ❤️ for financial freedom.

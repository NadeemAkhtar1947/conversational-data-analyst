# Conversational Data Analyst

An AI-powered analytics platform that lets you analyze data using natural language. Ask questions in plain English and get instant SQL queries, visualizations, and insights!

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- 🗣️ **Natural Language Queries** - Ask questions in plain English, no SQL knowledge needed
-  **Multiple Datasets** - Pre-loaded datasets (Superstore, IPL, Netflix, World Population) + CSV upload
-  **Multi-Agent AI System** - Context Rewriter, SQL Generator, Analysis, and Visualization agents
-  **Auto Visualizations** - Smart chart suggestions (line, bar, pie charts)
-  **Nova AI Chatbot** - Built-in assistant to help navigate the platform
-  **Draggable Dataset Viewer** - Preview and explore your data
-  **Secure** - Environment-based API key management

## Tech Stack

**Backend:**
- FastAPI (Python)
- PostgreSQL (Neon - Serverless)
- DuckDB (In-memory CSV processing)
- asyncpg (Async PostgreSQL driver)

**AI/ML:**
- Groq API (Llama 3.1 70B for SQL generation)
- Groq API (Llama 3.3 70B for chatbot)
- sentence-transformers (Semantic search)

**Frontend:**
- Vanilla JavaScript
- Tailwind CSS
- Chart.js

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL database (or use Neon free tier)
- Groq API key ([Get free key](https://console.groq.com))

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/NadeemAkhtar1947/conversational-data-analyst.git
cd conversational-data-analyst
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
Create a `.env` file:
```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
GROQ_API_KEY=your_groq_api_key_here
```

4. **Run the application**
```bash
uvicorn backend.main:app --reload --port 7860
```

5. **Open your browser**
```
http://localhost:7860
```

## Usage

1. **Select a Dataset** - Choose from sidebar or upload your own CSV
2. **Ask Questions** - Type natural language queries like:
   - "What are the top 5 sales by region?"
   - "Show me monthly trends for the last 6 months"
   - "Which products have the highest profit margin?"
3. **Get Insights** - Receive SQL query, results, analysis, and visualizations
4. **Continue Conversation** - Ask follow-up questions with context awareness


## Deployment

### Deploy to Render (Free)

1. **Push to GitHub** (already done)
2. **Go to [Render](https://render.com)** and sign up
3. **Create Blueprint** - Connect your repo
4. **Set Environment Variables:**
   - `DATABASE_URL`
   - `GROQ_API_KEY`
5. **Deploy!** - Takes ~5-10 minutes

 **Detailed Guide:** [DEPLOY.md](DEPLOY.md)

### Keep It Awake (Optional)
Render free tier sleeps after 15 minutes. Set up a cron job to keep it active:

 **Step-by-step:** [KEEP_ALIVE_SETUP.md](KEEP_ALIVE_SETUP.md)

## Project Structure

```
conversational-data-analyst/
├── backend/
│   ├── agents/              # Multi-agent system
│   │   ├── context_rewriter.py
│   │   ├── sql_generator.py
│   │   ├── analysis_agent.py
│   │   └── visualization_agent.py
│   ├── utils/
│   │   ├── database.py      # PostgreSQL manager
│   │   ├── session.py       # Session management
│   │   └── sql_validator.py
│   └── main.py              # FastAPI app
├── static/
│   ├── chat.html            # Main UI
│   ├── chat.js              # Frontend logic
│   ├── chatbot.js           # Nova AI chatbot
│   └── chatbot.css
├── data/                    # CSV files
├── .env                     # Environment variables (not in git)
├── requirements.txt
├── render.yaml             # Render deployment config
└── README.md
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `GROQ_API_KEY` | Groq API key for LLM | Yes |

### Supported Datasets

1. **Superstore Sales** - 9,994 rows of retail data
2. **E-Commerce Sales** - 9,994 rows of online sales
3. **IPL Cricket** - 1,169 matches of IPL data
4. **Netflix Titles** - 8,807 movies and TV shows
5. **World Population** - 234 rows of population data (1970-2022)
6. **Custom CSV** - Upload your own datasets

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Nadeem Akhtar**

- GitHub: [@NadeemAkhtar1947](https://github.com/NadeemAkhtar1947)
- LinkedIn: [nadeem-akhtar](https://www.linkedin.com/in/nadeem-akhtar-/)
- Portfolio: [nsde.netlify.app](https://nsde.netlify.app/)
- Email: nadeemnns2000@gmail.com

## Acknowledgments

- [Groq](https://groq.com) for lightning-fast LLM inference
- [Neon](https://neon.tech) for serverless PostgreSQL
- [Render](https://render.com) for free hosting
- [Tailwind CSS](https://tailwindcss.com) for beautiful UI

## Stats

![GitHub stars](https://img.shields.io/github/stars/NadeemAkhtar1947/conversational-data-analyst?style=social)
![GitHub forks](https://img.shields.io/github/forks/NadeemAkhtar1947/conversational-data-analyst?style=social)

---

 **Star this repo** if you find it helpful!

🐛 **Found a bug?** [Open an issue](https://github.com/NadeemAkhtar1947/conversational-data-analyst/issues)

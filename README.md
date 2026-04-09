# AI Agent POC
Single AI Agent dengan SQLite + RAG + OpenRouter API

Belajar membina AI Agent dari scratch - tanpa LangChain!

✨ Features
🧠 Agent Loop: Reason → Act → Observe pattern
📊 SQLite Search: Structured data lookup (search_docs)
📄 Markdown RAG: Documentation search (search_markdown)
🌐 OpenRouter: Gunakan apa-apa model (Gemma, GPT, Claude, etc.)
💬 Bahasa Melayu: Full BM system prompts
📝 Audit Logging: Track semua agent actions
🚀 Quick Start
Prerequisites
Python 3.11+
OpenRouter API key (Free)
Installation

### Clone repositorygit clone https://github.com/hardyweb/ai-agent-poc.gitcd ai-agent-poc
###Create virtual environment
### python -m venv .venvsource .venv/bin/activate  

### Linux/Mac/Wsl# Install dependenciespip install openai python-dotenv rich prompt-toolkit
### Setup environmentcp .env.example .env
### Edit .env dan masukkan OpenRouter API key
### Run!python app.py


##  Project Structure
```bash
ai-agent-poc/
├── app.py           # CLI entry point
├── config.py        # Configuration
├── agent/           # Agent core (loop, prompts)
├── tools/           # SQLite search tool
├── rag/             # Markdown RAG search
├── db/              # Database schema & seeds
└── docs/            # Markdown knowledge base
```
## Usage Examples

```bash

# Interactive mode
python app.py

# Single question
python app.py -q "Apa itu Python?"

# Try these questions:
# - "hello, siapa awak?"
# - "terangkan machine learning"
# - "apa kategori dokumen yang ada?"

```


# Tech Stack

Language: Python 3.11+
LLM Provider: OpenRouter API
Database: SQLite
CLI: Rich + Prompt Toolkit
No LangChain: Pure OpenAI SDK implementation

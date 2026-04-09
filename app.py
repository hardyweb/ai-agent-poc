#!/usr/bin/env python3
"""
AI Agent POC - Command Line Interface
=====================================
Run: python app.py
Then type questions interactively!
"""

import sys
import argparse
from pathlib import Path
import sqlite3
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from config import Config
from agent.core import AIAgent

console = Console()


def setup_database():
    """Initialize SQLite database with schema and sample data"""
    console.print("[bold blue]📦 Setting up database...[/]")
    
    # Ensure directory exists
    Config.DB_DIR.mkdir(exist_ok=True)
    
    # Read and execute schema
    schema_path = Path(__file__).parent / "db" / "schema.sql"
    seed_path = Path(__file__).parent / "db" / "seed_data.sql"
    
    conn = sqlite3.connect(str(Config.DB_PATH))
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript(schema_path.read_text())
    
    # Seed sample data (check if empty first)
    cursor.execute("SELECT COUNT(*) FROM documents")
    if cursor.fetchone()[0] == 0:
        cursor.executescript(seed_path.read_text())
        console.print("[green]✓ Sample data inserted[/]")
    else:
        console.print("[dim]Database already has data[/]")
    
    conn.commit()
    conn.close()
    
    console.print(f"[green]✓ Database ready at:[/] {Config.DB_PATH}\n")

# After setup_database(), add this:
from rag.markdown_search import get_searcher

console.print("[bold blue]📄 Loading markdown documents...[/]")
md_searcher = get_searcher()  # This loads all .md files
console.print(f"[green]✓ Ready with {len(md_searcher.documents)} documents[/]\n")

def interactive_mode(agent: AIAgent):
    """Run interactive chat session"""
    console.print(Markdown("""
# 🤖 AI Agent POC - Interactive Mode

**Available Commands:**
- Type your question normally
- `/reset` - Clear conversation history  
- `/stats` - Show session statistics
- `/quit` or `/exit` - Exit

**Try these questions:**
1. "What is Python?"
2. "Tell me about SQLite databases"
3. "How do AI agents work?"
4. "Show me documents about REST APIs"
5. "What categories of docs do you have?"

---
"""))
    
    session = PromptSession(history=FileHistory('.agent_history'))
    
    while True:
        try:
            user_input = session.prompt("\n[bold green]You:[/] ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ['/quit', '/exit', '/q']:
                console.print("\n[yellow]Goodbye! 👋[/]\n")
                break
            
            elif user_input.lower() == '/reset':
                agent.reset_conversation()
                console.print("[cyan]Conversation cleared.[/]")
                continue
            
            elif user_input.lower() == '/stats':
                stats = agent.get_stats()
                console.print(f"\n[dim]Stats: {stats}[/]\n")
                continue
            
            # Run agent
            agent.run(user_input, verbose=True)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type /quit to exit.[/]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


def single_question_mode(agent: AIAgent, question: str):
    """Answer a single question and exit"""
    answer = agent.run(question, verbose=True)
    print(answer)


def main():
    parser = argparse.ArgumentParser(
        description='AI Agent POC - Single Agent with SQLite + OpenRouter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app.py                          # Interactive mode
  python app.py -q "What is Python?"     # Single question
  python app.py --setup                  # Setup DB only
        """
    )
    parser.add_argument('-q', '--question', help='Ask a single question')
    parser.add_argument('--setup-only', action='store_true', help='Setup database and exit')
    parser.add_argument('--no-setup', action='store_true', help='Skip database setup')
    
    args = parser.parse_args()
    
    # Show banner
    console.print(Panel.fit(
        "[bold cyan]🤖 AI Agent POC[/]\n"
        "[dim]Single Agent • SQLite • OpenRouter[/]",
        border_style="cyan"
    ))
    
    # Setup database
    if not args.no_setup:
        setup_database()
        if args.setup_only:
            return
    
    # Initialize agent
    try:
        agent = AIAgent()
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        console.print("[dim]Get API key from: https://openrouter.ai/keys[/]")
        sys.exit(1)
    
    # Run mode
    if args.question:
        single_question_mode(agent, args.question)
    else:
        interactive_mode(agent)


if __name__ == "__main__":
    main()

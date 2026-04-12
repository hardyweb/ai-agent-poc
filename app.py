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
from rag.markdown_search import reload_markdown_documents, list_markdown_documents
from rag.file_watcher import get_watcher
from memory.manager import MemoryManager

console = Console()


def setup_database():
    """Initialize SQLite database with schema and sample data"""
    console.print("[bold blue]📦 Setting up database...[/]")

    # Ensure directory exists
    Config.DB_DIR.mkdir(exist_ok=True)

    # Read and execute schema
    schema_path = Path(__file__).parent / "db" / "schema.sql"
    seed_path = Path(__file__).parent / "db" / "seed_data.sql"
    new_data_path = Path(__file__).parent / "db" / "add_new_data.sql"

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

    # Auto-run add_new_data.sql if exists (only inserts new data)
    if new_data_path.exists():
        new_data_content = new_data_path.read_text()
        # Only run if not empty/comment-only
        clean_content = "\n".join(
            line
            for line in new_data_content.split("\n")
            if line.strip() and not line.strip().startswith("--")
        )
        if clean_content.strip():
            cursor.executescript(new_data_content)
            console.print("[green]✓ New data inserted from add_new_data.sql[/]")

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
    console.print(
        Markdown("""
# 🤖 AI Agent POC - Interactive Mode

**Available Commands:**
- Type your question normally
- `/reset` - Clear conversation history  
- `/stats` - Show session statistics
- `/reload` - Force reload markdown documents
- `/reload-smart` - Check & reload if changes detected
- `/add` - Add new data from add_new_data.sql
- `/docs` - List all loaded documents
- `/profile` - Show user profile & memories
- `/memory list` - Show all memories
- `/memory add X=Y` - Add memory manually
- `/memory delete X` - Delete memory
- `/memory clear` - Clear all memories
- `/forget X` - Quick delete memory
- `/session` - Session statistics
- `/quit` or `/exit` - Exit

**Try these questions:**
1. "What is Python?"
2. "Tell me about SQLite databases"
3. "How do AI agents work?"
4. "Show me documents about REST APIs"
5. "What categories of docs do you have?"

---
""")
    )

    session = PromptSession(history=FileHistory(".agent_history"))

    while True:
        try:
            user_input = session.prompt("\n[bold green]You:[/]").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ["/quit", "/exit", "/q"]:
                console.print("\n[yellow]Goodbye! 👋[/]\n")
                break

            elif user_input.lower() == "/reset":
                agent.reset_conversation()
                console.print("[cyan]Conversation cleared.[/]")
                continue

            elif user_input.lower() == "/stats":
                stats = agent.get_stats()
                console.print(f"\n[dim]Stats: {stats}[/]\n")
                continue

            # ==================== MEMORY COMMANDS ====================

            elif user_input.lower().startswith("/profile"):
                console.print("\n[bold cyan]👤 User Profile & Memories:[/]\n")
                memory = MemoryManager(user_id="default")
                profile = memory.get_profile()
                memories = memory.get_all_memories()

                console.print(
                    Panel(
                        f"[bold]Name:[/] {profile.get('display_name') or 'Not set'}\n"
                        f"[bold]Sessions:[/] {profile['total_sessions']}\n"
                        f"[bold]Messages:[/] {profile['total_messages']}\n"
                        f"[bold]Last seen:[/] {profile.get('last_seen_at') or 'N/A'}",
                        title="Profile",
                        border_style="cyan",
                    )
                )

                if memories:
                    console.print("\n[bold cyan]Memories:[/]")
                    for mem in memories:
                        console.print(
                            Panel(
                                f"[bold]{mem['key']}[/] = {mem['value']}\n"
                                f"[dim]Type: {mem['type']} | Confidence: {mem['confidence']}[/]",
                                border_style="green",
                                padding=(0, 1),
                            )
                        )
                else:
                    console.print("\n[dim]No memories stored yet.[/]")
                console.print()
                continue

            elif user_input.lower().startswith("/memory"):
                parts = user_input.lower().split()
                memory = MemoryManager(user_id="default")

                if len(parts) == 1 or parts[1] == "list":
                    memories = memory.get_all_memories()
                    console.print("\n[bold cyan]All Memories:[/]")
                    if memories:
                        for mem in memories:
                            console.print(
                                f"  {mem['key']} = {mem['value']} ({mem['type']})"
                            )
                    else:
                        console.print("[dim]No memories.[/]")
                    console.print()
                    continue

                elif parts[1] == "add" and len(parts) >= 3:
                    key_value = " ".join(parts[2:]).split("=", 1)
                    if len(key_value) == 2:
                        key, value = key_value[0].strip(), key_value[1].strip()
                        memory.remember(key, value, source="manual")
                        console.print(f"[green]✓ Added:[/] {key} = {value}\n")
                    else:
                        console.print("[red]Format: /memory add key=value[/]")
                    continue

                elif parts[1] == "delete" and len(parts) >= 3:
                    key = " ".join(parts[2:])
                    if memory.forget(key):
                        console.print(f"[green]✓ Deleted:[/] {key}\n")
                    else:
                        console.print(f"[dim]Key not found:[/] {key}\n")
                    continue

                elif parts[1] == "clear":
                    confirm = console.input(
                        "[yellow]⚠️ Delete ALL memories? Type 'yes' to confirm: [/]"
                    )
                    if confirm.lower() == "yes":
                        memory.forget_all()
                        console.print("[green]✓ All memories cleared.[/]\n")
                    else:
                        console.print("[dim]Cancelled.[/]\n")
                    continue

                else:
                    console.print(
                        "Usage: /memory [list|add key=value|delete key|clear]\n"
                    )
                    continue

            elif user_input.lower().startswith("/forget"):
                parts = user_input.lower().split()
                if len(parts) >= 2:
                    memory = MemoryManager(user_id="default")
                    key = " ".join(parts[1:])
                    if memory.forget(key):
                        console.print(f"[green]✓ Forgotten:[/] {key}\n")
                    else:
                        console.print(f"[dim]Key not found:[/] {key}\n")
                    continue

            elif user_input.lower() == "/session":
                memory = MemoryManager(user_id="default")
                stats = memory.get_stats()
                console.print(
                    Panel(
                        f"[bold]User:[/] {stats['user_id']}\n"
                        f"[bold]Sessions:[/] {stats['total_sessions']}\n"
                        f"[bold]Messages:[/] {stats['total_messages']}\n"
                        f"[bold]Memories:[/] {stats['total_memories']}\n"
                        f"[bold]Last seen:[/] {stats['last_seen_at'] or 'N/A'}",
                        title="Session Stats",
                        border_style="purple",
                    )
                )
                console.print()
                continue

            # ==================== NEW COMMANDS ====================

            elif user_input.lower() == "/reload":
                console.print("\n[bold blue]🔄 Reloading markdown documents...[/]\n")
                result = reload_markdown_documents(force=True, verbose=True)

                if result["success"]:
                    console.print(
                        f"[green]✓ Reload complete! {result['docs_loaded']} documents loaded[/]\n"
                    )
                else:
                    console.print("[red]✗ Reload failed[/]\n")
                continue

            elif user_input.lower() == "/reload-smart":
                console.print("\n[bold blue]🔍 Checking for changes...[/]\n")
                result = reload_markdown_documents(force=False, verbose=True)

                if result["reloaded"]:
                    console.print(
                        f"[green]✓ Changes detected! Reloaded {result['docs_loaded']} documents[/]\n"
                    )
                else:
                    console.print(
                        "[dim]✓ No changes detected - documents up to date[/]\n"
                    )
                continue

            elif user_input.lower() == "/add":
                console.print(
                    "\n[bold blue]📥 Adding new data from add_new_data.sql...[/]\n"
                )
                new_data_path = Path(__file__).parent / "db" / "add_new_data.sql"

                if not new_data_path.exists():
                    console.print("[red]✗ add_new_data.sql not found[/]\n")
                    continue

                conn = sqlite3.connect(str(Config.DB_PATH))
                cursor = conn.cursor()

                new_data_content = new_data_path.read_text()
                clean_content = "\n".join(
                    line
                    for line in new_data_content.split("\n")
                    if line.strip() and not line.strip().startswith("--")
                )

                if not clean_content.strip():
                    console.print(
                        "[dim]✓ No new data to add (add_new_data.sql is empty)[/]\n"
                    )
                else:
                    cursor.executescript(new_data_content)
                    conn.commit()
                    console.print("[green]✓ New data added![/]\n")

                conn.close()
                continue

            elif user_input.lower() == "/docs":
                console.print("\n[bold blue]📄 Loaded Documents:[/]\n")
                result = list_markdown_documents()

                if result["success"]:
                    console.print(
                        f"[dim]Total: {result['total_documents']} documents, {result['total_chunks']} chunks[/]\n"
                    )

                    for doc in result["documents"]:
                        console.print(
                            Panel(
                                f"[bold]{doc['filename']}[/]\n"
                                f"[dim]Size: {doc['size_kb']} KB | Modified: {doc['modified']}[/]\n\n"
                                f"{doc['content_preview']}",
                                border_style="green",
                                padding=(0, 2),
                            )
                        )

                    # Also show file watcher stats
                    try:
                        watcher = get_watcher()
                        watcher_stats = watcher.get_stats()
                        console.print(
                            f"\n[dim]File Watcher: {watcher_stats['files_tracked']} files tracked[/]"
                        )
                        if watcher_stats["recent_changes"]:
                            console.print(
                                f"[dim]Recent changes: {watcher_stats['recent_changes']}[/]"
                            )
                    except:
                        pass
                else:
                    console.print("[red]✗ Failed to load document info[/]")

                console.print()
                continue

            # ====================================================

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


try:
    from tools.vector_search import get_vector_search

    vector_search = get_vector_search()
    stats = vector_search.get_stats()
    console.print("[bold purple]🧠 Vector Search:[/] ChromaDB ready")
    console.print(f"[dim]   Documents indexed: {stats['total_documents']}[/]")
except Exception as e:
    console.print("[dim]⚠️  Vector Search: Not available (keyword search only)[/]")
    console.print(f"[dim]   Reason: {e}[/]")


def main():
    parser = argparse.ArgumentParser(
        description="AI Agent POC - Single Agent with SQLite + OpenRouter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app.py                          # Interactive mode
  python app.py -q "What is Python?"     # Single question
  python app.py --setup                  # Setup DB only
        """,
    )
    parser.add_argument("-q", "--question", help="Ask a single question")
    parser.add_argument(
        "--setup-only", action="store_true", help="Setup database and exit"
    )
    parser.add_argument("--no-setup", action="store_true", help="Skip database setup")

    args = parser.parse_args()

    # Show banner
    console.print(
        Panel.fit(
            "[bold cyan]🤖 AI Agent POC[/]\n[dim]Single Agent • SQLite • OpenRouter[/]",
            border_style="cyan",
        )
    )

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

"""
AI Agent Core - Custom Agent Loop (Hybrid: SQLite + RAG)
=========================================================
Supports TWO tools:
1. search_docs - SQLite database search
2. search_markdown - Markdown/RAG document search
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from config import Config
from tools.search_docs import search_docs, TOOL_SCHEMA as DOCS_TOOL_SCHEMA
from rag.markdown_search import search_markdown, MARKDOWN_TOOL_SCHEMA
from agent.prompts import SYSTEM_PROMPT, MEMORY_CONTEXT_SECTION
from rag.markdown_search import reload_markdown_documents
from memory.manager import MemoryManager
from memory.extractor import MemoryExtractor

# Setup logging
Config.LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[logging.FileHandler(Config.LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

console = Console()


class AIAgent:
    """
    AI Agent with dual tool capability:
    - SQLite database search
    - Markdown/RAG document search
    """

    def __init__(self):
        Config.validate()

        # Initialize OpenAI client pointing to OpenRouter
        self.client = OpenAI(
            api_key=Config.OPENROUTER_API_KEY, base_url=Config.OPENROUTER_BASE_URL
        )

        self.model = Config.MODEL
        self.max_rounds = Config.MAX_TOOL_ROUNDS

        # 🔥🔥🔥 CRITICAL: Both tools must be here!
        self.tools = [
            DOCS_TOOL_SCHEMA,  # Tool 1: SQLite search
            MARKDOWN_TOOL_SCHEMA,  # Tool 2: Markdown/RAG search
        ]

        # Log available tools
        tool_names = [t["function"]["name"] for t in self.tools]
        logger.info(f"🤖 Agent initialized | Model: {self.model} | Tools: {tool_names}")

        # Initialize memory manager
        self.memory = MemoryManager(user_id="default")
        self.memory_extractor = MemoryExtractor()

        # Build system prompt with memory context
        system_content = SYSTEM_PROMPT
        memory_context = self.memory.build_context_string()
        if memory_context:
            system_content += "\n\n" + MEMORY_CONTEXT_SECTION.format(
                memory_context=memory_context
            )

        # Conversation history (for context)
        self.messages = [{"role": "system", "content": system_content}]

        # Audit log
        self.interaction_log: List[Dict] = []

    def _log_interaction(self, round_num: int, phase: str, content: Any):
        """Log each interaction step for auditing"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "round": round_num,
            "phase": phase,
            "content": str(content)[:500] if content else "",
        }
        self.interaction_log.append(log_entry)
        logger.debug(f"[Round {round_num}] {phase.upper()}: {str(content)[:200]}")

    def _execute_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """
        Execute a tool function by name.
        Supports BOTH tools!
        """
        logger.info(f"🔧 Executing tool: [{tool_name}] with args: {arguments}")

        # 🔥🔥🔥 AUTO-RELOAD: Check for markdown changes before search
        if tool_name == "search_markdown":
            try:
                # Smart reload (only if changes detected)
                reload_markdown_documents(force=False, verbose=False)
            except Exception as e:
                logger.debug(f"Auto-reload check skipped: {e}")

        # 🔥 Tool 1: SQLite Database Search
        if tool_name == "search_docs":
            try:
                result = search_docs(**arguments)
                return result
            except Exception as e:
                logger.error(f"search_docs error: {e}")
                return {"success": False, "error": str(e), "results": []}

        # 🔥 Tool 2: Markdown/RAG Search
        elif tool_name == "search_markdown":
            try:
                result = search_markdown(**arguments)
                return result
            except Exception as e:
                logger.error(f"search_markdown error: {e}")
                return {"success": False, "error": str(e), "results": []}

        # Unknown tool
        else:
            error_msg = f"❌ Unknown tool: {tool_name}. Available tools: search_docs, search_markdown"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "results": []}

    def _display_tool_call(self, tool_name: str, args: Dict):
        """Pretty print tool execution"""
        # Choose icon based on tool type
        icon = "📊" if tool_name == "search_docs" else "📄"

        console.print(
            Panel(
                f"[bold cyan]{icon} Tool:[/] {tool_name}\n"
                f"[dim]Arguments:[/]\n{json.dumps(args, indent=2)}",
                title="Agent Action",
                border_style="cyan",
                padding=(1, 2),
            )
        )

    def _display_result(self, result: Dict, tool_name: str = ""):
        """Pretty print tool result"""
        if result.get("success"):
            count = result.get("count", 0)

            # Different formatting based on tool
            if tool_name == "search_markdown":
                content = f"[green]✓ Found {count} document sections[/]\n\n"
                for doc in result.get("results", []):
                    content += f"[bold]📄 {doc['source']}[/]\n"
                    content += f"[dim]Section: {doc['section']}[/] (Score: {doc.get('score', 'N/A')})\n"
                    content += f"{doc['content'][:200]}...\n\n"
            else:
                content = f"[green]✓ Found {count} results[/]\n\n"
                for doc in result.get("results", []):
                    content += f"[bold]{doc['title']}[/] ([dim]{doc['category']}[/])\n"
                    content += f"{doc['content'][:150]}...\n\n"
        else:
            content = f"[red]✗ Error:[/] {result.get('error', 'Unknown')}"

        console.print(
            Panel(content, title="Observation", border_style="green", padding=(1, 2))
        )

    def run(self, user_message: str, verbose: bool = True) -> str:
        """
        Main agent loop - REASON → ACT → OBSERVE → REPEAT
        """
        if verbose:
            console.print(
                Panel(
                    f"[bold]Question:[/] {user_message}",
                    title="👤 User Input",
                    border_style="blue",
                    padding=(1, 2),
                )
            )

        # Add user message to conversation
        self.messages.append({"role": "user", "content": user_message})

        start_time = time.time()

        # === AGENT LOOP ===
        for round_num in range(1, self.max_rounds + 1):
            logger.info(f"\n{'=' * 50}")
            logger.info(f"🔄 ROUND {round_num}/{self.max_rounds}")

            # STEP 1: REASON - Ask LLM what to do
            self._log_interaction(round_num, "reason", "Calling LLM for reasoning...")

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=self.tools,
                    temperature=Config.TEMPERATURE,
                    tool_choice="auto",
                )
            except Exception as e:
                logger.error(f"LLM API error: {e}")
                return f"❌ API Error: {str(e)}"

            message = response.choices[0].message

            # Check if LLM wants to call a tool
            if message.tool_calls and len(message.tool_calls) > 0:
                # STEP 2: ACT - Execute the tool(s)
                tool_call = message.tool_calls[0]
                tool_name = tool_call.function.name

                # Parse arguments safely
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse arguments: {e}")
                    arguments = {}

                self._log_interaction(
                    round_num, "act", f"Calling {tool_name}({arguments})"
                )

                if verbose:
                    self._display_tool_call(tool_name, arguments)

                # Add assistant message (with tool call) to history
                self.messages.append(message)

                # Execute tool
                tool_result = self._execute_tool(tool_name, arguments)

                # STEP 3: OBSERVE - Feed result back to LLM
                self._log_interaction(
                    round_num,
                    "observe",
                    f"{tool_name} returned {len(tool_result.get('results', []))} results",
                )

                if verbose:
                    self._display_result(tool_result, tool_name)

                # Add tool result to conversation
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(
                            tool_result, indent=2, ensure_ascii=False
                        ),
                    }
                )

                # Loop continues - LLM will see the result and decide next action

            else:
                # No tool call - LLM provided final answer
                final_answer = (
                    message.content or "Sorry, I couldn't generate a response."
                )

                self._log_interaction(round_num, "final", final_answer[:200])

                # Add assistant response to history
                self.messages.append({"role": "assistant", "content": final_answer})

                elapsed = time.time() - start_time

                if verbose:
                    console.print(
                        Panel(
                            Markdown(final_answer),
                            title=f"🤖 Agent Response (Round {round_num}, {elapsed:.1f}s)",
                            border_style="yellow",
                            padding=(1, 2),
                        )
                    )

                logger.info(f"✅ Completed in {round_num} rounds, {elapsed:.2f}s")

                # Extract and save memories from conversation
                self._extract_and_remember(user_message, final_answer)

                # Update last seen
                self.memory.update_last_seen()
                self.memory.increment_messages()

                return final_answer

        # Max rounds reached
        warning = "⚠️ Maximum rounds reached. Please rephrase your question."
        logger.warning(warning)
        return warning

    def reset_conversation(self):
        """Clear conversation history (keep system prompt)"""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.interaction_log = []
        logger.info("🗑️ Conversation reset")

    def get_stats(self) -> Dict:
        """Return session statistics"""
        return {
            "total_interactions": len(self.interaction_log),
            "model": self.model,
            "conversation_length": len(self.messages),
            "available_tools": [t["function"]["name"] for t in self.tools],
        }

    def _extract_and_remember(self, user_msg: str, assistant_msg: str):
        """Extract and save memories from conversation."""
        try:
            memories = self.memory_extractor.extract_from_conversation(self.messages)

            for mem in memories:
                if mem.get("confidence", 0) > 0.5:
                    self.memory.remember(
                        key=mem["key"],
                        value=mem["value"],
                        memory_type=mem.get("type", "fact"),
                        source="auto_extracted",
                        confidence=mem.get("confidence", 1.0),
                        reason=mem.get("reason", ""),
                    )
                    logger.info(f"Auto-remembered: {mem['key']} = {mem['value']}")
        except Exception as e:
            logger.debug(f"Memory extraction skipped: {e}")

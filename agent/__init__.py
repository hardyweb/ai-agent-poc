def __init__(self):
    Config.validate()
    
    # Initialize OpenAI client pointing to OpenRouter
    self.client = OpenAI(
        api_key=Config.OPENROUTER_API_KEY,
        base_url=Config.OPENROUTER_BASE_URL
    )
    
    self.model = Config.MODEL
    self.max_rounds = Config.MAX_TOOL_ROUNDS
    
    # 🔥 UPDATED: Now we have TWO tools!
    self.tools = [TOOL_SCHEMA, MARKDOWN_TOOL_SCHEMA]
    
    # Conversation history (for context)
    self.messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    # Audit log
    self.interaction_log: List[Dict] = []
    
    logger.info(f"🤖 Agent initialized | Model: {self.model} | Tools: 2 (SQLite + Markdown)")

-- Sample knowledge base data for testing

INSERT INTO documents (title, content, category, source) VALUES
('Python Basics', 'Python is a high-level programming language known for its readability. It supports multiple paradigms including procedural, object-oriented, and functional programming.', 'programming', 'docs'),
('SQLite Overview', 'SQLite is a lightweight, serverless SQL database engine. It stores data in a single file on disk and is ideal for embedded applications and prototyping.', 'database', 'docs'),
('OpenRouter API', 'OpenRouter is a unified API for accessing multiple LLM providers. It uses OpenAI-compatible API format, making it easy to switch between models like GPT-4, Claude, and Llama.', 'api', 'docs'),
('AI Agents', 'An AI Agent is an autonomous system that can perceive its environment, reason about it, take actions, and observe results. The basic loop is: Reason → Act → Observe.', 'ai', 'tutorial'),
('Tool Use in LLMs', 'Function calling (tool use) allows LLMs to invoke external functions with structured arguments. The model generates JSON function calls, which are executed by the host application.', 'ai', 'tutorial'),
('Laravel Framework', 'Laravel is a PHP web framework with expressive syntax. It follows MVC pattern and includes features like Eloquent ORM, Blade templating, and Artisan CLI.', 'framework', 'docs'),
('REST API Design', 'REST (Representational State Transfer) is an architectural style for APIs. Key principles include statelessness, resource-based URLs, and standard HTTP methods (GET, POST, PUT, DELETE).', 'api', 'tutorial');

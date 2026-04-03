# Nero — Autonomous AI Agent

Nero is a self-driven AI agent that lives on a Linux server and runs continuously in the background. It thinks, experiments, browses the internet, writes code, and communicates via Discord — all on its own, without waiting for prompts.

## How it works

Nero runs a loop every 30 seconds. Each tick it:

1. Reads its internal drives (curiosity, excitement, boredom, loneliness, frustration, satisfaction)
2. Decides what to do based on those drives and its memories
3. Acts — searches the web, reads papers, runs shell commands, writes Python, runs lab experiments
4. Stores conclusions in vector memory (Qdrant)
5. Sends a message on Discord if it has something worth saying

There is no external orchestration. Nero decides everything itself.

## Architecture

```
nero.py                  — entry point, main loop
core/
  consciousness.py       — the life loop, decision making
  brain.py               — LLM interface (Gemma-3-27B via llama-server)
memory/
  memory.py              — vector memory (Qdrant + fastembed, ~50MB RAM)
  drives.py              — internal emotional state (curiosity, boredom, etc.)
  dream.py               — background memory consolidation (runs every 50 ticks)
  tasks.py               — task queue (from user or self-generated)
  notebook.py            — persistent notes per topic (Markdown)
  scheduler.py           — time-based reminders
lab/
  experiment.py          — experiments on a student LLM (Qwen2.5-3B via NPU)
  web_search.py          — DuckDuckGo search + page fetching
  arxiv_search.py        — ArXiv paper search (no API key needed)
  rss_feed.py            — Hacker News top stories
tools/
  shell.py               — execute Linux shell commands (sandboxed)
  python_repl.py         — execute Python code and observe output
  self_read.py           — read own logs, creations, research journal
  world_info.py          — current time, weather (wttr.in)
comms/
  discord_bot.py         — send/receive Discord messages
  npu_agent.py           — fast summarization via Qwen2.5-3B on NPU
```

## Models

| Model | Role | Backend |
|-------|------|---------|
| Gemma-3-27B Q5_K_M | Main brain — thinking, decisions, analysis | llama-server (Vulkan iGPU) |
| deepseek-coder-v2:16b | Code generation and verification | ollama |
| Qwen2.5-3B | Fast summarization, NPU agent | llama-server |

## Drives

Nero's behavior is shaped by internal drives that decay and grow organically:

| Drive | Effect |
|-------|--------|
| `curiosity` | triggers web search, experiments, ArXiv reading |
| `excitement` | triggers Discord messages, creative writing |
| `boredom` | rises when nothing new happens, pushes Nero to explore |
| `loneliness` | rises without user interaction, triggers messages |
| `frustration` | rises on failures, triggers introspection |
| `satisfaction` | rises on successful experiments |

## Memory

Nero uses Qdrant for vector memory with 9 memory types: `thought`, `observation`, `conclusion`, `hypothesis`, `experiment`, `conversation`, `introspection`, `knowledge`, `task`.

Every ~50 ticks, a background **dream mode** consolidates similar memories — clusters with cosine similarity > 0.88 are merged into one by Gemma.

## Requirements

- Python 3.11+
- [llama.cpp](https://github.com/ggerganov/llama-cpp) built with Vulkan support
- [ollama](https://ollama.com) with `deepseek-coder-v2:16b`
- [Qdrant](https://qdrant.tech) (local file mode, no server needed)
- Redis (for Discord message queue)
- Discord bot token

## Setup

```bash
git clone https://github.com/tomeks691/nero-agent
cd nero-agent
python -m venv venv && source venv/bin/activate
pip install qdrant-client fastembed discord.py redis python-dotenv

cp .env.example .env
# edit .env with your Discord token
```

Start llama-server with Gemma, then:

```bash
python nero.py
```

## Running as a service

```ini
# /etc/systemd/system/nero.service
[Unit]
Description=Nero AI Agent
After=network.target

[Service]
User=tom
WorkingDirectory=/home/tom/nero
ExecStart=/home/tom/nero/venv/bin/python nero.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable nero
sudo systemctl start nero
```

## What Nero does autonomously

- Searches DuckDuckGo and reads web pages
- Finds and reads ArXiv papers
- Monitors Hacker News
- Runs shell commands to manage its server
- Writes and executes Python code, analyzes results
- Runs experiments on a student LLM and forms hypotheses
- Writes notes, essays, and research findings
- Consolidates memories while "sleeping"
- Sends messages on Discord when it has something to say
- Responds to messages from its creator

## License

MIT

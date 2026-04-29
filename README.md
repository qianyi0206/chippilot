# ChipPilot - EDA/CAD AI Agent CLI

An AI-powered CLI agent for chip design EDA/CAD workflows. Built as a modular, extensible agent system that understands EDA tools, LSF job management, Git workflows, and more.

## Architecture

ChipPilot is built on a 12-mechanism agent harness (inspired by [learn-claude-code](https://github.com/anthropics/learn-claude-code)):

| # | Mechanism | Module | Description |
|---|-----------|--------|-------------|
| s01 | Agent Loop | `core/agent_loop.py` | LLM call → tool execution → result feedback |
| s02 | Tool Registry | `core/tool_registry.py` | Pluggable tool registration + dispatch |
| s03 | Todo Manager | `core/todos.py` | In-session task tracking with nag reminders |
| s04 | Subagent | `core/subagent.py` | Isolated child agents for exploration |
| s05 | Skill Loader | `core/skills.py` | Two-layer on-demand skill injection |
| s06 | Compression | `core/compression.py` | 3-layer context compression pipeline |
| s07 | Task System | `core/tasks.py` | Persistent file-based task board |
| s08 | Background | `core/background.py` | Threaded async execution + notification |
| s09 | Messaging | `core/messaging.py` | JSONL inbox inter-agent communication |
| s10 | Protocols | `core/protocols.py` | Shutdown + plan approval handshakes |
| s11 | Teams | `core/teams.py` | Autonomous teammates with auto-claim |
| s12 | Worktrees | `core/worktrees.py` | Git worktree isolation + EventBus |

## Domain Tools (35+ tools)

### Real execution
- **Git** (9 tools): status, log, diff, branch, commit, tag, PR, hotfix, subtree sync

### Mock simulation (demonstrates integration architecture)
- **LSF** (8 tools): bsub, bjobs, bqueues, bhist, bkill, SSUSP/USUSP diagnosis, resource planning
- **Jira** (5 tools): create, search, get, transition, comment
- **EDA** (6 tools): setws, module load/list, tool version, run Helium, check license
- **Storage** (3 tools): quota, disk usage, snapshot check
- **Monitoring** (3 tools): job monitor, host status, Grafana
- **Release** (3 tools): CSR flow, verilog line count, IP version management

## Knowledge System

68 domain documents (Chinese) covering EDA, LSF, Git, storage, monitoring, scripting, and workflows. Two-layer injection:
- **Layer 1** (system prompt): Category summaries (~200 tokens)
- **Layer 2** (on-demand): Full document loaded via `load_knowledge` tool

## Quick Start

```bash
# 1. Clone
git clone <repo-url>
cd chippilot

# 2. Install
pip install -e .

# 3. Configure
cp .env.example .env
# Edit .env with your API key

# 4. Run
chippilot
# or: python -m chippilot
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/compact` | Compress context |
| `/tasks` | Task board |
| `/team` | Teammate status |
| `/inbox` | Read messages |
| `/jobs` | LSF job status |
| `/queues` | Queue utilization |
| `/storage` | Storage quotas |
| `/tools` | EDA tool versions |
| `/jira` | Recent Jira issues |
| `/knowledge` | Knowledge base directory |

## Demo Scenarios

```
# 1. Git workflow
> 查看当前 git 状态

# 2. LSF job submission
> 提交一个 VCS 仿真任务到 short 队列

# 3. SSUSP diagnosis
> 有个仿真 job 被 SSUSP 了，帮我排查

# 4. Multi-agent collaboration
> 创建一个代码审查任务，然后 spawn 一个 teammate 来做
```

## Project Structure

```
chippilot/
├── chippilot/              # Main Python package
│   ├── main.py             # Entry point
│   ├── cli.py              # REPL + slash commands
│   ├── config.py           # Configuration center
│   ├── core/               # 12 harness mechanisms
│   ├── tools/              # 35+ tool implementations
│   ├── knowledge/          # Document indexer + loader
│   └── prompts/            # System prompt assembly
├── skills/                 # 7 SKILL.md operation guides
├── cad/                    # 68 domain knowledge documents
├── mock_data/              # Mock fixture data
├── tests/                  # Test suite
└── docs/                   # Architecture + demo docs
```

## Tech Stack

- Python 3.11+
- Anthropic Claude API (pre-wired for multi-provider)
- Rich (terminal rendering)
- prompt_toolkit (REPL)

## License

MIT

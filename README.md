# A700cli - Enhanced Agent700 CLI

A sophisticated command-line interface for interacting with Agent700 agents with rich visual output, enhanced MCP support, session management, conversation history, and comprehensive workflow integration features.

---

## 🚀 Quick Start

Get your first message sent in under a minute:

### Prerequisites
- Python 3.8 or higher (`python3 --version` to check)
- pip package manager

### 3 Steps to Get Started

```bash
# 1. Install the CLI
pip install -e .

# 2. Start interactive setup (you'll be prompted for email, password, and agent UUID)
a700cli --interactive

# 3. Send a message!
a700cli "Hello, how can you help me today?"
```

**Don't know your Agent UUID?** Run `a700cli --list-agents` to see all available agents and copy the UUID.

You don't need to configure an agent in advance; the CLI will prompt you to choose one when needed (use `--list-agents` to discover agents).

---

## ✨ Key Features

### 🎨 Rich Visual Output
- Beautiful colored console output with progress indicators
- Markdown rendering in terminal
- Formatted tables for structured data
- Visual MCP tool execution feedback
- Citation display with source information
- Enhanced error formatting with troubleshooting tips

### 🔧 Enhanced MCP Integration
- Robust MCP tool result parsing with fallback strategies
- Better error handling and reporting
- Visual feedback during tool execution
- Support for complex MCP result structures
- Comprehensive MCP debugging with verbose logging

### 💾 Session Management
- Persistent session storage with automatic token refresh
- Conversation history management with JSON-based storage
- Enhanced device fingerprinting for security
- Automatic session recovery and validation
- Pickle-based session persistence for reliability

### 🚀 Workflow Integration
- Multiple output formats (rich, JSON, plain text)
- Proper exit codes for workflow automation
- Quiet mode for minimal output
- File I/O support for batch processing
- Stdin/stdout integration for piping
- Configurable timeouts and retry logic
- Test pattern execution for systematic testing

### 🛡️ Enhanced Reliability
- Better WebSocket connection handling with automatic fallback
- Comprehensive error messages with troubleshooting tips
- Enhanced device fingerprinting for security
- Robust authentication with detailed feedback
- Graceful error recovery and fallback mechanisms

## 🚀 Installation

### Option 1: Install as Package (Recommended)

```bash
# Install the package
pip install -e .

# Or install from source
pip install -r requirements.txt
pip install -e .
```

After installation, use the `a700cli` command:

```bash
# Interactive setup
a700cli --interactive

# Send a message
a700cli "Your message here"
```

### Option 2: Run Directly from Source

```bash
# Install dependencies
pip install -r requirements.txt

# Run the module
python -m a700cli --interactive
# or
python -m a700cli "Your message here"
```

### Configuration

```bash
# Option A: Interactive setup (recommended)
a700cli --interactive
   
# Option B: Manual .env configuration
cp .env.example .env
# Edit .env with your credentials
```

## 📁 Local Development Files

The CLI stores local state under your home directory, not in the repo:

- **`~/.agent700/conversations/default.json`** - Stores conversation history and context
- **`~/.agent700/session.dat`** - Contains session data and authentication tokens  
- **`.env`** - Environment variables for authentication (project-local if you create it)

These files:
- ✅ **Should be ignored by git**
- ✅ **Contain sensitive data** (authentication tokens, session info)
- ✅ **Are user-specific** (different for each developer)
- ✅ **Are automatically generated** when using the CLI
- ✅ **Should not be committed** to the repository

**Note**: Legacy repo-local state files are still read if present, but new writes go to `~/.agent700/`.

## 📋 Configuration

### Automatic Configuration (Recommended)

The CLI will automatically prompt for missing credentials and agent selection:

```bash
a700cli --interactive
```

The tool will:
1. **Prompt for login credentials** if not found in `.env`
2. **Authenticate with Agent700** and show your account info
3. **Prompt for agent UUID** if not found in `.env` (use `--list-agents` to discover agents)
4. **Save configuration** to `.env` file for future use

**Agent selection:** You don't need to define an agent up front. When `AGENT_UUID` is missing, the CLI prompts you to choose one; use `--list-agents` to find IDs. To switch agents later, run the CLI again and enter a different UUID when prompted (the chosen agent is saved to `.env`).

### Interactive Setup Features

- **🔐 Secure Login**: Password input is hidden for security
- **🤖 Agent UUID Prompt**: Direct UUID entry with format validation
- **📋 Agent Discovery**: Use `--list-agents` to find available agents
- **💾 Configuration Saving**: Automatically saves credentials to `.env` file
- **🔄 Session Management**: Maintains authentication across conversations

### Manual Configuration

Alternatively, create a `.env` file with your Agent700 credentials:

```env
EMAIL=your-email@company.com
PASSWORD=your_secure_password
AGENT_UUID=your-agent-uuid-here
API_BASE_URL=https://api.agent700.ai  # Optional, defaults to production
```

## 💬 Usage

The Agent700 CLI supports two primary usage modes:

### 🔄 Interactive Mode
For back-and-forth conversations with persistent context:
```bash
a700cli --interactive
```

### ⚡ Non-Interactive Mode  
For single commands, automation, and workflow integration:
```bash
a700cli "Your message here"
```

## 🆕 Enhanced Features

### 📁 File I/O Support
```bash
# Read message from file
a700cli --input-file prompt.txt

# Read from stdin
echo "Your message" | a700cli

# Write response to file
a700cli "Generate report" --output-file report.txt
```

### 🔇 Quiet Mode for Scripting
```bash
# Minimal output for automation
a700cli "Quick query" --quiet

# Perfect for piping
result=$(a700cli "Process data" --quiet)
```

### 🤖 Agent Discovery
```bash
# List available agents
a700cli --list-agents

# Search for agents
a700cli --list-agents --search "code"

# Then use the UUID when prompted
a700cli --interactive
```

### 💬 Enhanced Interactive Commands
- `/exit`, `/quit`, `/q` - Exit conversation
- `/clear` - Clear conversation history
- `/context` - Show conversation context
- `/help` - Show available commands

## 🚀 Non-Interactive Mode Usage

### Basic Single Message
```bash
a700cli "Your message here"
```

### File Input/Output
```bash
# Read from file
a700cli --input-file prompt.txt

# Write to file
a700cli "Generate report" --output-file report.txt

# Read from stdin
echo "Your message" | a700cli
```

### Quiet Mode for Automation
```bash
# Minimal output for scripts
a700cli "Quick query" --quiet

# Perfect for piping
result=$(a700cli "Process data" --quiet)
```

## 💬 Interactive Mode Usage

### Interactive Conversation Mode
```bash
a700cli --interactive
```

## 🎯 Non-Interactive Mode Use Cases

### Automation & Scripting
Perfect for automated workflows, CI/CD pipelines, and batch processing:

```bash
# Automated report generation
a700cli "Generate weekly sales report" --output-file report.txt

# Batch data processing
a700cli "Process customer feedback data" --quiet

# Status checks in monitoring systems
a700cli "Check system health" --quiet
```

### API Integration
Ideal for integrating with other systems and applications:

```bash
# REST API integration
response=$(a700cli "Analyze user behavior" --quiet)
echo "$response"

# Webhook processing
a700cli "Process webhook data: $payload" --output-file result.txt

# Microservice communication
a700cli "Validate transaction data" --quiet
```

### Data Processing Workflows
Excellent for data analysis and processing pipelines:

```bash
# Data analysis with MCP tools
a700cli "Analyze dataset: $file_path" --input-file data.txt

# Report generation
a700cli "Generate insights from Q4 data" --output-file insights.txt

# Data validation
a700cli "Validate data integrity" --quiet
```

### System Administration
Great for system monitoring and administrative tasks:

```bash
# System diagnostics
a700cli "Check server performance metrics" --quiet

# Log analysis
a700cli "Analyze error logs for patterns" --input-file logs.txt

# Automated alerts
a700cli "Generate system status report" --output-file status.txt --quiet
```

### Development & Testing
Perfect for development workflows and testing:

```bash
# Code analysis
a700cli "Review code quality for: $file" --input-file code.py --output-file analysis.txt

# Test generation
a700cli "Generate unit tests for: $function" --output-file tests.py

# Documentation generation
a700cli "Create API documentation" --output-file docs.md
```

### Business Process Automation
Ideal for business workflow automation:

```bash
# Customer service automation
a700cli "Process customer inquiry: $ticket" --output-file response.txt

# Content generation
a700cli "Generate marketing content for: $campaign" --output-file content.txt

# Compliance checking
a700cli "Check compliance requirements" --quiet
```

## 🔧 Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `message` | Message to send (positional argument) | None |
| `--interactive, -i` | Start interactive conversation mode | Single message mode |
| `--input-file, -f` | Read message from file (use `-` for stdin) | None |
| `--output-file, -o` | Write response to file | None |
| `--quiet, -q` | Minimal output for workflows | Verbose output |
| `--help-auth` | Show authentication environment variables | None |
| `--list-agents, -l` | List available agents with pagination and search | None |
| `--page` | Page number for agent list (used with --list-agents) | 1 |
| `--limit` | Results per page (max: 100, used with --list-agents) | 20 |
| `--search` | Filter agents by name (case-insensitive, used with --list-agents) | None |
| `--format` | Output format for --list-agents (table or json) | table |
| `--streaming` | Use WebSocket streaming mode | HTTP mode |

## 📊 Output Formats

### Rich Output (Default)
Beautiful console output with:
- Colored panels and sections
- Markdown rendering
- Progress indicators
- Citation cards
- MCP tool result formatting

### Plain Text Output
Use `--quiet` when you want the assistant response only, with no status chatter. This is the right mode for shell scripts and piping.

### Structured Command Output
Some administrative commands support `--format json`, notably agent listing. Chat responses do not currently expose a JSON response mode.

Example:
```bash
a700cli --list-agents --format json
```

### File Output
Use `--output-file` when you want to capture the raw assistant response for later processing.
```
a700cli "Generate release notes" --output-file release_notes.txt
```

## 💬 Interactive Conversation Mode

### Features
- **Back-and-forth messaging** with persistent conversation context
- **Graceful Ctrl+C exit** with proper signal handling
- **Special commands** for conversation management
- **Session persistence** across messages
- **Rich console output** with progress indicators

### Interactive Commands
| Command | Description |
|---------|-------------|
| `/exit`, `/quit`, `/q` | Exit conversation gracefully |
| `/clear` | Clear conversation history |
| `/context` | Show conversation context |
| `/help` | Show available commands |

### Usage Examples
```bash
# Start interactive conversation
a700cli --interactive

# Interactive with streaming
a700cli --interactive --streaming
```

### Interactive Mode Features
- **Conversation History**: Maintains context across all messages
- **Session Management**: Automatic token refresh and validation
- **Error Recovery**: Graceful handling of connection issues
- **Rich Output**: Beautiful formatting with progress indicators
- **MCP Integration**: Full MCP tool support in interactive mode

## 🔐 Interactive Setup Process

### First-Time Setup
When you run the CLI without a `.env` file or when `AGENT_UUID` is missing, it will guide you through setup:

```bash
a700cli --interactive
```

**Step 1: Authentication**
```
🔐 Agent700 Authentication Setup
Some configuration is missing. Let's set it up interactively.

📧 Email: your-email@company.com
🔒 Password: [hidden input]
```

**Step 2: Agent UUID Entry**
```
🔍 No agent UUID found. Enter an agent UUID to continue.
💡 Tip: Use 'a700cli --list-agents' to see available agents.
? Enter Agent UUID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
🔍 Fetching agent configuration...
✓ Agent: Code Reviewer
✅ Configuration saved to .env file
```

**Note:** If you enter an invalid UUID format, you'll see:
```
❌ Invalid UUID format. Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### Agent Discovery
You can run without any pre-set agent; when `AGENT_UUID` is missing, the CLI prompts you to enter one. To switch agents, run the CLI again and enter a different UUID when prompted.

To find available agents, use the `--list-agents` command:

```bash
# List all agents (paginated)
a700cli --list-agents

# Search for agents by name
a700cli --list-agents --search "code"

# Get JSON output for scripting
a700cli --list-agents --format json

# Navigate pages
a700cli --list-agents --page 2 --limit 50
```

The CLI will:
- **Prompt for UUID directly** when `AGENT_UUID` is missing (no auto-fetching)
- **Validate UUID format** before making API calls
- **Show helpful error messages** if agent is not found
- **Provide a separate discovery command** for finding agents

## 🔗 WebSocket vs HTTP Modes

### WebSocket Streaming Mode (Recommended)
- **Real-time response streaming**
- **Progress indicators**  
- **Live MCP tool execution feedback**
- **Automatic fallback to HTTP on failure**

```bash
a700cli "Stream this response" --streaming
```

### HTTP Mode
- **Simple request-response**
- **Better for automation**
- **More reliable for network issues**

```bash
a700cli "Process this" # HTTP mode (default)
```

## 🛠️ MCP Tool Support

The enhanced script provides MCP integration during normal chat and streaming flows.

### Features
- **Automatic MCP server detection** from agent configuration
- **Real-time tool execution feedback** with progress indicators
- **Enhanced result parsing** with multiple fallback strategies
- **Visual tool result formatting** in rich output mode
- **Error handling** for malformed tool responses

### MCP Tool Execution Flow
1. **Agent Configuration**: Fetches MCP settings from agent
2. **Tool Detection**: Shows which MCP tools are available
3. **Execution Feedback**: Visual indicators during tool runs
4. **Result Processing**: Structured display of tool outputs
5. **Error Recovery**: Graceful handling of tool failures

### MCP Usage
```bash
# Use MCP-capable agents in normal chat
a700cli "Use MCP tools"

# Or stream the response
a700cli "Search for information" --streaming
```

## 🔄 Workflow Integration

Perfect for automated workflows and CI/CD pipelines using non-interactive mode:

### Exit Codes
- **0**: Success
- **1**: Error (authentication, network, agent error)

### Workflow Examples

#### Basic Automation Script
```bash
#!/bin/bash
# Workflow script example

response=$(a700cli "Analyze deployment" --quiet)
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "Agent response successful"
    echo "$response"
else
    echo "Agent request failed"
    exit 1
fi
```

#### CI/CD Pipeline Integration
```bash
#!/bin/bash
# GitHub Actions / Jenkins example

# Generate deployment report
a700cli "Generate deployment report for $BRANCH" \
    --output-file deployment_report.txt

# Check exit code
if [ $? -eq 0 ]; then
    echo "✅ Deployment report generated successfully"
    cat deployment_report.txt
else
    echo "❌ Failed to generate deployment report"
    exit 1
fi
```

#### Monitoring & Alerting
```bash
#!/bin/bash
# System monitoring example

# Check system health
health_status=$(a700cli "Check system health metrics" --quiet)

if [ $? -eq 0 ]; then
    echo "System Status: $health_status"
else
    # Send alert
    a700cli "Generate system alert notification" \
        --output-file system_alert.txt
    mail -s "System Alert" admin@company.com < system_alert.txt
fi
```

#### Data Processing Pipeline
```bash
#!/bin/bash
# Data processing workflow

# Process incoming data
a700cli "Process data file: $INPUT_FILE" \
    --output-file processed_data.txt

# Validate results
validation_result=$(a700cli "Validate processed data" --quiet)

if [ $? -eq 0 ]; then
    echo "✅ Data processing completed: $validation_result"
    mv processed_data.txt /output/
else
    echo "❌ Data validation failed: $validation_result"
    exit 1
fi
```

### Docker Integration
```dockerfile
FROM python:3.9-slim

COPY a700cli/ requirements.txt pyproject.toml /app/
WORKDIR /app

RUN pip install -r requirements.txt

# Copy environment file
COPY .env /app/

ENTRYPOINT ["a700cli"]
```

## 🎯 Use Cases

### Development & Testing
```bash
# Test agent responses with rich output
a700cli "Test query" --streaming

# Exercise an MCP-capable agent
a700cli "Use search tool"
```

### Automation & CI/CD
```bash
# Automated report generation
a700cli "Generate weekly report" --output-file weekly_report.txt

# Quiet mode for scripts
a700cli "Process data batch" --quiet
```

### Data Analysis Workflows
```bash
# Process with MCP tools and stream the response
a700cli "Analyze this dataset" --streaming
```

## 🐛 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **Authentication failed** | Check EMAIL and PASSWORD in your `.env` file. Reset your password at Agent700 if needed. |
| **Invalid UUID format** | UUID must be `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`. Run `a700cli --list-agents` to find valid UUIDs. |
| **Agent not found (404)** | Run `a700cli --list-agents` and copy the exact UUID from the list. |
| **No message provided** | Use `a700cli "your message"` or `a700cli --interactive` for chat mode. |
| **Connection / WebSocket errors** | Try without `--streaming` (uses HTTP mode). Check your network/firewall. |
| **Import or dependency errors** | Run `pip install -r requirements.txt` from the project directory. |

### Debug Commands

```bash
# Use HTTP mode if WebSocket fails
a700cli "test"  # HTTP is default, no --streaming flag

# Check streaming behavior explicitly
a700cli "test" --streaming

# See the authoritative CLI surface
a700cli --help
```

### Error Messages
The CLI provides detailed error messages with:
- **Root cause identification**
- **Troubleshooting suggestions**
- **Configuration guidance**
- **Network diagnostics**

---

## 📞 Support

**Need help?**

- Email: hello@agent700.ai
- Documentation: https://agent700.ai/docs
- Run `a700cli --help` for all available options

## 💾 Session Management

### Persistent Sessions
- **Automatic session storage** in `~/.agent700/session.dat`
- **Token refresh** with automatic retry logic
- **Session validation** before each request
- **Graceful session recovery** on token expiration

### Conversation History
- **Chat history storage** in `~/.agent700/conversations/default.json`
- **Conversation context** maintained across sessions
- **Automatic conversation management** with cleanup
- **Rich conversation display** with timestamps and formatting

### Session Features
```bash
# Sessions are automatically managed
a700cli "Continue our conversation"  # Uses existing session

# Force a fresh local session
rm ~/.agent700/session.dat ~/.agent700/conversations/default.json
a700cli "Start fresh conversation"
```

## 🔒 Security Features

### Enhanced Authentication
- **Device fingerprinting** for improved security
- **Token validation** with detailed error reporting
- **Session management** with automatic retry logic
- **Enhanced device fingerprinting** with system information

### Privacy Protection
- **Credential protection** in logs
- **Secure token storage** recommendations
- **Network security** best practices
- **Session encryption** for sensitive data

## 🚀 Performance Features

### Optimizations
- **Connection pooling** for WebSocket connections
- **Automatic fallback** from streaming to HTTP
- **Timeout management** for different operation types
- **Memory-efficient** response processing

### Monitoring
- **Real-time progress tracking**
- **Connection status monitoring**
- **Resource usage optimization**

## 📝 Examples

### 🔄 Interactive Mode Examples

#### Interactive Conversation
```bash
# Start interactive chat
a700cli --interactive
```

### ⚡ Non-Interactive Mode Examples

#### Basic Single Message
```bash
a700cli "Hello, how can you help me today?"
```

#### File Input/Output
```bash
# Read from file
a700cli --input-file prompt.txt

# Write to file
a700cli "Generate report" --output-file report.txt

# Read from stdin
echo "Your message" | a700cli
```

#### Quiet Automation
```bash
result=$(a700cli "Quick status check" --quiet)
echo "Status: $result"
```

#### Batch Processing
```bash
# Process multiple items
for item in $ITEMS; do
    a700cli "Process item: $item" --quiet
done
```

#### Content Generation
```bash
# Generate documentation
a700cli "Create API documentation for: $endpoint" \
    --output-file docs.md
```

## 🔄 Migration from Previous Versions

### Single Entry Point
The CLI now uses a single official entry point: `a700cli` (installed via package) or `python -m a700cli` (run from source).

### Key Features
1. **Enhanced CLI Interface**: Proper argparse-based command-line parsing
2. **File I/O Support**: Read from files, write to files, stdin/stdout integration
3. **WebSocket Streaming**: Real-time streaming with `--streaming` flag
4. **Interactive UUID Prompt**: Direct UUID entry with validation (use `--list-agents` for discovery)
5. **Session Management**: Persistent sessions with automatic token refresh
6. **Conversation History**: JSON-based conversation tracking
7. **Quiet Mode**: Perfect for automation and scripting (`--quiet`)
8. **Rich Console Support**: Beautiful terminal output with fallback
9. **Agent Discovery**: Paginated agent listing with search (`--list-agents`)

### Migration Steps
1. Install the package: `pip install -e .` (or `pip install -r requirements.txt` for dependencies only)
2. Use the `a700cli` command instead of `python A700cli.py` or `python run_agent.py`
3. All features are now available in the single entry point
4. Use `--streaming` flag for WebSocket mode (previously default in `run_agent.py`)
5. Test with your existing .env configuration

## 🤝 Contributing

### Development Setup
```bash
git clone <repository>
cd agent700-enhanced-cli
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If available
```

### Testing
```bash
# Run basic tests
a700cli "test"

# Test different modes
a700cli "test" --quiet
a700cli "test" --input-file test.txt
a700cli "test" --output-file result.txt

# Test interactive mode
a700cli --interactive
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Resources

- [Agent700 Documentation](https://agent700.ai/docs)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io)
- [Rich Python Library](https://rich.readthedocs.io)
- [WebSocket Documentation](https://python-socketio.readthedocs.io)

---

**Happy chatting with your enhanced Agent700 CLI!** 🚀

Need help? Email hello@agent700.ai

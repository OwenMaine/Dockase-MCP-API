# Dockase Legal Reasoning MCP Server

A Model Context Protocol (MCP) server that connects large language models (such as Anthropic Claude, Google Gemini, and Meta Llama) to the **Dockase Legal Intelligence Engine** for Nigerian and Commonwealth law.

By connecting this server to your local LLM client, the model gains the ability to run automated legal research, draft motions and briefs, perform senior-counsel-level contract risk analysis, validate citations, and manage legal cases using your Dockase CRM data.

---

## Architecture

```
┌─────────────────┐             ┌─────────────────────┐             ┌──────────────────────┐
│  LLM Agent App  │             │ Local MCP Connector │             │ Dockase Cloud API    │
│ (Claude/Gemini) ├────────────►│     (server.py)     ├────────────►│ (gateway.py / Django)│
│  [Client-side]  │  stdio      │    [Zero-dep Py]    │  HTTPS/REST │     [Secure Cloud]   │
└─────────────────┘ (JSON-RPC)  └─────────────────────┘             └──────────────────────┘
```

The Dockase MCP server is designed around a **Strict Client-Gateway Separation**:
1. **Local Bridge**: `server.py` is a lightweight, zero-dependency Python script that runs on your local machine. It reads JSON-RPC commands from your LLM agent via `stdin` and writes response payloads to `stdout`.
2. **Cloud Security**: The local bridge does not store databases, prompt weights, or core algorithms. Instead, it forwards requests securely to the cloud-hosted Dockase API Gateway over HTTPS using your developer API Key.

---

## Prerequisites

1. **Python 3.8+** installed on your system.
2. A **Dockase Developer Account** and API key.
   * To get your key, register an account at [Dockase Developer Portal](https://dockase.com/developer/docs/) and copy your token from the developer dashboard.

---

## Installation & Setup

### 1. Claude Desktop Setup

To connect Dockase tools to the Claude Desktop application, configure your local configuration file.

* **Windows Config Path**: `%APPDATA%\Claude\claude_desktop_config.json`
* **macOS Config Path**: `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the `dockase-litigation` server block under `mcpServers`:

```json
{
  "mcpServers": {
    "dockase-litigation": {
      "command": "python",
      "args": [
        "/absolute/path/to/your/cloned/repo/server.py"
      ],
      "env": {
        "DOCKASE_API_KEY": "dk_your_secret_api_key_here",
        "DOCKASE_GATEWAY_URL": "https://dockase.com"
      }
    }
  }
}
```

*Replace `/absolute/path/to/your/cloned/repo/server.py` with the actual file path on your system. Make sure to use forward slashes (`/`) even on Windows paths.*

---

## Exposed Legal Tools (20 Tools)

The local server exposes the following legal reasoning tools to your connected AI model:

### 1. Legal Research & Reasoning
* **`dockase_query`**: Run natural language legal research queries on Nigerian law principles.
* **`dockase_search_judgments`**: Perform semantic vector search (RAG) directly against the certified legal judgments compendium.
* **`dockase_similar_judgments`**: Fetch semantically related case precedents to a known legal judgment by ID.
* **`dockase_deep_research`**: Spin up a multi-step autonomous agent research pipeline compiling precedents for complex, multi-issue facts.

### 2. Document Drafting & Analysis
* **`dockase_draft`**: Draft agreements, NDAs, contracts of sale, or originating court briefs based on factual outlines.
* **`dockase_draft_multi`**: Draft structured document sets (e.g., Motion Packs containing Motion + Affidavit + Written Address).
* **`dockase_analyze_contract`**: Conduct a senior-counsel-level risk review of contract clauses (e.g., indemnity, governing law).
* **`dockase_validate_citations`**: Scan a brief or draft, validate court citations against database records, and identify/remove AI hallucinations.

### 3. CRM & Matter Management
* **`dockase_list_clients`**: Fetch a list of clients in your firm's CRM database.
* **`dockase_create_client`**: Add a new client profile (name, contact info) directly into the CRM.
* **`dockase_list_cases`**: Fetch active firm matters, cases, or litigation files.
* **`dockase_create_case`**: Open a new legal matter folder linked to a client ID.
* **`dockase_create_document`**: Save a drafted brief or document directly into a case folder.
* **`dockase_check_freshness`**: Scan documents in a case folder for stale timelines or upcoming filing deadlines.
* **`dockase_list_case_updates`**: Retrieve hearing logs and court adjournment records for a matter.
* **`dockase_log_case_update`**: Add a new court update, hearing transcript, and set next hearing timelines.
* **`dockase_summarize_case`**: Compile an executive summary of facts, pleadings, and status for a legal matter.
* **`dockase_draft_client_email`**: Draft a professional status update email to send to the client.
* **`dockase_tag_case`**: Suggest primary and secondary practice areas (e.g., Land Law, Family Law) from description keywords.
* **`dockase_chat`**: Conduct standard conversational sessions with Amicus, the Dockase legal assistant agent.

---

## Testing & Troubleshooting

To verify that the local server is operating correctly before integrating it into your LLM clients, run it directly in your terminal:

```bash
python server.py
```

It will wait for input. Paste the standard MCP initialization message to see if it responds with the list of tools:

```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}
```

### Log Streaming
Since standard output (`stdout`) is reserved for JSON-RPC messages, any warnings, errors, or info updates are sent to standard error (`stderr`). Check your LLM client's console logs or error outputs for stderr logs starting with `[INFO]` or `[ERROR]`.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

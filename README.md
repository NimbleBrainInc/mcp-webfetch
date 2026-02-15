# WebFetch MCP Server

[![mpak](https://img.shields.io/badge/mpak-registry-blue)](https://mpak.dev/packages/@nimblebraininc/webfetch?utm_source=github&utm_medium=readme&utm_campaign=mcp-webfetch)
[![NimbleBrain](https://img.shields.io/badge/NimbleBrain-nimblebrain.ai-purple)](https://nimblebrain.ai?utm_source=github&utm_medium=readme&utm_campaign=mcp-webfetch)
[![Discord](https://img.shields.io/badge/Discord-community-5865F2)](https://nimblebrain.ai/discord?utm_source=github&utm_medium=readme&utm_campaign=mcp-webfetch)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that fetches web pages, converts HTML to markdown, and uses Claude to answer questions about the content. Get AI-powered summaries and analysis of any web page from any MCP client.

**[View on mpak registry](https://mpak.dev/packages/@nimblebraininc/webfetch?utm_source=github&utm_medium=readme&utm_campaign=mcp-webfetch)** | **Built by [NimbleBrain](https://nimblebrain.ai?utm_source=github&utm_medium=readme&utm_campaign=mcp-webfetch)**

## Install

Install with [mpak](https://mpak.dev?utm_source=github&utm_medium=readme&utm_campaign=mcp-webfetch):

```bash
mpak install @nimblebraininc/webfetch
```

### Configuration

Get your API key from [Anthropic Console](https://console.anthropic.com/), then configure:

```bash
mpak config set @nimblebraininc/webfetch anthropic_api_key YOUR_API_KEY
```

### Claude Code

```bash
claude mcp add webfetch -- mpak run @nimblebraininc/webfetch
```

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "webfetch": {
      "command": "mpak",
      "args": ["run", "@nimblebraininc/webfetch"]
    }
  }
}
```

See the [mpak registry page](https://mpak.dev/packages/@nimblebraininc/webfetch?utm_source=github&utm_medium=readme&utm_campaign=mcp-webfetch) for full install options.

## Tools

### web_fetch

Fetch a web page and answer questions about its content. The page is fetched, converted to markdown, and sent to Claude Haiku for analysis.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | `string` | Yes | URL to fetch. HTTP URLs are auto-upgraded to HTTPS. |
| `prompt` | `string` | Yes | Question or instruction about the page content. |

**Example call:**

```json
{
  "name": "web_fetch",
  "arguments": {
    "url": "https://example.com",
    "prompt": "What is this page about? Summarize the main points."
  }
}
```

**Example response:**

```
This page is the IANA example domain, reserved for use in documentation
and examples. It contains a simple heading and a paragraph explaining
that the domain is established for illustrative purposes.
```

Features:
- Automatic HTTP to HTTPS upgrade
- HTML cleaned and converted to markdown (strips scripts, styles, nav, headers, footers)
- 15-minute in-memory cache for repeated fetches of the same URL
- Cross-host redirect detection (returns redirect URL for you to follow)
- Content truncation for very large pages

## Quick Start

### Local Development

```bash
git clone https://github.com/NimbleBrainInc/mcp-webfetch.git
cd mcp-webfetch

# Install dependencies
uv sync

# Set API key
export ANTHROPIC_API_KEY=your-key-here

# Run the server (stdio mode)
uv run python -m mcp_webfetch.server
```

The server supports HTTP transport with:
- Health check: `GET /health`
- MCP endpoint: `POST /mcp`

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run all checks (format, lint, typecheck, unit tests)
make check

# Run unit tests
make test

# Run with coverage
make test-cov
```

## About

WebFetch MCP Server is published on the [mpak registry](https://mpak.dev?utm_source=github&utm_medium=readme&utm_campaign=mcp-webfetch) and built by [NimbleBrain](https://nimblebrain.ai?utm_source=github&utm_medium=readme&utm_campaign=mcp-webfetch). mpak is an open registry for [Model Context Protocol](https://modelcontextprotocol.io) servers.

- [mpak registry](https://mpak.dev?utm_source=github&utm_medium=readme&utm_campaign=mcp-webfetch)
- [NimbleBrain](https://nimblebrain.ai?utm_source=github&utm_medium=readme&utm_campaign=mcp-webfetch)
- [MCP specification](https://modelcontextprotocol.io)
- [Discord community](https://nimblebrain.ai/discord?utm_source=github&utm_medium=readme&utm_campaign=mcp-webfetch)

## License

MIT

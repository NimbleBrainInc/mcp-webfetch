"""Unit tests for the WebFetch MCP server."""

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

from mcp_webfetch.server import mcp


@pytest.mark.asyncio
async def test_tools_list() -> None:
    """Test that tools are properly registered."""
    async with Client(mcp) as client:
        tools = await client.list_tools()

        assert len(tools) == 1
        tool_names = [tool.name for tool in tools]
        assert "web_fetch" in tool_names


@pytest.mark.asyncio
async def test_skill_resource_listed() -> None:
    """Test that the skill resource is registered."""
    async with Client(mcp) as client:
        resources = await client.list_resources()

        assert len(resources) >= 1
        uris = [str(r.uri) for r in resources]
        assert "skill://webfetch/usage" in uris


@pytest.mark.asyncio
async def test_skill_resource_readable() -> None:
    """Test that the skill resource returns content."""
    async with Client(mcp) as client:
        content = await client.read_resource("skill://webfetch/usage")

        text = content[0].content if hasattr(content[0], "content") else str(content[0])
        assert "WebFetch" in text
        assert "web_fetch" in text


@pytest.mark.asyncio
async def test_web_fetch_tool() -> None:
    """Test web_fetch tool returns a result."""
    with patch("mcp_webfetch.server.get_fetcher") as mock_get_fetcher:
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_and_summarize.return_value = "This is a test page about example topics."
        mock_get_fetcher.return_value = mock_fetcher

        async with Client(mcp) as client:
            result = await client.call_tool(
                "web_fetch",
                {"url": "https://example.com", "prompt": "What is this page about?"},
            )

        mock_fetcher.fetch_and_summarize.assert_called_once_with(
            url="https://example.com",
            prompt="What is this page about?",
        )
        assert result is not None


@pytest.mark.asyncio
async def test_web_fetch_with_http_url() -> None:
    """Test web_fetch tool accepts HTTP URLs."""
    with patch("mcp_webfetch.server.get_fetcher") as mock_get_fetcher:
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_and_summarize.return_value = "Summary of the page."
        mock_get_fetcher.return_value = mock_fetcher

        async with Client(mcp) as client:
            await client.call_tool(
                "web_fetch",
                {"url": "http://example.com", "prompt": "Summarize this page."},
            )

        mock_fetcher.fetch_and_summarize.assert_called_once_with(
            url="http://example.com",
            prompt="Summarize this page.",
        )

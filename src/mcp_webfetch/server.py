"""WebFetch MCP Server - FastMCP Implementation."""

import logging
import os
import sys
from importlib.resources import files

from dotenv import load_dotenv
from fastmcp import Context, FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .fetcher import FetchError, WebFetcher

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp_webfetch")

load_dotenv()

mcp = FastMCP(
    "WebFetch",
    instructions=(
        "Before using the web_fetch tool, read the skill://webfetch/usage resource "
        "for prompt writing guidance, URL handling, and caching behavior."
    ),
)

SKILL_CONTENT = files("mcp_webfetch").joinpath("SKILL.md").read_text()


@mcp.resource("skill://webfetch/usage")
def webfetch_skill() -> str:
    """How to effectively use WebFetch: prompt tips, URL handling, caching, limitations."""
    return SKILL_CONTENT


_fetcher: WebFetcher | None = None


def get_fetcher() -> WebFetcher:
    """Get or create the WebFetcher instance."""
    global _fetcher
    if _fetcher is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required. "
                "Get your API key from https://console.anthropic.com/"
            )
        _fetcher = WebFetcher(api_key=api_key)
    return _fetcher


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for monitoring."""
    return JSONResponse({"status": "healthy", "service": "mcp-webfetch"})


@mcp.tool()
async def web_fetch(
    url: str,
    prompt: str,
    ctx: Context | None = None,
) -> str:
    """Fetch a web page and answer questions about its content.

    Fetches the URL, converts HTML to markdown, and uses Claude to answer
    the prompt based on the page content.

    Args:
        url: The URL to fetch content from. HTTP URLs are auto-upgraded to HTTPS.
        prompt: Question or instruction about the page content.
        ctx: MCP context.

    Returns:
        AI-generated response about the page content.
    """
    fetcher = get_fetcher()

    if ctx:
        await ctx.info(f"Fetching {url[:80]}...")

    try:
        result = await fetcher.fetch_and_summarize(url=url, prompt=prompt)
    except FetchError as e:
        if ctx:
            await ctx.error(f"Fetch error: {e}")
        raise

    return result


# ASGI entrypoint (nimbletools-core container deployment)
app = mcp.http_app()

# Stdio entrypoint (mpak / Claude Desktop)
if __name__ == "__main__":
    logger.info("Running in stdio mode")
    mcp.run()

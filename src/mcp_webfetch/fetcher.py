"""Web fetcher: HTTP fetch, HTML-to-markdown conversion, caching, and LLM summarization."""

import logging
import re
import time
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientError
from anthropic import AsyncAnthropic
from markdownify import markdownify

logger = logging.getLogger("mcp_webfetch")

# Cache TTL in seconds (15 minutes)
CACHE_TTL = 15 * 60

# Max content length before truncation (fits Haiku context window)
MAX_CONTENT_CHARS = 180_000

# Tags to strip before markdown conversion
STRIP_TAGS_PATTERN = re.compile(
    r"<(script|style|nav|header|footer|noscript)[^>]*>.*?</\1>",
    re.DOTALL | re.IGNORECASE,
)


class FetchError(Exception):
    """Error during web fetching."""

    def __init__(self, message: str, url: str | None = None) -> None:
        self.url = url
        super().__init__(message)


class WebFetcher:
    """Fetches web pages, converts to markdown, and summarizes with Claude Haiku."""

    def __init__(self, api_key: str, timeout: float = 30.0) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self._session: aiohttp.ClientSession | None = None
        self._anthropic: AsyncAnthropic | None = None
        self._cache: dict[str, tuple[str, float]] = {}

    def _get_anthropic(self) -> AsyncAnthropic:
        if self._anthropic is None:
            self._anthropic = AsyncAnthropic(api_key=self.api_key)
        return self._anthropic

    async def _ensure_session(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "WebFetch-MCP/1.0 (compatible; bot)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate",
                },
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL: auto-upgrade http to https."""
        if url.startswith("http://"):
            url = "https://" + url[7:]
        elif not url.startswith("https://"):
            url = "https://" + url
        return url

    async def _fetch_html(self, url: str) -> str:
        """Fetch HTML from a URL. Returns redirect info for cross-host redirects."""
        await self._ensure_session()
        assert self._session is not None

        try:
            async with self._session.get(url, allow_redirects=True) as response:
                # Check for cross-host redirect
                final_url = str(response.url)
                original_host = urlparse(url).hostname
                final_host = urlparse(final_url).hostname
                if original_host != final_host:
                    raise FetchError(
                        f"Redirected to a different host: {final_url}. "
                        f"Please make a new request with this URL.",
                        url=final_url,
                    )

                if response.status >= 400:
                    raise FetchError(
                        f"HTTP {response.status} fetching {url}",
                        url=url,
                    )

                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    raise FetchError(
                        f"URL returned non-HTML content type: {content_type}",
                        url=url,
                    )

                return await response.text()
        except ClientError as e:
            raise FetchError(f"Network error fetching {url}: {e}", url=url) from e

    @staticmethod
    def html_to_markdown(html: str) -> str:
        """Convert HTML to markdown, stripping non-content elements."""
        # Strip script, style, nav, header, footer, noscript tags
        cleaned = STRIP_TAGS_PATTERN.sub("", html)
        # Convert to markdown with ATX-style headings
        md = markdownify(cleaned, heading_style="ATX", strip=["img"])
        # Clean up excessive whitespace
        md = re.sub(r"\n{3,}", "\n\n", md)
        return md.strip()

    def _get_cached(self, url: str) -> str | None:
        """Get cached markdown if available and not expired."""
        if url in self._cache:
            content, timestamp = self._cache[url]
            if time.time() - timestamp < CACHE_TTL:
                return content
            del self._cache[url]
        return None

    def _set_cache(self, url: str, content: str) -> None:
        """Cache markdown content with current timestamp."""
        self._cache[url] = (content, time.time())

    async def _summarize_with_llm(self, markdown: str, prompt: str) -> str:
        """Send markdown + prompt to Claude Haiku for summarization."""
        client = self._get_anthropic()

        # Truncate if content exceeds Haiku's context window
        if len(markdown) > MAX_CONTENT_CHARS:
            markdown = markdown[:MAX_CONTENT_CHARS] + "\n\n[Content truncated due to length]"

        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=(
                "You are a helpful assistant that answers questions about web page content. "
                "The user will provide a web page (converted to markdown) and a question or prompt. "
                "Answer based on the content provided. Be concise and direct."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Here is the web page content:\n\n---\n{markdown}\n---\n\n{prompt}"
                    ),
                }
            ],
        )

        return response.content[0].text  # type: ignore[union-attr]

    async def fetch_and_summarize(self, url: str, prompt: str) -> str:
        """Full pipeline: fetch URL, convert to markdown, summarize with LLM.

        Args:
            url: The URL to fetch.
            prompt: Question or instruction about the page content.

        Returns:
            LLM-generated response about the page content.
        """
        normalized = self.normalize_url(url)

        # Check cache for markdown
        markdown = self._get_cached(normalized)
        if markdown is None:
            logger.info("Fetching %s", normalized)
            html = await self._fetch_html(normalized)
            markdown = self.html_to_markdown(html)
            self._set_cache(normalized, markdown)
            logger.info("Cached markdown for %s (%d chars)", normalized, len(markdown))
        else:
            logger.info("Cache hit for %s", normalized)

        return await self._summarize_with_llm(markdown, prompt)

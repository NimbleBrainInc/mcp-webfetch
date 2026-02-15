"""Unit tests for the WebFetcher."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_webfetch.fetcher import CACHE_TTL, MAX_CONTENT_CHARS, WebFetcher


@pytest.fixture
def fetcher() -> WebFetcher:
    """Create a WebFetcher with a dummy API key."""
    return WebFetcher(api_key="test-key")


class TestNormalizeUrl:
    """Tests for URL normalization."""

    def test_http_upgraded_to_https(self) -> None:
        assert WebFetcher.normalize_url("http://example.com") == "https://example.com"

    def test_https_unchanged(self) -> None:
        assert WebFetcher.normalize_url("https://example.com") == "https://example.com"

    def test_no_scheme_gets_https(self) -> None:
        assert WebFetcher.normalize_url("example.com") == "https://example.com"

    def test_preserves_path_and_query(self) -> None:
        assert (
            WebFetcher.normalize_url("http://example.com/path?q=1")
            == "https://example.com/path?q=1"
        )


class TestHtmlToMarkdown:
    """Tests for HTML to markdown conversion."""

    def test_basic_html(self) -> None:
        html = "<h1>Hello</h1><p>World</p>"
        md = WebFetcher.html_to_markdown(html)
        assert "# Hello" in md
        assert "World" in md

    def test_strips_script_tags(self) -> None:
        html = '<p>Content</p><script>alert("x")</script><p>More</p>'
        md = WebFetcher.html_to_markdown(html)
        assert "alert" not in md
        assert "Content" in md
        assert "More" in md

    def test_strips_style_tags(self) -> None:
        html = "<style>body { color: red; }</style><p>Visible</p>"
        md = WebFetcher.html_to_markdown(html)
        assert "color" not in md
        assert "Visible" in md

    def test_strips_nav_tags(self) -> None:
        html = "<nav><a href='/'>Home</a></nav><p>Content</p>"
        md = WebFetcher.html_to_markdown(html)
        assert "Home" not in md
        assert "Content" in md

    def test_strips_footer_tags(self) -> None:
        html = "<p>Content</p><footer>Copyright 2025</footer>"
        md = WebFetcher.html_to_markdown(html)
        assert "Copyright" not in md
        assert "Content" in md

    def test_strips_header_tags(self) -> None:
        html = "<header><h1>Site Title</h1></header><main><p>Content</p></main>"
        md = WebFetcher.html_to_markdown(html)
        assert "Site Title" not in md
        assert "Content" in md

    def test_strips_noscript_tags(self) -> None:
        html = "<p>Content</p><noscript>Enable JS</noscript>"
        md = WebFetcher.html_to_markdown(html)
        assert "Enable JS" not in md
        assert "Content" in md

    def test_collapses_excessive_newlines(self) -> None:
        html = "<p>A</p><br><br><br><br><p>B</p>"
        md = WebFetcher.html_to_markdown(html)
        assert "\n\n\n" not in md


class TestCache:
    """Tests for the in-memory cache."""

    def test_cache_miss_returns_none(self, fetcher: WebFetcher) -> None:
        assert fetcher._get_cached("https://example.com") is None

    def test_cache_hit_returns_content(self, fetcher: WebFetcher) -> None:
        fetcher._set_cache("https://example.com", "# Hello")
        result = fetcher._get_cached("https://example.com")
        assert result == "# Hello"

    def test_cache_expired_returns_none(self, fetcher: WebFetcher) -> None:
        fetcher._cache["https://example.com"] = ("# Old", time.time() - CACHE_TTL - 1)
        result = fetcher._get_cached("https://example.com")
        assert result is None
        assert "https://example.com" not in fetcher._cache


class TestFetchAndSummarize:
    """Tests for the full pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline(self, fetcher: WebFetcher) -> None:
        """Test fetch -> convert -> summarize pipeline."""
        html = "<html><body><h1>Test Page</h1><p>Some content here.</p></body></html>"

        with (
            patch.object(fetcher, "_fetch_html", new_callable=AsyncMock) as mock_fetch,
            patch.object(fetcher, "_summarize_with_llm", new_callable=AsyncMock) as mock_summarize,
        ):
            mock_fetch.return_value = html
            mock_summarize.return_value = "This is a test page with some content."

            result = await fetcher.fetch_and_summarize(
                "https://example.com", "What is this page about?"
            )

            assert result == "This is a test page with some content."
            mock_fetch.assert_called_once_with("https://example.com")
            mock_summarize.assert_called_once()
            # Verify markdown was passed to LLM
            call_args = mock_summarize.call_args
            assert "Test Page" in call_args[0][0]
            assert call_args[0][1] == "What is this page about?"

    @pytest.mark.asyncio
    async def test_uses_cache_on_second_call(self, fetcher: WebFetcher) -> None:
        """Test that second call uses cached markdown."""
        html = "<html><body><p>Cached content</p></body></html>"

        with (
            patch.object(fetcher, "_fetch_html", new_callable=AsyncMock) as mock_fetch,
            patch.object(fetcher, "_summarize_with_llm", new_callable=AsyncMock) as mock_summarize,
        ):
            mock_fetch.return_value = html
            mock_summarize.return_value = "Response"

            # First call fetches
            await fetcher.fetch_and_summarize("https://example.com", "Question 1")
            assert mock_fetch.call_count == 1

            # Second call uses cache
            await fetcher.fetch_and_summarize("https://example.com", "Question 2")
            assert mock_fetch.call_count == 1  # Not called again
            assert mock_summarize.call_count == 2  # LLM called both times

    @pytest.mark.asyncio
    async def test_normalizes_url_before_fetch(self, fetcher: WebFetcher) -> None:
        """Test that HTTP URLs are normalized to HTTPS."""
        with (
            patch.object(fetcher, "_fetch_html", new_callable=AsyncMock) as mock_fetch,
            patch.object(fetcher, "_summarize_with_llm", new_callable=AsyncMock) as mock_summarize,
        ):
            mock_fetch.return_value = "<p>Content</p>"
            mock_summarize.return_value = "Response"

            await fetcher.fetch_and_summarize("http://example.com", "Summarize")
            mock_fetch.assert_called_once_with("https://example.com")


class TestSummarizeWithLlm:
    """Tests for the LLM summarization step."""

    @pytest.mark.asyncio
    async def test_truncates_long_content(self, fetcher: WebFetcher) -> None:
        """Test that content exceeding MAX_CONTENT_CHARS is truncated."""
        long_markdown = "x" * (MAX_CONTENT_CHARS + 1000)

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary of long content")]

        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        with patch.object(fetcher, "_get_anthropic", return_value=mock_client):
            result = await fetcher._summarize_with_llm(long_markdown, "Summarize")

        assert result == "Summary of long content"
        # Verify truncated content was sent
        call_args = mock_client.messages.create.call_args
        sent_content = call_args[1]["messages"][0]["content"]
        assert "[Content truncated due to length]" in sent_content

    @pytest.mark.asyncio
    async def test_sends_correct_model(self, fetcher: WebFetcher) -> None:
        """Test that Haiku model is used."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]

        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        with patch.object(fetcher, "_get_anthropic", return_value=mock_client):
            await fetcher._summarize_with_llm("# Content", "Question")

        call_args = mock_client.messages.create.call_args
        assert call_args[1]["model"] == "claude-haiku-4-5-20251001"

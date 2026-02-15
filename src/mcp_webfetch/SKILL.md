# WebFetch

## When to Use (and When Not To)

| Situation | Tool |
|-----------|------|
| Have a specific URL, want to understand its content | `web_fetch` |
| Need to find URLs on a topic | Use a web search tool first, then `web_fetch` on results |
| Want raw HTML or markdown | Don't use this, it returns an LLM summary |
| URL points to PDF, image, JSON API | Don't use this, it only handles HTML pages |

## Writing Effective Prompts

The `prompt` is sent to an LLM along with the page's markdown. Specific prompts get better results.

| Weak | Strong |
|------|--------|
| "Summarize this page" | "Extract the pricing tiers and format as a table" |
| "What is this?" | "What problem does this product solve and who is the target audience?" |
| "Tell me about it" | "List the API endpoints documented on this page with their HTTP methods" |

For large pages, say what section you care about: "Focus on the installation instructions" or "Only look at the FAQ section."

## URL Handling

- **No scheme?** Auto-prepended with `https://` ("example.com" becomes "https://example.com")
- **HTTP?** Auto-upgraded to HTTPS
- **Cross-host redirect?** Returns an error with the redirect URL. Call `web_fetch` again with that new URL.

## Caching

Fetched pages are cached for 15 minutes. Multiple questions about the same URL are cheap because only the LLM step re-runs, not the HTTP fetch. Use this to your advantage:

```
web_fetch(url="https://example.com/docs", prompt="What authentication methods are supported?")
web_fetch(url="https://example.com/docs", prompt="What are the rate limits?")  ← cache hit, no re-fetch
```

## Limitations

- HTML only. Non-HTML content types (PDF, JSON, images) return an error.
- Pages requiring JavaScript rendering may return incomplete content.
- Content over 180K characters is truncated. Be specific in your prompt for large pages.

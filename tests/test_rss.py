import httpx
import pytest

from fetchers.rss import RSSFetcher


def _rss_xml(items):
    body = ['<?xml version="1.0"?><rss><channel>']
    for title, url, desc in items:
        body.append(
            f"<item><title>{title}</title><link>{url}</link>"
            f"<description>{desc}</description></item>"
        )
    body.append("</channel></rss>")
    return "".join(body).encode()


def _patch_client(monkeypatch, transport):
    """Force the fetcher's httpx.AsyncClient to use a MockTransport."""
    real = httpx.AsyncClient

    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real(*args, **kwargs)

    monkeypatch.setattr("fetchers.rss.httpx.AsyncClient", _factory)


@pytest.mark.asyncio
async def test_rss_parses_entries(monkeypatch):
    xml = _rss_xml([("Title 1", "https://example.com/1", "desc 1"),
                    ("Title 2", "https://example.com/2", "desc 2")])

    def handler(request):
        assert request.headers["user-agent"].startswith("CybersecDashboard")
        return httpx.Response(200, content=xml,
                              headers={"content-type": "application/rss+xml"})

    _patch_client(monkeypatch, httpx.MockTransport(handler))
    fetcher = RSSFetcher("test", "https://feed.example.com")
    articles = await fetcher.fetch()

    assert len(articles) == 2
    assert articles[0]["title"] == "Title 1"
    assert articles[0]["url"] == "https://example.com/1"
    assert articles[0]["source"] == "test"
    assert articles[1]["title"] == "Title 2"


@pytest.mark.asyncio
async def test_rss_strips_html_in_desc(monkeypatch):
    xml = _rss_xml([("T", "https://example.com/x",
                     "<p>Hello <b>world</b></p>")])

    def handler(request):
        return httpx.Response(200, content=xml,
                              headers={"content-type": "application/rss+xml"})

    _patch_client(monkeypatch, httpx.MockTransport(handler))
    fetcher = RSSFetcher("test", "https://feed.example.com")
    articles = await fetcher.fetch()

    assert articles[0]["desc"] == "Hello world"


@pytest.mark.asyncio
async def test_rss_raises_on_redirect(monkeypatch):
    def handler(request):
        return httpx.Response(301, headers={"location": "https://elsewhere.example.com"})

    _patch_client(monkeypatch, httpx.MockTransport(handler))
    fetcher = RSSFetcher("test", "https://feed.example.com")
    with pytest.raises(httpx.HTTPStatusError):
        await fetcher.fetch()


@pytest.mark.asyncio
async def test_rss_sends_user_agent(monkeypatch):
    seen = {}

    def handler(request):
        seen["ua"] = request.headers.get("user-agent", "")
        return httpx.Response(200, content=_rss_xml([("T", "https://x.example.com", "d")]),
                              headers={"content-type": "application/rss+xml"})

    _patch_client(monkeypatch, httpx.MockTransport(handler))
    fetcher = RSSFetcher("test", "https://feed.example.com")
    await fetcher.fetch()

    assert seen["ua"].startswith("CybersecDashboard")


@pytest.mark.asyncio
async def test_rss_respects_max_articles(monkeypatch):
    items = [(f"Title {i}", f"https://example.com/{i}", "d") for i in range(10)]
    xml = _rss_xml(items)

    def handler(request):
        return httpx.Response(200, content=xml,
                              headers={"content-type": "application/rss+xml"})

    _patch_client(monkeypatch, httpx.MockTransport(handler))

    class Cfg:
        max_articles_per_source = 3
        max_summary_length = 500

    fetcher = RSSFetcher("test", "https://feed.example.com", config=Cfg())
    articles = await fetcher.fetch()

    assert len(articles) == 3
import json

import httpx
import pytest

from fetchers.cisa_kev import CISAKEVFetcher


def _kev_payload(vulns):
    return json.dumps({
        "title": "CISA KEV",
        "vulnerabilities": vulns,
    }).encode()


def _patch_client(monkeypatch, transport):
    real = httpx.AsyncClient

    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real(*args, **kwargs)

    monkeypatch.setattr("fetchers.cisa_kev.httpx.AsyncClient", _factory)


@pytest.mark.asyncio
async def test_cisa_kev_parses_vulnerabilities(monkeypatch):
    payload = _kev_payload([
        {"cveID": "CVE-2024-1", "vulnerabilityName": "Foo RCE",
         "shortDescription": "bad bug", "dateAdded": "2024-01-15",
         "vendorProject": "Acme", "product": "Widget", "vendorAdvisory": ""},
        {"cveID": "CVE-2024-2", "vulnerabilityName": "Bar Escalation",
         "shortDescription": "worse bug", "dateAdded": "2024-02-20",
         "vendorProject": "Beta", "product": "Gadget", "vendorAdvisory": "https://advisory.example.com/2"},
    ])

    def handler(request):
        assert request.headers["user-agent"].startswith("CybersecDashboard")
        return httpx.Response(200, content=payload,
                              headers={"content-type": "application/json"})

    _patch_client(monkeypatch, httpx.MockTransport(handler))
    fetcher = CISAKEVFetcher()
    articles = await fetcher.fetch()

    assert len(articles) == 2
    assert articles[0]["title"] == "CISA KEV: CVE-2024-1 — Foo RCE"
    assert articles[0]["url"] == "https://nvd.nist.gov/vuln/detail/CVE-2024-1"
    assert articles[0]["published_at"].startswith("2024-01-15")
    assert "CISA KEV" in articles[0]["raw_tags"]
    assert articles[1]["url"] == "https://advisory.example.com/2"


@pytest.mark.asyncio
async def test_cisa_kev_raises_on_redirect(monkeypatch):
    def handler(request):
        return httpx.Response(302, headers={"location": "https://elsewhere.example.com"})

    _patch_client(monkeypatch, httpx.MockTransport(handler))
    fetcher = CISAKEVFetcher()
    with pytest.raises(httpx.HTTPStatusError):
        await fetcher.fetch()


@pytest.mark.asyncio
async def test_cisa_kev_sends_user_agent(monkeypatch):
    seen = {}
    payload = _kev_payload([{"cveID": "CVE-2024-9", "vulnerabilityName": "X",
                            "shortDescription": "d", "dateAdded": "2024-09-01",
                            "vendorProject": "", "product": "", "vendorAdvisory": ""}])

    def handler(request):
        seen["ua"] = request.headers.get("user-agent", "")
        return httpx.Response(200, content=payload,
                              headers={"content-type": "application/json"})

    _patch_client(monkeypatch, httpx.MockTransport(handler))
    fetcher = CISAKEVFetcher()
    await fetcher.fetch()

    assert seen["ua"].startswith("CybersecDashboard")
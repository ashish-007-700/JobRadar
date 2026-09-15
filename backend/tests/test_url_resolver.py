import httpx
import pytest

from app.services import url_resolver
from app.services.url_resolver import ResolutionStatus, find_best_candidate, resolve_apply_url


def html_page(body: str) -> str:
    return f"<html><body>{body}</body></html>"


def make_client(pages: dict[str, httpx.Response]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url not in pages:
            return httpx.Response(404, text="not found")
        return pages[url]

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def html_response(body: str) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "text/html"}, text=html_page(body))


# 1. Direct application: page has no further apply link -----------------------------


@pytest.mark.asyncio
async def test_direct_application_no_further_link():
    original = "https://careers.acme.com/jobs/1"
    pages = {original: html_response("<p>Full job description here. No further links.</p>")}

    async with make_client(pages) as client:
        result = await resolve_apply_url(original, client=client)

    assert result["resolution_status"] == ResolutionStatus.NO_NEXT_LINK
    assert result["final_apply_url"] == original
    assert result["steps_followed"] == 0


# 2. One intermediate page -----------------------------------------------------------


@pytest.mark.asyncio
async def test_one_intermediate_page_resolves_to_employer():
    aggregator = "https://aggregator.com/job/1"
    employer = "https://careers.acme.com/apply/1"
    pages = {
        aggregator: html_response(f'<a href="{employer}">Apply Now</a>'),
        employer: html_response("<p>Application form here.</p>"),
    }

    async with make_client(pages) as client:
        result = await resolve_apply_url(aggregator, client=client)

    assert result["resolution_status"] == ResolutionStatus.RESOLVED
    assert result["final_apply_url"] == employer
    assert result["steps_followed"] == 1


# 3. Multiple intermediate pages ------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_intermediate_pages():
    site_a = "https://site-a.com/job"
    site_b = "https://site-b.com/redirectish"
    employer = "https://careers.company.com/jobs/123"
    pages = {
        site_a: html_response(f'<a href="{site_b}">Apply Here</a>'),
        site_b: html_response(f'<a href="{employer}">Official Apply</a>'),
        employer: html_response("<p>No more links.</p>"),
    }

    async with make_client(pages) as client:
        result = await resolve_apply_url(site_a, client=client)

    assert result["final_apply_url"] == employer
    assert result["steps_followed"] == 2
    assert result["resolution_status"] == ResolutionStatus.RESOLVED


# 4. No Apply link at all -------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_apply_link_stops_at_current():
    original = "https://blog.example.com/post"
    pages = {
        original: html_response(
            '<a href="/about">About Us</a> <a href="/home">Home</a>'
        )
    }

    async with make_client(pages) as client:
        result = await resolve_apply_url(original, client=client)

    assert result["resolution_status"] == ResolutionStatus.NO_NEXT_LINK
    assert result["final_apply_url"] == original


# 5. Social links are ignored, only Apply Now is considered ---------------------------


def test_find_best_candidate_ignores_social_links():
    body = (
        '<a href="https://chat.whatsapp.com/xyz">WhatsApp</a>'
        '<a href="https://t.me/xyz">Telegram</a>'
        '<a href="https://instagram.com/xyz">Instagram</a>'
        '<a href="https://acme.com/apply">Apply Now</a>'
    )
    candidate = find_best_candidate(html_page(body), "https://intermediate.com/")
    assert candidate == "https://acme.com/apply"


@pytest.mark.asyncio
async def test_social_links_and_apply_end_to_end():
    intermediate = "https://intermediate.com/job"
    employer = "https://acme.com/apply"
    pages = {
        intermediate: html_response(
            '<a href="https://chat.whatsapp.com/xyz">WhatsApp</a>'
            '<a href="https://t.me/xyz">Telegram</a>'
            f'<a href="{employer}">Apply Now</a>'
        ),
        employer: html_response("<p>Application page.</p>"),
    }

    async with make_client(pages) as client:
        result = await resolve_apply_url(intermediate, client=client)

    assert result["final_apply_url"] == employer
    assert result["steps_followed"] == 1


# 6. Redirect chain is recorded --------------------------------------------------------


@pytest.mark.asyncio
async def test_redirect_chain_is_recorded():
    start = "https://short.link/abc"
    final = "https://careers.company.com/jobs/1"
    pages = {
        start: httpx.Response(302, headers={"location": final}),
        final: html_response("<p>No further links.</p>"),
    }

    async with make_client(pages) as client:
        result = await resolve_apply_url(start, client=client)

    assert result["final_apply_url"] == final
    assert start in result["redirect_chain"]
    assert final in result["redirect_chain"]


# 7. Loop detection ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_loop_is_detected_and_stopped():
    site_a = "https://site-a.com/"
    site_b = "https://site-b.com/"
    pages = {
        site_a: html_response(f'<a href="{site_b}">Apply Now</a>'),
        site_b: html_response(f'<a href="{site_a}">Apply Now</a>'),
    }

    async with make_client(pages) as client:
        result = await resolve_apply_url(site_a, client=client)

    assert result["resolution_status"] == ResolutionStatus.LOOP_DETECTED
    assert result["final_apply_url"] == site_b
    assert result["steps_followed"] == 1


# 8. Maximum depth protection -------------------------------------------------------------


@pytest.mark.asyncio
async def test_max_depth_reached(monkeypatch):
    monkeypatch.setattr(url_resolver, "MAX_RESOLUTION_DEPTH", 2)

    urls = [f"https://chain.com/step{i}" for i in range(6)]
    pages = {}
    for i in range(len(urls) - 1):
        pages[urls[i]] = html_response(f'<a href="{urls[i + 1]}">Apply Now</a>')
    pages[urls[-1]] = html_response("<p>End of chain.</p>")

    async with make_client(pages) as client:
        result = await resolve_apply_url(urls[0], client=client)

    assert result["resolution_status"] == ResolutionStatus.MAX_DEPTH_REACHED
    assert result["steps_followed"] == 2
    assert result["final_apply_url"] == urls[2]


# 9. HTTP timeout / error handling ---------------------------------------------------------


@pytest.mark.asyncio
async def test_http_timeout_is_handled_gracefully():
    original = "https://slow.example.com/job"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await resolve_apply_url(original, client=client)

    assert result["resolution_status"] == ResolutionStatus.TIMEOUT
    assert result["final_apply_url"] == original


@pytest.mark.asyncio
async def test_http_error_status_is_handled_gracefully():
    original = "https://broken.example.com/job"
    pages = {original: httpx.Response(500, text="server error")}

    async with make_client(pages) as client:
        result = await resolve_apply_url(original, client=client)

    assert result["resolution_status"] == ResolutionStatus.HTTP_ERROR
    assert result["final_apply_url"] == original


# 10. JavaScript-heavy page uses the Playwright fallback only when needed -----------------


@pytest.mark.asyncio
async def test_javascript_heavy_page_uses_playwright_fallback(monkeypatch):
    spa_shell = "https://spa.example.com/job"
    rendered_apply = "https://spa.example.com/apply"

    # A typical empty SPA shell: little text, several script tags, no real links.
    shell_html = (
        "<div id='root'></div>"
        + "<script src='a.js'></script>" * 4
    )
    pages = {
        spa_shell: httpx.Response(200, headers={"content-type": "text/html"}, text=shell_html),
        rendered_apply: html_response("<p>Application form here.</p>"),
    }

    async def fake_render(url: str) -> str:
        assert url == spa_shell
        return html_page(f'<a href="{rendered_apply}">Apply Now</a>')

    monkeypatch.setattr(url_resolver, "_fetch_rendered_html", fake_render)

    async with make_client(pages) as client:
        result = await resolve_apply_url(spa_shell, client=client)

    assert result["final_apply_url"] == rendered_apply
    assert result["steps_followed"] == 1


@pytest.mark.asyncio
async def test_playwright_not_used_when_page_has_normal_content(monkeypatch):
    original = "https://normal.example.com/job"
    pages = {original: html_response("<p>Plenty of readable job description text here.</p>")}

    async def fail_if_called(url: str) -> str:
        raise AssertionError("Playwright fallback should not be used for a normal HTML page")

    monkeypatch.setattr(url_resolver, "_fetch_rendered_html", fail_if_called)

    async with make_client(pages) as client:
        result = await resolve_apply_url(original, client=client)

    assert result["resolution_status"] == ResolutionStatus.NO_NEXT_LINK


# Pure helper tests ------------------------------------------------------------------------


def test_normalize_url_strips_tracking_params_and_fragment():
    normalized = url_resolver.normalize_url(
        "https://example.com/page?utm_source=telegram&id=5#section"
    )
    assert normalized == "https://example.com/page?id=5"


def test_is_safe_url_blocks_private_and_loopback():
    assert url_resolver.is_safe_url("http://example.com") is True
    assert url_resolver.is_safe_url("http://127.0.0.1") is False
    assert url_resolver.is_safe_url("http://localhost") is False
    assert url_resolver.is_safe_url("http://192.168.1.10") is False
    assert url_resolver.is_safe_url("ftp://example.com") is False


def test_invalid_empty_url_is_rejected():
    import asyncio

    result = asyncio.run(resolve_apply_url(""))
    assert result["resolution_status"] == ResolutionStatus.INVALID_URL

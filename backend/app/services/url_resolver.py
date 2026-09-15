import html
import ipaddress
import logging
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from app.config import MAX_RESOLUTION_DEPTH

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}
REQUEST_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MB, avoid downloading huge/non-HTML bodies
MAX_REDIRECTS_PER_HOP = 10
REDIRECT_STATUS_CODES = (301, 302, 303, 307, 308)

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "igshid",
}

SOCIAL_DOMAINS = [
    "whatsapp.com",
    "wa.me",
    "t.me",
    "telegram.me",
    "telegram.org",
    "facebook.com",
    "fb.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "youtu.be",
    "twitter.com",
    "x.com",
]

AVOID_TEXT_KEYWORDS = [
    "whatsapp",
    "telegram",
    "facebook",
    "instagram",
    "youtube",
    "linkedin",
    "newsletter",
    "subscribe",
    "privacy",
    "terms",
    "cookie",
    "home",
    "about us",
    "contact us",
    "blog",
    "sign in",
    "log in",
]

STRONG_APPLY_PHRASES = [
    "apply now",
    "apply here",
    "click here to apply",
    "submit application",
    "official apply",
    "apply online",
]
MEDIUM_APPLY_PHRASES = ["apply", "application", "view job", "apply for this job"]
WEAK_APPLY_PHRASES = ["careers", "official website", "company website", "view details"]

KNOWN_ATS_DOMAINS = [
    "greenhouse.io",
    "lever.co",
    "myworkdayjobs.com",
    "workday.com",
    "smartrecruiters.com",
    "icims.com",
    "successfactors.com",
    "oraclecloud.com",
    "taleo.net",
    "bamboohr.com",
    "jobvite.com",
    "ashbyhq.com",
    "workable.com",
]


class UnsafeRedirectError(Exception):
    def __init__(self, url: str):
        super().__init__(f"Redirect target blocked by SSRF policy: {url}")
        self.url = url


class TooManyRedirectsError(Exception):
    pass


class ResolutionStatus:
    RESOLVED = "resolved"
    NO_NEXT_LINK = "no_next_link"
    MAX_DEPTH_REACHED = "max_depth_reached"
    HTTP_ERROR = "http_error"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    INVALID_URL = "invalid_url"
    LOOP_DETECTED = "loop_detected"
    RESOLUTION_ERROR = "resolution_error"


def normalize_url(url: str, base: str | None = None) -> str:
    url = html.unescape(url.strip())
    if base:
        url = urljoin(base, url)
    parsed = urlparse(url)
    if not parsed.scheme:
        parsed = urlparse(f"https://{url}")
    query_pairs = [
        (key, value) for key, value in parse_qsl(parsed.query) if key.lower() not in TRACKING_PARAMS
    ]
    normalized = parsed._replace(fragment="", query=urlencode(query_pairs))
    return urlunparse(normalized)


def is_safe_url(url: str) -> bool:
    """Basic SSRF guard: only http(s), and reject literal localhost/private/loopback
    IPs. Does not resolve hostnames, so it cannot catch DNS-rebinding attacks against
    a public hostname that resolves to a private IP — see README known limitations."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False

    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if host == "localhost" or host.endswith(".local"):
        return False

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True  # a regular hostname, not a literal IP

    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _is_social_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(domain in host for domain in SOCIAL_DOMAINS)


def looks_like_employer_domain(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    if any(domain in host for domain in KNOWN_ATS_DOMAINS):
        return True
    return host.startswith("careers.") or host.startswith("jobs.") or ".careers." in host


def _link_confidence(text: str, href: str) -> int | None:
    lower_text = (text or "").strip().lower()
    if not lower_text or _is_social_url(href):
        return None
    if any(keyword in lower_text for keyword in AVOID_TEXT_KEYWORDS):
        return None
    if any(phrase in lower_text for phrase in STRONG_APPLY_PHRASES):
        return 3
    if any(phrase in lower_text for phrase in MEDIUM_APPLY_PHRASES):
        return 2
    if any(phrase in lower_text for phrase in WEAK_APPLY_PHRASES):
        return 1
    return None


def find_best_candidate(html_text: str, base_url: str) -> str | None:
    soup = BeautifulSoup(html_text, "html.parser")
    candidates: list[tuple[int, str]] = []

    for anchor in soup.find_all("a", href=True):
        text = anchor.get_text(" ", strip=True)
        try:
            href = normalize_url(anchor["href"], base=base_url)
        except Exception:
            continue
        confidence = _link_confidence(text, href)
        if confidence is not None:
            candidates.append((confidence, href))

    for form in soup.find_all("form", action=True):
        identifiers = " ".join([form.get("id", ""), " ".join(form.get("class", []))]).lower()
        if "apply" in identifiers or "application" in identifiers:
            try:
                href = normalize_url(form["action"], base=base_url)
            except Exception:
                continue
            candidates.append((2, href))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _looks_js_rendered(html_text: str) -> bool:
    soup = BeautifulSoup(html_text, "html.parser")
    visible_text = soup.get_text(strip=True)
    return len(visible_text) < 200 and len(soup.find_all("script")) >= 3


async def _fetch_rendered_html(url: str) -> str | None:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.info("Playwright not installed; skipping JS-rendering fallback for %s", url)
        return None

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page(user_agent=DEFAULT_HEADERS["User-Agent"])
                await page.goto(url, timeout=15000, wait_until="networkidle")
                return await page.content()
            finally:
                await browser.close()
    except Exception as exc:
        logger.info("Playwright fallback failed for %s: %s", url, exc)
        return None


async def _fetch_page(client: httpx.AsyncClient, url: str) -> tuple[str, str, list[str], int]:
    # Redirects are followed manually (not via httpx's follow_redirects=True) so
    # every intermediate hop — not just the initial URL — passes is_safe_url().
    # httpx's built-in redirect following has no hook for that: a "safe" URL
    # could 302 straight to a private/loopback address and httpx would fetch it
    # without ever asking us.
    redirect_urls: list[str] = []
    current_url = url

    for _ in range(MAX_REDIRECTS_PER_HOP + 1):
        if not is_safe_url(current_url):
            raise UnsafeRedirectError(current_url)

        async with client.stream(
            "GET", current_url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT, follow_redirects=False
        ) as response:
            if response.status_code in REDIRECT_STATUS_CODES and "location" in response.headers:
                redirect_urls.append(str(response.url))
                current_url = normalize_url(response.headers["location"], base=str(response.url))
                continue

            if response.status_code >= 400:
                return str(response.url), "", redirect_urls, response.status_code

            content_type = response.headers.get("content-type", "")
            if content_type and "text/html" not in content_type:
                return str(response.url), "", redirect_urls, response.status_code

            chunks = []
            total = 0
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                chunks.append(chunk)
                if total > MAX_RESPONSE_BYTES:
                    break
            body = b"".join(chunks)
            text = body.decode(response.encoding or "utf-8", errors="replace")
            return str(response.url), text, redirect_urls, response.status_code

    raise TooManyRedirectsError(f"Exceeded {MAX_REDIRECTS_PER_HOP} redirects")


def _result(original: str, final: str, status: str, chain: list[str], steps: int, error: str | None) -> dict:
    return {
        "original_apply_url": original,
        "final_apply_url": final,
        "resolution_status": status,
        "redirect_chain": chain,
        "steps_followed": steps,
        "error": error,
        "final_url_confidence": "high" if looks_like_employer_domain(final) else "low",
    }


async def _resolve_with_client(client: httpx.AsyncClient, original_url: str) -> dict:
    try:
        current = normalize_url(original_url)
    except Exception as exc:
        return _result(original_url, original_url, ResolutionStatus.INVALID_URL, [], 0, str(exc))

    if not is_safe_url(current):
        return _result(original_url, current, ResolutionStatus.BLOCKED, [], 0, "URL blocked by SSRF policy")

    redirect_chain: list[str] = []
    visited: set[str] = set()
    last_reached = current

    # hop == steps_followed: hop 0 is the original URL itself, hop N is the page
    # reached after following N application links from it.
    for hop in range(MAX_RESOLUTION_DEPTH + 1):
        if current in visited:
            return _result(
                original_url, last_reached, ResolutionStatus.LOOP_DETECTED, redirect_chain, hop, "Cycle detected"
            )
        visited.add(current)

        if not is_safe_url(current):
            return _result(
                original_url, last_reached, ResolutionStatus.BLOCKED, redirect_chain, hop, "URL blocked by SSRF policy"
            )

        try:
            effective_url, html_text, redirects, status_code = await _fetch_page(client, current)
        except UnsafeRedirectError as exc:
            return _result(original_url, last_reached, ResolutionStatus.BLOCKED, redirect_chain, hop, str(exc))
        except TooManyRedirectsError as exc:
            return _result(original_url, last_reached, ResolutionStatus.HTTP_ERROR, redirect_chain, hop, str(exc))
        except httpx.TimeoutException:
            return _result(original_url, last_reached, ResolutionStatus.TIMEOUT, redirect_chain, hop, "Request timed out")
        except httpx.HTTPError as exc:
            return _result(original_url, last_reached, ResolutionStatus.HTTP_ERROR, redirect_chain, hop, str(exc))
        except Exception as exc:
            return _result(original_url, last_reached, ResolutionStatus.RESOLUTION_ERROR, redirect_chain, hop, str(exc))

        if status_code >= 400:
            return _result(
                original_url, last_reached, ResolutionStatus.HTTP_ERROR, redirect_chain, hop, f"HTTP {status_code}"
            )

        for redirect_url in redirects:
            if redirect_url not in redirect_chain:
                redirect_chain.append(redirect_url)
        if effective_url not in redirect_chain:
            redirect_chain.append(effective_url)

        last_reached = effective_url
        visited.add(effective_url)

        candidate = find_best_candidate(html_text, effective_url) if html_text else None
        if candidate is None and html_text and _looks_js_rendered(html_text):
            rendered_html = await _fetch_rendered_html(effective_url)
            if rendered_html:
                candidate = find_best_candidate(rendered_html, effective_url)

        if candidate is None:
            # hop == 0 means we never left the original URL ("simply the original
            # URL because no further link was found"); hop > 0 means we followed
            # one or more hops and settled on a stable final page ("resolved").
            status = ResolutionStatus.RESOLVED if hop > 0 else ResolutionStatus.NO_NEXT_LINK
            return _result(original_url, effective_url, status, redirect_chain, hop, None)

        if candidate == effective_url or candidate in visited:
            return _result(
                original_url, effective_url, ResolutionStatus.LOOP_DETECTED, redirect_chain, hop, "Cycle detected"
            )

        current = candidate

    return _result(original_url, last_reached, ResolutionStatus.MAX_DEPTH_REACHED, redirect_chain, MAX_RESOLUTION_DEPTH, None)


async def resolve_apply_url(original_url: str, client: httpx.AsyncClient | None = None) -> dict:
    if not original_url or not original_url.strip():
        return _result(original_url, original_url, ResolutionStatus.INVALID_URL, [], 0, "Empty URL")

    if client is not None:
        return await _resolve_with_client(client, original_url)

    async with httpx.AsyncClient() as owned_client:
        return await _resolve_with_client(owned_client, original_url)

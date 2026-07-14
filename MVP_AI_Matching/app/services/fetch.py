"""
Shared file download helper — used by any endpoint that needs to pull a CV
file (S3/R2/presigned URL) before extracting its text.
"""

from __future__ import annotations

import asyncio
import re

import httpx


async def fetch_file(url: str, client: httpx.AsyncClient) -> tuple[bytes, str]:
    """Download file from URL. Returns (bytes, filename). Retries up to 3x on transient errors."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = await client.get(url, follow_redirects=True, timeout=30.0)
            resp.raise_for_status()
            break
        except (httpx.TransportError, httpx.ConnectError) as e:
            last_exc = e
            await asyncio.sleep(1.5 * (attempt + 1))
    else:
        raise last_exc

    # Try Content-Disposition header first
    filename = ""
    cd = resp.headers.get("content-disposition", "")
    if cd:
        m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\r\n]+)', cd, re.IGNORECASE)
        if m:
            filename = m.group(1).strip().strip('"\'')

    # Fallback: last path segment (strip query string)
    if not filename:
        filename = url.split("?")[0].rstrip("/").split("/")[-1]

    # Ensure recognizable extension
    if "." not in filename.rsplit("/", 1)[-1]:
        ct = resp.headers.get("content-type", "")
        ext = ".docx" if ("wordprocessingml" in ct or "docx" in ct) else ".pdf"
        filename += ext

    return resp.content, filename

"""Allowlist-based HTML sanitizer for rich-text bodies.

Rich text is stored as HTML, so every body that enters the system is sanitized to
prevent stored XSS: only a known set of formatting tags/attributes survive, and
``<script>``/``<style>``/event handlers/`javascript:` URLs are stripped. Implemented
with BeautifulSoup (already a dependency) to avoid adding a native lib.
"""
from __future__ import annotations

from bs4 import BeautifulSoup, Comment

# Tags TipTap's StarterKit + our extensions can emit.
_ALLOWED_TAGS = {
    "p", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "b", "em", "i", "u", "s", "del", "sub", "sup",
    "ul", "ol", "li",
    "blockquote", "pre", "code",
    "a", "span", "mark",
}

# Per-tag allowed attributes.
_ALLOWED_ATTRS = {
    "a": {"href", "title", "target", "rel"},
    "span": {"style", "data-color"},
    "mark": {"style", "data-color"},
    "*": {"class"},
}

# CSS properties allowed inside an inline style="" attribute.
_ALLOWED_STYLE_PROPS = {"color", "background-color"}

_SAFE_URL_SCHEMES = {"http", "https", "mailto", ""}


def _clean_style(raw: str) -> str:
    parts = []
    for decl in raw.split(";"):
        if ":" not in decl:
            continue
        prop, _, value = decl.partition(":")
        prop = prop.strip().lower()
        value = value.strip()
        if prop in _ALLOWED_STYLE_PROPS and value and "url(" not in value.lower():
            parts.append(f"{prop}: {value}")
    return "; ".join(parts)


def _safe_href(value: str) -> bool:
    value = value.strip()
    if value.startswith("/") or value.startswith("#"):
        return True
    scheme = value.split(":", 1)[0].lower() if ":" in value else ""
    return scheme in _SAFE_URL_SCHEMES


def sanitize_html(raw_html: str) -> str:
    """Return a sanitized copy of ``raw_html`` containing only allowlisted markup."""
    if not raw_html:
        return "<p></p>"

    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove HTML comments outright.
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()

    for tag in list(soup.find_all(True)):
        name = tag.name.lower()
        if name not in _ALLOWED_TAGS:
            tag.unwrap()  # keep children/text, drop the disallowed wrapper
            continue

        allowed = set(_ALLOWED_ATTRS.get(name, set())) | _ALLOWED_ATTRS["*"]
        for attr in list(tag.attrs):
            if attr.lower() not in allowed:
                del tag[attr]
                continue
            if attr.lower() == "style":
                cleaned = _clean_style(str(tag[attr]))
                if cleaned:
                    tag[attr] = cleaned
                else:
                    del tag[attr]
            elif attr.lower() == "href":
                if not _safe_href(str(tag[attr])):
                    del tag[attr]

        # Harden external links.
        if name == "a" and tag.get("href"):
            tag["rel"] = "noopener noreferrer nofollow"

    cleaned = str(soup).strip()
    return cleaned or "<p></p>"


def html_to_plain_text(raw_html: str) -> str:
    """Extract a plain-text projection (used for comment anchoring / previews)."""
    soup = BeautifulSoup(raw_html or "", "html.parser")
    return soup.get_text(separator=" ", strip=True)

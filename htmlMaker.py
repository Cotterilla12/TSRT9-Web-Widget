from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


# Address at which the running Flask app can be opened.
BASE_URL = "http://127.0.0.1:8000"

# Page to export. Change this to include an existing code if required:
# HOME_PATH = "/TSRT9/Level%201/A1/MD2/CF1a/D01"
HOME_PATH = "/"

OUTPUT_FILE = Path("TSRT9-standalone.html")
TIMEOUT_SECONDS = 30


def download_text(
    session: requests.Session,
    url: str,
) -> str:
    response = session.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.text


def download_bytes(
    session: requests.Session,
    url: str,
) -> tuple[bytes, str]:
    response = session.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()

    mime_type = response.headers.get(
        "Content-Type",
        "application/octet-stream",
    ).split(";")[0].strip()

    if mime_type == "application/octet-stream":
        guessed_type, _ = mimetypes.guess_type(url)
        mime_type = guessed_type or mime_type

    return response.content, mime_type


def belongs_to_app(url: str) -> bool:
    parsed_url = urlparse(url)
    parsed_base = urlparse(BASE_URL)

    return (
        parsed_url.scheme in {"http", "https"}
        and parsed_url.netloc == parsed_base.netloc
    )


def make_data_url(
    content: bytes,
    mime_type: str,
) -> str:
    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def inline_css_urls(
    css: str,
    stylesheet_url: str,
    session: requests.Session,
) -> str:
    """
    Inline simple url(...) references inside CSS.

    This covers common local background images and font files.
    """
    import re

    pattern = re.compile(
        r"url\(\s*(['\"]?)(.*?)\1\s*\)",
        flags=re.IGNORECASE,
    )

    def replace_url(match: re.Match) -> str:
        resource = match.group(2).strip()

        if not resource:
            return match.group(0)

        if resource.startswith(
            (
                "data:",
                "http://",
                "https://",
                "#",
            )
        ):
            return match.group(0)

        resource_url = urljoin(stylesheet_url, resource)

        if not belongs_to_app(resource_url):
            return match.group(0)

        try:
            content, mime_type = download_bytes(
                session,
                resource_url,
            )
        except requests.RequestException:
            print(
                "Warning: could not embed CSS resource:",
                resource_url,
            )
            return match.group(0)

        return f"url('{make_data_url(content, mime_type)}')"

    return pattern.sub(replace_url, css)


def inline_stylesheets(
    soup: BeautifulSoup,
    page_url: str,
    session: requests.Session,
) -> None:
    for link in list(soup.find_all("link", href=True)):
        rel_values = [
            str(value).lower()
            for value in link.get("rel", [])
        ]

        if "stylesheet" not in rel_values:
            continue

        stylesheet_url = urljoin(
            page_url,
            link["href"],
        )

        if not belongs_to_app(stylesheet_url):
            continue

        css = download_text(
            session,
            stylesheet_url,
        )

        css = inline_css_urls(
            css,
            stylesheet_url,
            session,
        )

        style = soup.new_tag("style")
        style.string = css
        link.replace_with(style)


def inline_external_scripts(
    soup: BeautifulSoup,
    page_url: str,
    session: requests.Session,
) -> None:
    for script in list(soup.find_all("script", src=True)):
        script_url = urljoin(
            page_url,
            script["src"],
        )

        if not belongs_to_app(script_url):
            continue

        javascript = download_text(
            session,
            script_url,
        )

        replacement = soup.new_tag("script")

        # Preserve useful script attributes.
        for attribute in (
            "type",
            "defer",
            "async",
            "nomodule",
        ):
            if script.has_attr(attribute):
                replacement[attribute] = script[attribute]

        replacement.string = javascript
        script.replace_with(replacement)


def inline_images(
    soup: BeautifulSoup,
    page_url: str,
    session: requests.Session,
) -> None:
    for image in soup.find_all("img", src=True):
        source = image["src"]

        if source.startswith(("data:", "#")):
            continue

        image_url = urljoin(page_url, source)

        if not belongs_to_app(image_url):
            continue

        content, mime_type = download_bytes(
            session,
            image_url,
        )

        image["src"] = make_data_url(
            content,
            mime_type,
        )


def inline_icons(
    soup: BeautifulSoup,
    page_url: str,
    session: requests.Session,
) -> None:
    icon_relationships = {
        "icon",
        "shortcut",
        "shortcut icon",
        "apple-touch-icon",
    }

    for link in soup.find_all("link", href=True):
        rel = " ".join(
            str(value).lower()
            for value in link.get("rel", [])
        )

        if rel not in icon_relationships:
            continue

        icon_url = urljoin(
            page_url,
            link["href"],
        )

        if not belongs_to_app(icon_url):
            continue

        content, mime_type = download_bytes(
            session,
            icon_url,
        )

        link["href"] = make_data_url(
            content,
            mime_type,
        )


def make_page_standalone(
    page_html: str,
    page_url: str,
    session: requests.Session,
) -> str:
    soup = BeautifulSoup(
        page_html,
        "html.parser",
    )

    inline_stylesheets(
        soup,
        page_url,
        session,
    )

    inline_external_scripts(
        soup,
        page_url,
        session,
    )

    inline_images(
        soup,
        page_url,
        session,
    )

    inline_icons(
        soup,
        page_url,
        session,
    )

    return str(soup)


def embed_widget_iframe(
    home_html: str,
    home_url: str,
    session: requests.Session,
) -> str:
    home_soup = BeautifulSoup(
        home_html,
        "html.parser",
    )

    iframe = home_soup.find(
        "iframe",
        id="widgetIframe",
    )

    if iframe is None:
        raise RuntimeError(
            'Could not find an iframe with '
            'id="widgetIframe" in the rendered home page.'
        )

    iframe_source = iframe.get("src")

    if not iframe_source:
        raise RuntimeError(
            "The widget iframe does not have a src attribute."
        )

    widget_url = urljoin(
        home_url,
        iframe_source,
    )

    print("Downloading widget:", widget_url)

    widget_html = download_text(
        session,
        widget_url,
    )

    widget_html = make_page_standalone(
        widget_html,
        widget_url,
        session,
    )

    widget_data_url = make_data_url(
        widget_html.encode("utf-8"),
        "text/html;charset=utf-8",
    )

    # Replace the server route with an embedded HTML document.
    iframe["src"] = widget_data_url

    # Remove any previous broken srcdoc attempt.
    iframe.attrs.pop("srcdoc", None)

    return str(home_soup)


def export() -> None:
    with requests.Session() as session:
        home_url = urljoin(
            BASE_URL,
            HOME_PATH,
        )

        print("Downloading home page:", home_url)

        home_html = download_text(
            session,
            home_url,
        )

        # Put the fully rendered widget into the iframe as a data URL.
        home_html = embed_widget_iframe(
            home_html,
            home_url,
            session,
        )

        # Embed the home page's own CSS, scripts and images.
        final_html = make_page_standalone(
            home_html,
            home_url,
            session,
        )

        OUTPUT_FILE.write_text(
            final_html,
            encoding="utf-8",
        )

    print()
    print("Created:")
    print(OUTPUT_FILE.resolve())


if __name__ == "__main__":
    try:
        export()

    except requests.ConnectionError as exc:
        raise SystemExit(
            "\nCould not connect to the Flask application.\n"
            f"Start it at {BASE_URL}, leave it running, "
            "then run this script in another terminal.\n\n"
            f"{exc}"
        ) from exc

    except requests.HTTPError as exc:
        raise SystemExit(
            f"\nThe Flask application returned an HTTP error:\n{exc}"
        ) from exc

    except Exception as exc:
        raise SystemExit(
            f"\nExport failed:\n{exc}"
        ) from exc
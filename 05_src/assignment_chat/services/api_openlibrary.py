import requests

SEARCH_URL = "https://openlibrary.org/search.json"
BOOKS_URL  = "https://openlibrary.org/api/books"

HEADERS = {
    "User-Agent": "DSI-AssignmentChat (jiamin.liao@mail.utoronto.ca)"
}

def openlibrary_search_top(query: str, limit: int = 5) -> list[dict]:
    params = {
        "q": query,
        "limit": limit,
        "fields": "title,author_name,first_publish_year,isbn,key",
    }
    r = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    docs = r.json().get("docs", []) or []

    results = []
    for d in docs[:limit]:
        title = d.get("title") or "Unknown title"
        authors = d.get("author_name", []) or []
        year = d.get("first_publish_year")
        isbns = d.get("isbn", []) or []
        isbn = isbns[0] if isbns else None
        key = d.get("key")

        results.append({
            "title": title,
            "authors": authors,
            "first_publish_year": year,
            "isbn": isbn,
            "key": key,
        })

    return results

def openlibrary_book_details_by_isbn(isbn: str) -> dict:
    if not isbn:
        return {}

    params = {
        "bibkeys": f"ISBN:{isbn}",
        "format": "json",
        "jscmd": "data",
    }
    r = requests.get(BOOKS_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data.get(f"ISBN:{isbn}", {}) or {}

def openlibrary_url_from_work_or_edition(details: dict, fallback_key: str | None = None) -> str:
    url = details.get("url")
    if isinstance(url, str) and url.startswith("/"):
        return "https://openlibrary.org" + url

    info_url = details.get("info_url")
    if isinstance(info_url, str) and info_url.startswith("http"):
        return info_url

    if fallback_key and isinstance(fallback_key, str) and fallback_key.startswith("/"):
        return "https://openlibrary.org" + fallback_key

    return ""
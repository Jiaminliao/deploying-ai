import gradio as gr
from openai import OpenAI
import os
from dotenv import load_dotenv
import traceback

from guardrails import check_guardrails

from services.retrieval_chroma import build_kb_if_empty, semantic_search
from services.tools_service import run_tools_loop
from services.api_openlibrary import (
    openlibrary_search_top,
    openlibrary_book_details_by_isbn,
    openlibrary_url_from_work_or_edition as openlibrary_best_url
)

load_dotenv("05_src/.secrets")

if not os.getenv("API_GATEWAY_KEY"):
    raise ValueError("API_GATEWAY_KEY is not set. Please check 05_src/.secrets")

build_kb_if_empty()

client = OpenAI(
    base_url="https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1",
    api_key="any value",
    default_headers={"x-api-key": os.getenv("API_GATEWAY_KEY")},
)

instructions = "You are a helpful assistant."

PENDING_BOOKS = []
PENDING_QUERY = ""

def _clean_book_query(message: str) -> str:
    """Convert user message into keywords for OpenLibrary search (ALWAYS returns a string)."""
    q = (message or "").lower()

    for phrase in [
        "recommend books for",
        "recommend book for",
        "recommend books about",
        "recommend a book about",
        "recommend books",
        "recommend book",
        "books about",
        "book about",
        "books for",
        "book for",
        "a book about",
        "books on",
        "book on",
        "can you",
        "could you",
        "please",
        "for me",
    ]:
        q = q.replace(phrase, " ")

    q = " ".join(q.split())

    if q.startswith("for "):
        q = q[4:].strip()

    return q

def _format_candidates(cands: list[dict]) -> str:
    cands = cands or []
    lines = []
    for i, c in enumerate(cands, 1):
        title = c.get("title", "Unknown title")
        authors = c.get("authors", []) or []
        author_str = ", ".join(authors[:2]) if authors else "Unknown author"
        year = c.get("first_publish_year") or "Unknown year"
        lines.append(f"{i}) {title} — {author_str} ({year})")
    return "\n".join(lines)

def _friendly_book_message(title: str, author_str: str, year, url: str) -> str:
    year_str = year if year else "Unknown year"
    url_str = url if url else "(No URL available from OpenLibrary metadata.)"

    return f"""Here is a book I found on OpenLibrary:

Title: {title}
Author(s): {author_str}
First publish year: {year_str}
URL: {url_str}

Why it may be useful:
- I can’t reliably summarize the book’s content from OpenLibrary metadata alone, but the title/author info above is verified.
- If you want, tell me what you care about (e.g., music theory, music history, songwriting), and I can search again with a more specific query.
"""

def chat_fn(message, history):
    global PENDING_BOOKS, PENDING_QUERY

    try:
        ok, msg = check_guardrails(message)
        if not ok:
            return msg

        m = (message or "").lower().strip()

        # Semantic Query (ChromaDB)
        if "kb:" in m or "notes:" in m or "from kb" in m:
            docs = semantic_search(message, k=3) or []
            prompt = f"""
Use the following knowledge base snippets to answer the question.

SNIPPETS:
{docs}

Question: {message}
Answer briefly and clearly. Do not invent facts not supported by the snippets.
""".strip()

            response = client.responses.create(
                model="gpt-4o-mini",
                instructions=instructions,
                input=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            return response.output_text

        # Function calling (tools)
        if "checklist" in m or "todo" in m or "to-do" in message:
            return run_tools_loop(client, message)

        # OpenLibrary

        if (PENDING_BOOKS or []) and m.isdigit():
            idx = int(m)
            if 1 <= idx <= len(PENDING_BOOKS):
                chosen = PENDING_BOOKS[idx - 1]
                title = chosen.get("title") or "Unknown title"
                authors = chosen.get("authors") or []
                author_str = ", ".join(authors[:3]) if authors else "Unknown author"
                year = chosen.get("first_publish_year")
                isbn = chosen.get("isbn")
                key = chosen.get("key")

                details = openlibrary_book_details_by_isbn(isbn) if isbn else {}
                url = openlibrary_best_url(details, fallback_key=key)

                PENDING_BOOKS = []
                PENDING_QUERY = ""

                return _friendly_book_message(title, author_str, year, url)

            return f"Please choose a number between 1 and {len(PENDING_BOOKS)}."

        trigger_book = ("book" in m) or ("books" in m) or ("recommend a book" in m) or ("recommend books" in m)

        if trigger_book:
            query = _clean_book_query(message)

            if len(query) < 2:
                return "Sure — what topic should the book be about? (e.g., music history, singer biography, ocean animals)"

            cands = openlibrary_search_top(query, limit=5) or []
            if not cands:
                return f"I couldn't find any books on OpenLibrary for: {query}"

            PENDING_BOOKS = cands
            PENDING_QUERY = query

            choices = _format_candidates(cands)
            return f"""I found these possible matches on OpenLibrary for: "{query}"

{choices}

Reply with 1–{len(cands)} to pick one, if you see irrelevent books showing up, it is possible that Open Library Metadata does not contain the books you are looking for, you can try another topic or type a more specific query (e.g., "music theory")."""

        response = client.responses.create(
            model="gpt-4o-mini",
            instructions=instructions,
            input=[{"role": "user", "content": message}],
            temperature=0.2
        )
        return response.output_text

    except Exception as e:
        tb = traceback.format_exc()
        print("=== ERROR in chat_fn ===")
        print(tb)
        return f"Error: {type(e).__name__}: {e}\n\nTraceback:\n{tb}"

demo = gr.ChatInterface(fn=chat_fn, title="Assignment Chat")

if __name__ == "__main__":
    demo.launch()
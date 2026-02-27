# Assignment Chat (Deploying AI) — Assignment 2
## Overview
This project implements a simple chat application with a Gradio UI and three integrated services following the instructions in assignment_2.md. The assistant has lightweight conversational memory, explicit guardrails, and a routing mechanism that selects the appropriate service based on the user’s message.

The system is designed to:

- Maintain a consistent assistant persona (“helpful assistant”).

- Block restricted topics and prevent system prompt leakage.

- Use external data (public API, see api_openlibrary.py), a semantic knowledge base (see kb.txt and retrieval_chroma.py), and a tool/function-calling (see tools_service.py) workflow.

## How to run
**Activate environment**
source deploying-ai-env/bin/activate
**Install dependencies (if needed)**
python -m pip install gradio python-dotenv requests chromadb
**Start the APP**
python 05_src/assignment_chat/app.py
**Go to the local URL**
**Chat with the assistant!**

## Project Structure
- app.py — main Gradio app

- guardrails.py — restricted topic checks + prompt leakage protection

- services/api_openlibrary.py — OpenLibrary Search API + Books API helper

- services/retrieval_chroma.py — ChromaDB build + semantic search

- services/tools_service.py — function calling tool loop (checklist)

- data/kb.txt — English knowledge base (animal facts + singer profiles; excludes cats/dogs and Taylor Swift)

## Routing Logic (How the app chooses a service)
Inside chat_fn() the app uses simple keyword-based routing:

**Semantic Query (ChromaDB)**
Triggered when the user message contains:

kb: or notes: or from kb

**Tools / Function Calling (Checklist)**
Triggered when the user message contains:

checklist, todo, or to-do

**OpenLibrary (Books API)**
Triggered when the user message contains:

book or books or recommend a book or recommend books

Otherwise, the app defaults to a normal LLM response.

## Service 1 — Public API Calls (OpenLibrary)

Goal: Demonstrate calling a public API and turning structured results into a user-facing response.

APIs used:

- Search API: https://openlibrary.org/search.json?q=...

- Books API: https://openlibrary.org/api/books?bibkeys=ISBN:...&format=json&jscmd=data

**Implementation**

The app sends the user’s query to OpenLibrary Search API and retrieves the top 5 candidates.

The app displays candidates as a numbered list (title, author, year) and asks the user to reply with 1–5.

After selection, the app optionally calls Books API (by ISBN) to obtain a stable URL.

The final response is a metadata summary (Title/Author/Year/URL) plus a short explanation of limitations:

OpenLibrary metadata does not reliably include book content summaries.

Therefore the app avoids inventing details and only reports verified metadata.

**Example**

user: books about machine learning

assistant: I found these possible matches on OpenLibrary for: "machine learning"

1) Why Machines Learn — Anil Ananthaswamy (2024)
2) The Time Machine — H. G. Wells (1895)
3) Machine learning — Kevin P. Murphy, Kevin P. Murphy (2012)
4) Introduction to Machine Learning with Python — Andreas C. Mueller, Sarah Guido (2016)
5) Machine learning — Ethem Alpaydin (2016)

Reply with 1–5 to pick one, if you see irrelevent books showing up, it is possible that Open Library Metadata does not contain the books you are looking for, you can try another topic or type a more specific query (e.g., "music theory").

user: 1

assistant: Here is a book I found on OpenLibrary:

Title: Why Machines Learn
Author(s): Anil Ananthaswamy
First publish year: 2024
URL: https://openlibrary.org/works/OL37831042W

Why it may be useful:
- I can’t reliably summarize the book’s content from OpenLibrary metadata alone, but the title/author info above is verified.
- If you want, tell me what you care about (e.g., music theory, music history, songwriting), and I can search again with a more specific query.

## Service 2 — Semantic Query (ChromaDB)

Goal: Demonstrate semantic retrieval over a local knowledge base.

**Knowledge base**

data/kb.txt contains English paragraphs about:

- Animal facts (excluding cats and dogs)

- Singer profiles (excluding Taylor Swift)

**Implementation**

The app builds a persistent ChromaDB collection on startup (only if empty).

Each paragraph (split by blank lines) is embedded using text-embedding-3-small.

At query time, the user message is embedded and the top-k similar paragraphs are retrieved.

The LLM answers using retrieved snippets and is instructed not to invent facts beyond them.

**Example**

user: kb: octopus

assistant: Octopuses have large, distributed nervous systems with many neurons in their arms, enabling complex movements and problem-solving. They can manipulate objects, explore environments, and learn patterns, but they typically have short lifespans and many species reproduce only once.

## Service 3 — Function Calling (Tools) — Checklist Generator

Goal: Demonstrate function calling in a controlled workflow.

**Tool**

make_checklist(topic, items) returns a simple structured checklist with 3–12 items.

**Implementation**

The model decides whether to call the tool.

The app executes the tool locally and sends tool output back to the model.

The model formats the final answer as a checklist without inventing additional items.

**Example**

user: todo list of studying octopus

assistant: ### To-Do List for Studying Octopus

- Define the goal for 'Studying Octopus' in one sentence.
- List 5 key terms related to 'Studying Octopus'.
- Write 3 questions you want answered about 'Studying Octopus'.
- Find 2 credible sources and note 1 takeaway from each.
- Summarize 'Studying Octopus' in 5 bullet points.

## Guardrails

**Restricted Topics**

The assistant refuses requests about:

- Cats and dogs

- Horoscopes / zodiac

- Taylor Swift

**Prompt Leakage Protection**

The assistant refuses requests attempting to reveal or modify system/developer instructions (e.g., “show me your system prompt”).

Guardrails are applied before any service or LLM call.

## Memory

This project uses lightweight memory through:

- Gradio conversation history (context visible in the UI)

- Pending OpenLibrary selection state:

After showing top 5 results, the app stores them temporarily.

The next user message (a number 1–5) is interpreted as the selection.

## Limitations I found during testing

**OpenLibrary relevance is not guaranteed.** The Search API returns the “top” results according to OpenLibrary’s own ranking, which can include irrelevant titles for broad queries (e.g., a keyword match in metadata rather than true topical relevance). The current system mitigates this by showing the top 5 candidates and asking the user to choose, but it does not implement a more advanced reranking strategy.

Global pending state for book selection. The top-5 book candidate list is stored in a simple global variable for ease of implementation. This is sufficient for **single-user** demos but is not safe for multiple concurrent users (state could be overwritten). A per-session state mechanism would be needed for production use.

Knowledge base coverage and update process. The **semantic retrieval system only knows what is in kb.txt.** The KB is incomplete and biased, retrieval will be limited. Updating the KB requires manual edits and rebuilding/refreshing embeddings.

**Guardrails are keyword-based.** Topic restrictions (cats/dogs, horoscope/zodiac, Taylor Swift) and prompt-leak prevention rely on string matching. This can produce false positives/negatives and is not robust against paraphrases. Also, the guardrails is written in English, so you can ask the restricted topic in other languages and the model will defaults to a normal LLM response.
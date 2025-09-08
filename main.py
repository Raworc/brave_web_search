#!/usr/bin/env python3
"""
Minimal CLI for Brave Web Search API

Usage:
  python brave_web_search/main.py --q "greek restaurants in san francisco" --count 10 --country us --lang en --table
  python brave_web_search/main.py --q "latest LLM papers" --count 5 --json

Env:
  BRAVE_SEARCH_API_KEY must be set
Docs:
  Endpoint: https://api.search.brave.com/res/v1/web/search
  Auth header: X-Subscription-Token: <API_KEY>
"""

import argparse
import os
import sys
import json
import textwrap
from typing import Any, Dict, List, Optional
import requests

API_URL = "https://api.search.brave.com/res/v1/web/search"

SAFES_SEARCH_MAP = {0: 'off', 1: 'moderate', 2: 'strict'}

def parse_args():
    p = argparse.ArgumentParser(description="CLI for Brave Web Search API")
    p.add_argument("--q", required=True, help="Search query")
    p.add_argument("--count", type=int, default=10, help="Number of results per page, default 10")
    p.add_argument("--offset", type=int, default=0, help="Page offset, default 0")
    p.add_argument("--country", default="us", help="Country code, default us")
    p.add_argument("--lang", default="en", help="Search language, default en")
    p.add_argument("--safesearch", type=int, choices=[0,1,2], default=0, help="SafeSearch level 0 off, 1 moderate, 2 strict")
    p.add_argument("--freshness", choices=["pd", "pw", "pm", "py"], help="Limit results to past day, week, month, year")
    p.add_argument("--spellcheck", type=int, choices=[0,1], default=1, help="Enable spellcheck 1 yes, 0 no")
    p.add_argument("--extra_snippets", type=int, choices=[0,1], default=0, help="Return extra snippets 1 yes, 0 no")
    p.add_argument("--summary", type=int, choices=[0,1], default=0, help="Ask API to return summarizer key when available")
    p.add_argument("--json", action="store_true", help="Print full JSON response")
    p.add_argument("--table", action="store_true", help="Pretty print a compact table of results")
    p.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout seconds")
    p.add_argument("--save", help="Optional path to save raw JSON response")
    return p.parse_args()

def build_params(args) -> Dict[str, Any]:
    params = {
        "q": args.q,
        "count": args.count,
        "offset": args.offset,
        "country": args.country,
        "search_lang": args.lang,
        "safesearch": SAFES_SEARCH_MAP.get(args.safesearch, 'off'),
        "spellcheck": args.spellcheck,
    }
    if args.freshness:
        params["freshness"] = args.freshness
    if args.extra_snippets:
        params["extra_snippets"] = 1
    if args.summary:
        params["summary"] = 1
    return params


def compact_table(web_results: List[Dict[str, Any]]) -> str:
    lines = []
    for i, item in enumerate(web_results, start=1):
        title = item.get("title") or item.get("source", {}).get("title") or ""
        url = item.get("url") or item.get("link") or ""
        snippet = item.get("description") or item.get("snippet") or ""
        snippet = " ".join(snippet.split())
        if len(snippet) > 160:
            snippet = snippet[:157] + "..."
        wrapped = textwrap.fill(snippet, width=92)
        lines.append(f"{i:>2}. {title}\n    {url}\n    {wrapped}")
    return "\n".join(lines)


def extract_web_results(resp_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    # The API returns a top level object with a "results" array for web search
    # Sometimes content may be under "web" then "results" depending on response shape
    if "web" in resp_json and isinstance(resp_json["web"], dict):
        return resp_json["web"].get("results", []) or []
    return resp_json.get("results", []) or []


def main():
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        print("Error: BRAVE_SEARCH_API_KEY is not set", file=sys.stderr)
        sys.exit(1)

    args = parse_args()
    headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}
    params = build_params(args)

    try:
        r = requests.get(API_URL, headers=headers, params=params, timeout=args.timeout)
        r.raise_for_status()
        data = r.json()
    except requests.HTTPError as e:
        print(f"HTTP error: {e} - {getattr(e.response, 'text', '')}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(3)

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    if args.json or not args.table:
        # default to JSON so callers can pipe and parse
        print(json.dumps(data, ensure_ascii=False, indent=2))
        if args.table:
            print("\n---\n")

    if args.table:
        results = extract_web_results(data)
        if not results:
            print("No web results in response")
            return
        print(compact_table(results))


if __name__ == "__main__":
    main()

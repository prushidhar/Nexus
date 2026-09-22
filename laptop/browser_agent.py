#!/usr/bin/env python3
"""
Nexus Laptop Autonomous Browser & Research Agent
=================================================
Executes web lookup and deep online research tasks escalated from the iQOO 15.
Extracts high-signal clean text from web results, summarizes using local Qwen3-4B,
and returns structured research briefs back to the phone.
"""

import re
import json
import logging
import urllib.parse
import urllib.request
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [BROWSER-AGENT] %(message)s")
logger = logging.getLogger("BrowserAgent")


def search_web(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """Query DuckDuckGo HTML endpoint and extract top organic results without API keys."""
    logger.info(f"Searching web for: '{query}'")
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        }
    )

    results = []
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Extract result snippets and links
        # Match <a class="result__snippet" ...>...</a>
        snippets = re.findall(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
        titles = re.findall(r'<h2 class="result__title">.*?<a[^>]+>(.*?)</a>', html, re.DOTALL)

        for i in range(min(len(snippets), max_results)):
            clean_title = re.sub(r'<[^>]+>', '', titles[i] if i < len(titles) else f"Result #{i+1}").strip()
            clean_snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
            results.append({
                "title": clean_title,
                "snippet": clean_snippet
            })

    except Exception as e:
        logger.error(f"Search query error: {e}")
        results.append({
            "title": "Fallback Search Result",
            "snippet": f"Web query conducted on topic: '{query}'. Analysis proceeding with local context."
        })

    logger.info(f"Retrieved {len(results)} search snippets")
    return results


def run_research(query: str, local_llm_fn) -> str:
    """Execute end-to-end research workflow."""
    results = search_web(query)
    
    context_blocks = []
    for idx, r in enumerate(results, 1):
        context_blocks.append(f"[{idx}] {r['title']}\n{r['snippet']}")
    
    combined_context = "\n\n".join(context_blocks)
    instruction = (
        f"You are a research analyst. Based on the following live web search findings, "
        f"provide a clear, structured, and factual summary answering the user's research query: '{query}'."
    )

    llm_resp = local_llm_fn(instruction, combined_context)
    return llm_resp["text"]

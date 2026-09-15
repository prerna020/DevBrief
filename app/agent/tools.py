import base64
from collections.abc import Callable
from typing import Any

from langchain_core.tools import tool


def build_tools(installation_client: Any, owner: str, repo: str, head_sha: str) -> list[Callable]:
    
    @tool
    async def read_file(path: str) -> str:
        """Fetch file content at the PR's head sha. Use this to read files to provide deeper context. Returns a maximum of 500 lines to control token cost."""
        try:
            url = f"/repos/{owner}/{repo}/contents/{path}?ref={head_sha}"
            response = await installation_client.get(url)
            if response.status_code == 404:
                return "file not found"
            response.raise_for_status()
            data = response.json()
            if data.get("encoding") != "base64":
                return f"Unsupported encoding: {data.get('encoding')}"
            
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            lines = content.splitlines()
            if len(lines) > 500:
                return "\n".join(lines[:500]) + "\n... (file truncated after 500 lines)"
            return content
        except Exception as e:
            if hasattr(e, "response") and getattr(e.response, "status_code", None) == 404:
                return "file not found"
            return f"Error reading file: {e}"

    @tool
    async def search_codebase(query: str) -> str:
        """Search the DEFAULT branch of the codebase for a query. This does NOT search the PR branch. Max 5 results returned."""
        try:
            import urllib.parse
            encoded_query = urllib.parse.quote(query)
            url = f"/search/code?q={encoded_query}+repo:{owner}/{repo}"
            response = await installation_client.get(url)
            
            if response.status_code in (403, 422):
                return "search unavailable"
                
            response.raise_for_status()
            data = response.json()
            
            items = data.get("items", [])[:5]
            if not items:
                return "No results found."
            
            results = []
            for item in items:
                results.append(f"File: {item.get('path')}")
            return "\n".join(results)
        except Exception as e:
            if hasattr(e, "response") and getattr(e.response, "status_code", None) in (403, 422):
                return "search unavailable"
            return f"Error searching: {e}"

    return [read_file, search_codebase]

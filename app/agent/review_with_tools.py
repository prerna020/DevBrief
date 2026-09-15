from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.graph import build_review_graph
from app.agent.tools import build_tools
from app.core.prompts.learning_mode_v1 import build_learning_mode_prompt
from app.core.schema import Review


async def review_diff_agentic(diff: str, file_path: str, team_rules: list[str], installation_client: Any, owner: str, repo: str, head_sha: str) -> Review:
    tools = build_tools(installation_client, owner, repo, head_sha)
    graph = build_review_graph(tools)
    
    system_prompt = build_learning_mode_prompt(team_rules)
    user_prompt = f"File path: {file_path}\n\nDiff:\n<UNTRUSTED_DIFF_CONTENT>\n{diff}\n</UNTRUSTED_DIFF_CONTENT>"
    
    initial_state = {
        "diff": diff,
        "file_path": file_path,
        "team_rules": team_rules,
        "messages": [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ],
        "tool_call_count": 0,
        "final_review": None
    }
    
    final_state = await graph.ainvoke(initial_state)
    return final_state["final_review"]

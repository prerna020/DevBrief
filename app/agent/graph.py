import json
import os
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.core.groq_client import create_groq_client
from app.core.schema import REVIEW_JSON_SCHEMA, Review


class AgentState(TypedDict):
    diff: str
    file_path: str
    team_rules: list[str]
    messages: Annotated[list[AnyMessage], add_messages]
    tool_call_count: int
    final_review: Review | None

def build_review_graph(tools: list[Any]):
    model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    # Langchain model
    model = ChatGroq(model=model_name, temperature=0.2).bind_tools(tools)
    tool_node = ToolNode(tools)

    async def analyze(state: AgentState):
        response = await model.ainvoke(state["messages"])
        return {"messages": [response]}

    async def execute_tools(state: AgentState):
        result = await tool_node.ainvoke(state)
        return {"messages": result["messages"], "tool_call_count": state.get("tool_call_count", 0) + 1}

    async def finalize(state: AgentState):
        last_ai_message = ""
        for m in reversed(state["messages"]):
            if getattr(m, "type", "") == "ai" and m.content and isinstance(m.content, str):
                last_ai_message = m.content
                break
        
        client = create_groq_client()
        prompt = f"Here is your analysis of the file {state['file_path']}:\n\n{last_ai_message}\n\nNow output it in the required JSON format as defined by the schema."
        
        completion = await client.chat.completions.create(
            model=model_name,
            temperature=0,
            response_format={"type": "json_schema", "json_schema": {"name": "review", "strict": True, "schema": REVIEW_JSON_SCHEMA}},
            messages=[{"role": "user", "content": prompt}]
        )
        content = completion.choices[0].message.content
        review = Review.model_validate(json.loads(content))
        return {"final_review": review}

    def route_after_analyze(state: AgentState):
        last_msg = state["messages"][-1]
        tool_call_count = state.get("tool_call_count", 0)
        
        if getattr(last_msg, "tool_calls", None):
            if tool_call_count < 3:
                return "execute_tools"
        return "finalize"

    graph = StateGraph(AgentState)
    graph.add_node("analyze", analyze)
    graph.add_node("execute_tools", execute_tools)
    graph.add_node("finalize", finalize)
    
    graph.set_entry_point("analyze")
    graph.add_conditional_edges("analyze", route_after_analyze)
    graph.add_edge("execute_tools", "analyze")
    graph.add_edge("finalize", END)
    
    return graph.compile()

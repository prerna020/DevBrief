from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, ToolCall, ToolMessage
from langchain_core.tools import tool

from app.agent.graph import build_review_graph
from app.core.schema import Review


@pytest.fixture
def mock_tools():
    @tool
    async def read_file(path: str) -> str:
        """Fetch file content."""
        return "mocked file content"

    @tool
    async def search_codebase(query: str) -> str:
        """Search codebase."""
        return "mocked search results"

    return [read_file, search_codebase]

@pytest.mark.asyncio
async def test_agent_graph_tool_loop_and_finalize(mock_tools):
    tool_call = ToolCall(name="read_file", args={"path": "test.py"}, id="call_123")
    
    mock_groq_client = AsyncMock()
    mock_groq_client.chat.completions.create.return_value.choices = [
        AsyncMock(message=AsyncMock(content=Review(issues=[]).model_dump_json()))
    ]

    with patch("app.agent.graph.ChatOpenAI") as MockChatGroq, \
         patch("app.agent.graph.ToolNode.ainvoke", new_callable=AsyncMock) as mock_tool_node, \
         patch("app.agent.graph.create_groq_client", return_value=mock_groq_client):
         
        mock_model = MockChatGroq.return_value.bind_tools.return_value
        mock_model.ainvoke = AsyncMock()
        mock_model.ainvoke.side_effect = [
            AIMessage(content="", tool_calls=[tool_call], id="ai_1"),
            AIMessage(content="Analysis complete.", id="ai_2")
        ]
        
        graph = build_review_graph(mock_tools)
        mock_tool_node.return_value = {"messages": [ToolMessage(content="mocked file content", tool_call_id="call_123", id="tm_1")]}
         
        initial_state = {
            "diff": "test diff",
            "file_path": "test.py",
            "team_rules": [],
            "messages": [AIMessage(content="initial")],
            "tool_call_count": 0,
            "final_review": None
        }
        
        final_state = await graph.ainvoke(initial_state)
        
        assert final_state["tool_call_count"] == 1
        assert isinstance(final_state["final_review"], Review)
        assert mock_model.ainvoke.call_count == 2
        assert mock_tool_node.call_count == 1
        assert mock_groq_client.chat.completions.create.call_count == 1

@pytest.mark.asyncio
async def test_agent_graph_force_stop_at_3(mock_tools):
    tool_call = ToolCall(name="read_file", args={"path": "test.py"}, id="call_123")
    
    mock_groq_client = AsyncMock()
    mock_groq_client.chat.completions.create.return_value.choices = [
        AsyncMock(message=AsyncMock(content=Review(issues=[]).model_dump_json()))
    ]

    with patch("app.agent.graph.ChatOpenAI") as MockChatGroq, \
         patch("app.agent.graph.ToolNode.ainvoke", new_callable=AsyncMock) as mock_tool_node, \
         patch("app.agent.graph.create_groq_client", return_value=mock_groq_client):
         
        mock_model = MockChatGroq.return_value.bind_tools.return_value
        mock_model.ainvoke = AsyncMock()
        mock_model.ainvoke.side_effect = [
            AIMessage(content="", tool_calls=[tool_call], id="ai_1"),
            AIMessage(content="", tool_calls=[tool_call], id="ai_2"),
            AIMessage(content="", tool_calls=[tool_call], id="ai_3"),
            AIMessage(content="", tool_calls=[tool_call], id="ai_4")
        ]
        
        graph = build_review_graph(mock_tools)
        mock_tool_node.side_effect = [
            {"messages": [ToolMessage(content="mocked file content", tool_call_id="call_123", id="tm_1")]},
            {"messages": [ToolMessage(content="mocked file content", tool_call_id="call_123", id="tm_2")]},
            {"messages": [ToolMessage(content="mocked file content", tool_call_id="call_123", id="tm_3")]}
        ]
         
        initial_state = {
            "diff": "test diff",
            "file_path": "test.py",
            "team_rules": [],
            "messages": [AIMessage(content="initial")],
            "tool_call_count": 0,
            "final_review": None
        }
        
        final_state = await graph.ainvoke(initial_state)
        
        assert final_state["tool_call_count"] == 3
        assert isinstance(final_state["final_review"], Review)
        assert mock_model.ainvoke.call_count == 4
        assert mock_tool_node.call_count == 3
        assert mock_groq_client.chat.completions.create.call_count == 1

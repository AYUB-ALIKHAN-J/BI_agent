"""LangGraph agent for Iteration 4: Olist Decision Intelligence Analyst.

The agent uses LangGraph with Ollama (llama3.1) to answer business questions
about e-commerce performance using 6 tools for KPIs, trends, forecasts, etc.
"""

from __future__ import annotations

import os
from typing import TypedDict

from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from olist_bi.agent.tools import (
    get_available_months,
    get_basket_rules,
    get_forecast,
    get_headline_kpis,
    get_monthly_trend,
    get_revenue_by_category,
    get_revenue_by_state,
    get_rfm_segments,
)


def get_model() -> ChatOllama:
    """Get Ollama model from environment or default."""
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    model_name = os.environ.get("OLLAMA_MODEL", "llama3.1")
    return ChatOllama(
        base_url=base_url,
        model=model_name,
        temperature=0.1,
    )


class AgentState(TypedDict):
    """State for the agent graph."""
    messages: list


def call_model(state: AgentState) -> AgentState:
    """Call the LLM."""
    model = get_model()
    tools = [
        get_headline_kpis,
        get_monthly_trend,
        get_revenue_by_category,
        get_revenue_by_state,
        get_available_months,
        get_forecast,
        get_rfm_segments,
        get_basket_rules,
    ]
    model_with_tools = model.bind_tools(tools)
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """Determine if we should continue tool calling or finish."""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END


def run_agent(question: str, thread_id: str = "1") -> str:
    """Run the agent with a question and return the final answer."""
    config = {"configurable": {"thread_id": thread_id}}
    
    input_message = f"""You are an expert business analyst for Olist, a Brazilian e-commerce company.

Answer the following question using the available tools. Be concise and cite your sources.
If you need to use multiple tools, do so sequentially.

Question: {question}

Available tools: headline_kpis, monthly_trend, revenue_by_category, revenue_by_state,
available_months, forecast, rfm_segments, basket_rules"""
    
    # Build the graph
    tools = [
        get_headline_kpis,
        get_monthly_trend,
        get_revenue_by_category,
        get_revenue_by_state,
        get_available_months,
        get_forecast,
        get_rfm_segments,
        get_basket_rules,
    ]
    
    tool_node = ToolNode(tools)
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    
    workflow.add_edge("__start__", "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
    )
    workflow.add_edge("tools", "agent")
    
    checkpointer = MemorySaver()
    
    agent = workflow.compile(checkpointer=checkpointer)
    
    # Run the agent and get the final state
    final_state = agent.invoke(
        {"messages": [{"role": "user", "content": input_message}]},
        config=config,
    )
    
    # Return the content from the final message
    return final_state["messages"][-1].content


if __name__ == "__main__":
    # Test the agent
    question = "What is the current revenue and how has it changed over the last 6 months?"
    answer = run_agent(question)
    print(f"Question: {question}")
    print(f"Answer: {answer}")

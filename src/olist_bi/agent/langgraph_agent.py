"""LangGraph agent for Iteration 4: Olist Decision Intelligence Analyst.

The agent uses LangGraph with Ollama (llama3.1) to answer business questions
about e-commerce performance using 6 tools for KPIs, trends, forecasts, etc.
"""

from __future__ import annotations

import os
import time
import warnings
from typing import TypedDict

# Suppress upstream library deprecation warnings on newer Python versions (e.g. LangSmith on 3.14)
warnings.filterwarnings("ignore", category=DeprecationWarning)

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from olist_bi.agent.logging_handler import TerminalAgentCallbackHandler, TerminalColors
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
from olist_bi.config import get_settings


def get_model() -> BaseChatModel:
    """Factory creating the configured LLM (Ollama or Groq)."""
    settings = get_settings()
    provider = settings.llm_provider

    if provider == "groq":
        from langchain_groq import ChatGroq

        api_key = settings.groq_api_key or os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Please set it in your .env file or environment."
            )
        return ChatGroq(
            api_key=api_key,
            model=settings.groq_model,
            temperature=0.1,
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=0.1,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{provider}'. Supported values: 'ollama', 'groq'."
    )


def call_model(state: MessagesState, config: RunnableConfig | None = None) -> dict:
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
    response = model_with_tools.invoke(state["messages"], config=config)
    return {"messages": [response]}


def should_continue(state: MessagesState) -> str:
    """Determine if we should continue tool calling or finish."""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END


def run_agent(question: str, thread_id: str = "1") -> str:
    """Run the agent with a question and return the final answer."""
    settings = get_settings()
    provider = settings.llm_provider
    model_name = settings.groq_model if provider == "groq" else settings.ollama_model
    callback = TerminalAgentCallbackHandler(provider=provider, model=model_name)
    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": [callback],
    }

    C = TerminalColors
    clean_q = question.split("Question:")[-1].strip() if "Question:" in question else question.strip()
    print(f"\n{C.BOLD}{'=' * 75}{C.RESET}")
    print(f"{C.BOLD}🤖 [AGENT REQUEST]{C.RESET} {clean_q}")
    print(f"   Provider: {C.CYAN}{provider.upper()}{C.RESET} ({model_name}) | Thread: {thread_id}")
    print(f"{C.BOLD}{'=' * 75}{C.RESET}")

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

    workflow = StateGraph(MessagesState)

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
    t0 = time.perf_counter()
    try:
        final_state = agent.invoke(
            {"messages": [{"role": "user", "content": input_message}]},
            config=config,
        )
        elapsed = time.perf_counter() - t0
        tokens_info = f" | Total Tokens: {callback.total_tokens:,}" if callback.total_tokens else ""
        print(f"\n{C.GREEN}✅ [AGENT COMPLETE]{C.RESET} Finished in {elapsed:.2f}s{tokens_info}")
        print(f"{C.BOLD}{'=' * 75}{C.RESET}\n")
        return final_state["messages"][-1].content
    except Exception as e:
        elapsed = time.perf_counter() - t0
        print(f"\n{C.RED}❌ [AGENT FAILED]{C.RESET} Execution failed after {elapsed:.2f}s: {e}")
        print(f"{C.BOLD}{'=' * 75}{C.RESET}\n")
        raise


if __name__ == "__main__":
    # Test the agent
    question = "What is the current revenue and how has it changed over the last 6 months?"
    answer = run_agent(question)
    print(f"Question: {question}")
    print(f"Answer: {answer}")

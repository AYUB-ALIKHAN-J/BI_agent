"""Streamlit Chat tab with Iteration 4: LLM analyst agent.

The agent answers business questions using 6 tools for KPIs, trends, forecasts, etc.
Supports both local Ollama and Docker Ollama (via host.docker.internal).
"""

from __future__ import annotations

import ast

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from olist_bi.agent.langgraph_agent import run_agent
from olist_bi.config import get_settings
from olist_bi.warehouse.connection import WarehouseNotFound

settings = get_settings()
WH = settings.warehouse_path


def format_tool_call(tool_name: str, args: dict) -> str:
    """Format a tool call for display."""
    args_str = ", ".join(f"{k}={v}" for k, v in args.items())
    return f"🔧 **{tool_name}**({args_str})"


def format_tool_response(tool_name: str, response: str) -> str:
    """Format a tool response for display."""
    if len(response) > 500:
        response = response[:500] + "..."
    return f"✅ **{tool_name}** returned {len(response)} chars"


def parse_agent_output(raw: str) -> dict[str, object]:
    """Split agent output into tool calls and the final answer."""
    if not raw:
        return {"tool_calls": [], "answer": ""}

    tool_calls: list[dict[str, object]] = []
    answer_parts: list[str] = []

    for block in [part.strip() for part in raw.split("\n\n") if part.strip()]:
        if block.startswith("tool_call:"):
            part = block[len("tool_call:") :]
            if "|" not in part:
                tool_calls.append({"name": part, "args": {}})
                continue

            tool_name, payload = part.split("|", 1)
            try:
                parsed_payload = ast.literal_eval(payload.strip())
            except (ValueError, SyntaxError):
                parsed_payload = payload.strip()

            tool_calls.append({"name": tool_name.strip(), "args": parsed_payload})
        else:
            answer_parts.append(block)

    return {"tool_calls": tool_calls, "answer": "\n\n".join(answer_parts)}


def render_assistant_message(content: str) -> None:
    """Render the answer first and keep the tool reasoning in a collapsible section."""
    parsed = parse_agent_output(content)

    with st.chat_message("assistant"):
        st.markdown(
            "<div class='assistant-pill'>AI analyst</div>",
            unsafe_allow_html=True,
        )

        answer = parsed["answer"]
        if answer:
            st.markdown(answer)
        elif content:
            st.markdown(content)

        if parsed["tool_calls"]:
            with st.expander("Thinking", expanded=False):
                st.markdown("<div class='thinking-label'>Tool trace</div>", unsafe_allow_html=True)
                for tool in parsed["tool_calls"]:
                    st.markdown(f"### 🔧 {tool['name']}")
                    args = tool.get("args", {})
                    if isinstance(args, dict):
                        st.code(str(args), language="python")
                    elif args:
                        st.markdown(str(args))


def render(wh, start: str, end: str) -> None:
    """Render the Chat tab with the LLM agent."""
    st.subheader("Ask the analyst 🤖")
    st.caption(
        "Ask questions about your e-commerce performance. The agent uses tools to "
        "analyze KPIs, trends, forecasts, segments, and basket rules."
    )
    st.markdown(
        """
        <style>
        .assistant-pill {
            display: inline-block;
            background: rgba(79, 142, 247, 0.14);
            color: #7db3ff;
            border: 1px solid rgba(79, 142, 247, 0.35);
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            margin-bottom: 8px;
        }
        .thinking-label {
            color: #9ba5b4;
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin: 0 0 8px 0;
            font-weight: 700;
        }
        [data-testid="stChatMessage"] {
            background: rgba(26, 29, 38, 0.9);
            border: 1px solid rgba(122, 138, 166, 0.25);
            border-radius: 18px;
            padding: 12px 14px;
            box-shadow: 0 4px 18px rgba(0,0,0,0.08);
        }
        [data-testid="stChatMessage"] > div {
            gap: 6px;
        }
        [data-testid="stExpander"] {
            background: rgba(18, 21, 31, 0.9);
            border: 1px solid rgba(122, 138, 166, 0.25);
            border-radius: 12px;
        }
        .stCodeBlock {
            background: rgba(11, 13, 18, 0.95) !important;
            border-radius: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Show available months and active model provider for context
    try:
        from olist_bi.warehouse import kpis
        months = kpis.available_months(str(wh))
        provider_info = (
            f"Groq ({settings.groq_model})"
            if settings.llm_provider == "groq"
            else f"Ollama ({settings.ollama_model})"
        )
        st.caption(f"📊 Data: {months[0]} to {months[-1]} | 🧠 Engine: `{provider_info}`")
    except (WarehouseNotFound, FileNotFoundError):
        st.warning("Run `olist-bi etl` (or `make etl`) first to build the warehouse.")
        return
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Create a container for chat messages (scrollable)
    chat_container = st.container(height=600, border=False)
    
    # Display chat messages
    with chat_container:
        for i, message in enumerate(st.session_state.messages):
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(message["content"])
            else:
                render_assistant_message(message["content"])
    
    # Fixed bottom input area
    st.markdown(
        """
        <style>
        .chat-input-container {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: white;
            padding: 20px;
            border-top: 1px solid #ddd;
            z-index: 100;
        }
        .chat-input-container .stChatInput {
            max-width: 800px;
            margin: 0 auto;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Chat input at bottom
    with st.container():
        col1, col2 = st.columns([9, 1])
        with col1:
            if prompt := st.chat_input("Ask a question about your data...", key="chat_input"):
                # Add user message
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                # Display user message immediately
                with chat_container:
                    with st.chat_message("user"):
                        st.markdown(prompt)

                # Process with agent
                with chat_container:
                    context = f"""
Current period: {start} to {end}
Available months: {', '.join(months)}
"""
                    full_prompt = f"{context}\n\nQuestion: {prompt}"

                    try:
                        response = run_agent(full_prompt)
                        render_assistant_message(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        err_str = str(e)
                        st.error(f"Error: {e}")
                        if "429" in err_str or "rate limit" in err_str.lower():
                            st.warning(
                                "⚠️ Groq rate limit reached (Tokens or Requests Per Minute limit). "
                                "Please wait a few seconds and try again, or switch to local Ollama (`LLM_PROVIDER=ollama`). "
                                "Check your terminal for detailed API usage logs."
                            )
                        elif settings.llm_provider == "groq":
                            st.info(
                                "Make sure GROQ_API_KEY is set in your .env or environment, "
                                f"and that model '{settings.groq_model}' is accessible on Groq."
                            )
                        else:
                            st.info(
                                "Make sure Ollama is running. For Docker, ensure Ollama is accessible "
                                "at http://localhost:11434 or set OLLAMA_BASE_URL environment variable."
                            )


# Keep the old placeholder for backwards compatibility
def render_placeholder(wh, start: str, end: str) -> None:
    """Old placeholder version (kept for reference)."""
    st.info("The LLM analyst agent is built in Iteration 4.")

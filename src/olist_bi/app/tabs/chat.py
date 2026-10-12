"""Streamlit Chat tab with Iteration 4: LLM analyst agent.

The agent answers business questions using 6 tools for KPIs, trends, forecasts, etc.
Supports both local Ollama and Docker Ollama (via host.docker.internal).
"""

from __future__ import annotations

import streamlit as st

from olist_bi.agent.langgraph_agent import run_agent
from olist_bi.config import get_settings
from olist_bi.warehouse.connection import WarehouseNotFound

settings = get_settings()
WH = settings.warehouse_path


def render(wh, start: str, end: str) -> None:
    """Render the Chat tab with the LLM agent."""
    st.subheader("Ask the analyst 🤖")
    st.caption(
        "Ask questions about your e-commerce performance. The agent uses tools to "
        "analyze KPIs, trends, forecasts, segments, and basket rules."
    )
    
    # Show available months for context
    try:
        from olist_bi.warehouse import kpis
        months = kpis.available_months(str(wh))
        st.caption(f"📊 Data available: {months[0]} to {months[-1]}")
    except (WarehouseNotFound, FileNotFoundError):
        st.warning("Run `olist-bi etl` (or `make etl`) first to build the warehouse.")
        return
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your data..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.status("Analyzing...", expanded=True) as status:
                # Build context from current filters
                context = f"""
Current period: {start} to {end}
Available months: {', '.join(months)}
"""
                
                # Add context to prompt
                full_prompt = f"{context}\n\nQuestion: {prompt}"
                
                try:
                    response = run_agent(full_prompt)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    status.update(label="Analysis complete", state="complete")
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.info(
                        "Make sure Ollama is running. For Docker, ensure Ollama is accessible "
                        "at http://localhost:11434 or set OLLAMA_BASE_URL environment variable."
                    )


# Keep the old placeholder for backwards compatibility
def render_placeholder(wh, start: str, end: str) -> None:
    """Old placeholder version (kept for reference)."""
    st.info("The LLM analyst agent is built in Iteration 4.")

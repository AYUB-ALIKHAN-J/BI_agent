"""Terminal logging handler for Agent execution, Tool calls, and LLM API diagnostics."""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult


class TerminalColors:
    """ANSI color codes for terminal formatting."""

    ENABLED = sys.stdout.isatty() or os.getenv("FORCE_COLOR", "0") == "1"

    CYAN = "\033[96m" if ENABLED else ""
    GREEN = "\033[92m" if ENABLED else ""
    YELLOW = "\033[93m" if ENABLED else ""
    RED = "\033[91m" if ENABLED else ""
    MAGENTA = "\033[95m" if ENABLED else ""
    BLUE = "\033[94m" if ENABLED else ""
    BOLD = "\033[1m" if ENABLED else ""
    DIM = "\033[2m" if ENABLED else ""
    RESET = "\033[0m" if ENABLED else ""


C = TerminalColors


class TerminalAgentCallbackHandler(BaseCallbackHandler):
    """Logs LLM invocations, Tool calls, results, and Groq/Ollama diagnostics to terminal."""

    def __init__(self, provider: str = "ollama", model: str = "") -> None:
        super().__init__()
        self.provider = provider
        self.model = model
        self.step = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.start_time = time.perf_counter()

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID | None = None,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self.step += 1
        model_name = self.model or serialized.get("name", "LLM")
        print(
            f"\n{C.CYAN}🧠 [LLM STEP {self.step}]{C.RESET} "
            f"Reasoning with {C.BOLD}{self.provider.upper()}{C.RESET} ({model_name})..."
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID | None = None,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        # Check token usage in llm_output or generation response_metadata
        token_usage: dict[str, Any] = {}
        if response.llm_output and "token_usage" in response.llm_output:
            token_usage = response.llm_output["token_usage"]

        # Inspect generations for tool calls & response metadata
        for gen_list in response.generations:
            for gen in gen_list:
                msg = getattr(gen, "message", None)
                if msg:
                    # Token usage from response_metadata (common in ChatGroq)
                    meta = getattr(msg, "response_metadata", {}) or {}
                    if not token_usage and "token_usage" in meta:
                        token_usage = meta["token_usage"]

                    # Log tool calls if model requested any
                    tool_calls = getattr(msg, "tool_calls", None)
                    if tool_calls:
                        for tc in tool_calls:
                            name = tc.get("name", "tool")
                            args = tc.get("args", {})
                            formatted_args = ", ".join(f"{k}={v!r}" for k, v in args.items())
                            print(
                                f"{C.YELLOW}🛠️  [TOOL CALL]{C.RESET} "
                                f"{C.BOLD}{name}{C.RESET}({formatted_args})"
                            )

        # Print token usage diagnostics if available
        if token_usage:
            prompt_tokens = token_usage.get("prompt_tokens", 0)
            comp_tokens = token_usage.get("completion_tokens", 0)
            total = token_usage.get("total_tokens", prompt_tokens + comp_tokens)
            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += comp_tokens
            self.total_tokens += total

            print(
                f"{C.DIM}📈 [{self.provider.upper()} USAGE]{C.RESET} "
                f"Prompt: {prompt_tokens:,} | Completion: {comp_tokens:,} | Total: {total:,} tokens"
            )

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID | None = None,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "tool")
        print(f"{C.DIM}⏳ [TOOL EXEC]{C.RESET} Querying warehouse via {C.BOLD}{tool_name}{C.RESET}...")

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID | None = None,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        # Format a clean, non-flooding summary of the tool output
        raw_str = str(output).strip()
        lines = raw_str.splitlines()
        if len(lines) > 4:
            preview = f"{lines[0]} ... [{len(lines)} lines returned]"
        elif len(raw_str) > 160:
            preview = raw_str[:160] + "..."
        else:
            preview = raw_str

        # Replace internal newlines for single-line display
        preview_clean = " ".join(preview.split())
        print(f"{C.GREEN}📊 [TOOL RESULT]{C.RESET} {preview_clean}")

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID | None = None,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        print(f"{C.RED}❌ [TOOL ERROR]{C.RESET} {error}")

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID | None = None,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        err_msg = str(error)
        print(f"\n{C.RED}====================================================================")
        print(f"❌ [LLM API ERROR] Provider: {self.provider.upper()}")
        print(f"===================================================================={C.RESET}")

        # Check for rate limit indicators (e.g. 429, TPM, RPM, quota)
        if "429" in err_msg or "rate limit" in err_msg.lower():
            print(
                f"{C.YELLOW}⚠️  [RATE LIMIT ALERT] Rate limit exceeded on {self.provider.upper()} API!{C.RESET}"
            )
            print(f"   Details: {err_msg}")
            print(
                f"   {C.BOLD}Suggestion:{C.RESET} Wait a few moments before retrying, or configure local Ollama"
            )
            print(f"               by setting LLM_PROVIDER=ollama in your .env file.")
        else:
            print(f"   {C.RED}Error details:{C.RESET} {err_msg}")
        print(f"{C.RED}===================================================================={C.RESET}\n")

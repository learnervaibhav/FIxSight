"""LLM reasoning node for human-readable fault explanation."""

from __future__ import annotations

import os
from typing import cast

from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.state import AgentState


def _build_prompt(state: AgentState) -> str:
    """Create compact diagnostic prompt."""
    vehicle_id = state.get("vehicle_id", "unknown")
    fault_label = state.get("fault_label", "Unknown Fault")
    severity = state.get("severity", "LOW")
    probability = float(state.get("fault_probability", 0.0))
    telemetry_row = state.get("telemetry_row", {})

    telemetry_preview = {
        "engine_rpm": telemetry_row.get("engine_rpm"),
        "coolant_temperature": telemetry_row.get("coolant_temperature"),
        "oil_temperature": telemetry_row.get("oil_temperature"),
        "oil_pressure": telemetry_row.get("oil_pressure"),
        "battery_voltage": telemetry_row.get("battery_voltage"),
    }

    return f"""
You are an automotive predictive-maintenance assistant.

Task:
- Explain the predicted issue
- Explain likely causes
- Suggest what a technician should inspect next
- Keep response practical and under 120 words

Vehicle ID: {vehicle_id}
Predicted Fault: {fault_label}
Severity: {severity}
Fault Probability: {probability:.2%}

Telemetry Snapshot:
{telemetry_preview}
""".strip()


def _fallback_explanation(state: AgentState) -> str:
    """Deterministic explanation if LLM fails."""
    fault_label = str(state.get("fault_label", "Unknown fault"))
    severity = str(state.get("severity", "LOW"))
    probability = float(state.get("fault_probability", 0.0))

    return (
        f"Predicted issue: {fault_label}. "
        f"Severity: {severity}. "
        f"Estimated confidence: {probability:.1%}. "
        "Inspect the related subsystem, confirm with diagnostics, "
        "and schedule service if symptoms persist."
    )


def _get_llm() -> ChatGoogleGenerativeAI:
    """Initialize LangChain Gemini client."""
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    model_name = os.getenv("GOOGLE_MODEL_NAME", "gemini-2.5-flash")

    if not api_key:
        raise ValueError("GOOGLE_API_KEY is missing")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.2,
    )


def llm_reasoner_node(state: AgentState) -> AgentState:
    """Generate natural-language diagnostic reasoning."""
    model_name = os.getenv("GOOGLE_MODEL_NAME", "gemini-2.5-flash")

    try:
        llm = _get_llm()

        prompt = _build_prompt(state)

        response = llm.invoke(prompt)

        text = ""

        if isinstance(response, AIMessage):
            text = str(response.content).strip()
        else:
            text = str(response).strip()

        if not text:
            text = _fallback_explanation(state)

        updated_state = {
            **state,
            "llm_status": "generated",
            "llm_model": model_name,
            "llm_explanation": text,
        }

        return cast(AgentState, updated_state)

    except Exception as exc:
        errors = list(state.get("errors", []))

        errors.append(f"llm_reasoner_node failed: {exc}")

        failed_state = {
            **state,
            "errors": errors,
            "llm_status": "failed",
            "llm_model": model_name,
            "llm_explanation": _fallback_explanation(state),
        }

        return cast(AgentState, failed_state)
"""LLM reasoning node for human-readable fault explanation."""

from __future__ import annotations

import os
from typing import cast

from langchain_core.messages import AIMessage

from app.agents.state import AgentState
from app.core.database import SessionLocal

DEFAULT_MODEL_NAME = "gemini-2.5-flash"


def _build_prompt(state: AgentState) -> str:
    """Create compact diagnostic prompt."""
    vehicle_id = state.get("vehicle_id", "unknown")
    fault_label = state.get("fault_label", "Unknown Fault")
    severity = state.get("severity", "LOW")
    probability = float(state.get("fault_probability", 0.0))
    rul_hours = state.get("rul_hours")
    telemetry_row = state.get("telemetry_row", {})

    telemetry_preview = {
        "engine_rpm": telemetry_row.get("engine_rpm"),
        "coolant_temperature": telemetry_row.get("coolant_temperature"),
        "oil_temperature": telemetry_row.get("oil_temperature"),
        "oil_pressure": telemetry_row.get("oil_pressure"),
        "battery_voltage": telemetry_row.get("battery_voltage"),
        "transmission_temperature": telemetry_row.get("transmission_temperature"),
        "short_term_fuel_trim": telemetry_row.get("short_term_fuel_trim"),
        "egr_position": telemetry_row.get("egr_position"),
        "mass_air_flow": telemetry_row.get("mass_air_flow"),
        "fuel_rate": telemetry_row.get("fuel_rate"),
        "degradation_index": telemetry_row.get("degradation_index"),
    }
    rul_text = f"{float(rul_hours):.0f} hours" if rul_hours is not None else "unknown"

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
Remaining Useful Life: {rul_text}

Telemetry Snapshot:
{telemetry_preview}
""".strip()


def _fallback_explanation(state: AgentState) -> str:
    """Deterministic explanation if LLM is skipped or fails."""
    fault_label = str(state.get("fault_label", "Unknown fault"))
    severity = str(state.get("severity", "LOW"))
    probability = float(state.get("fault_probability", 0.0))

    if not state.get("is_fault", fault_label != "normal"):
        return (
            "All monitored subsystems are operating within normal ranges. "
            f"Fault likelihood is {probability:.1%}. Continue routine maintenance."
        )

    return (
        f"Predicted issue: {fault_label}. "
        f"Severity: {severity}. "
        f"Estimated confidence: {probability:.1%}. "
        "Inspect the related subsystem, confirm with diagnostics, "
        "and schedule service if symptoms persist."
    )


def _get_llm():
    """Initialize LangChain Gemini client."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    model_name = os.getenv("GOOGLE_MODEL_NAME", DEFAULT_MODEL_NAME)

    if not api_key:
        raise ValueError("GOOGLE_API_KEY is missing")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.2,
        timeout=15,  # never stall a simulation tick for long; fallback text is used instead
        max_retries=0,
    )


def llm_configured() -> bool:
    return bool(os.getenv("GOOGLE_API_KEY", "").strip())


def _persist(state: AgentState, text: str) -> None:
    fault_prediction_id = state.get("fault_prediction_id")
    if fault_prediction_id is None:
        return
    from app.services import MLService

    with SessionLocal() as db:
        MLService.update_fault_explanation(db, int(fault_prediction_id), text)


def llm_reasoner_node(state: AgentState) -> AgentState:
    """Generate natural-language diagnostic reasoning.

    Gemini is only called for detected faults (and when enabled/configured) so
    routine telemetry never burns LLM quota.
    """
    model_name = os.getenv("GOOGLE_MODEL_NAME", DEFAULT_MODEL_NAME)
    should_call = state.get("is_fault", False) and state.get("llm_enabled", True) and llm_configured()

    if not should_call:
        hint = state.get("explanation_hint")
        reuse = bool(hint) and state.get("is_fault", False)
        text = str(hint) if reuse else _fallback_explanation(state)
        _persist(state, text)
        return cast(
            AgentState,
            {**state, "llm_status": "reused" if reuse else "skipped", "llm_model": "rules", "llm_explanation": text},
        )

    try:
        response = _get_llm().invoke(_build_prompt(state))

        if isinstance(response, AIMessage):
            content = response.content
            text = (
                " ".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
                if isinstance(content, list)
                else str(content)
            ).strip()
        else:
            text = str(response).strip()

        if not text:
            text = _fallback_explanation(state)

        _persist(state, text)
        return cast(AgentState, {**state, "llm_status": "generated", "llm_model": model_name, "llm_explanation": text})

    except Exception as exc:
        errors = list(state.get("errors", []))
        errors.append(f"llm_reasoner_node failed: {exc}")
        text = _fallback_explanation(state)
        _persist(state, text)

        return cast(
            AgentState,
            {**state, "errors": errors, "llm_status": "failed", "llm_model": model_name, "llm_explanation": text},
        )

# Pydantic data contracts for OpsScout — populated test-by-test.
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DateRange(BaseModel):
    start: str
    end: str


class WeatherSignal(BaseModel):
    date: str
    condition: str
    temperature_c: float
    precipitation_mm: float
    confidence: float = Field(ge=0.0, le=1.0)
    source: str


class EventSignal(BaseModel):
    name: str
    date: str
    estimated_attendance: int | None
    distance_m: float
    category: str
    source: str


class AccommodationSignal(BaseModel):
    date: str
    available_listings: int
    avg_price_usd: float
    occupancy_pressure: Literal["low", "medium", "high", "very_high"]
    source: str


class DemandForecast(BaseModel):
    business_id: str
    forecast_for_date: str
    generated_at: str
    weather: WeatherSignal
    events: list[EventSignal]
    accommodation: AccommodationSignal
    demand_multiplier: float = Field(ge=0.0, le=5.0)
    demand_trend: Literal[
        "spike", "above_normal", "normal", "below_normal", "drop"
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class ReActStep(BaseModel):
    step_index: int
    agent_role: str
    thought: str
    tool_called: str | None
    tool_input: dict | None
    observation: str | None
    is_final: bool = False


class InventoryItem(BaseModel):
    name: str
    current_quantity: float
    unit: str
    suggested_order_quantity: float
    estimated_cost_usd: float | None
    supplier_name: str | None


class StaffingChange(BaseModel):
    action: Literal["add_shift", "extend_shift", "reduce_shift", "cancel_shift"]
    role: str
    count: int
    date: str
    reason: str


class CommunicationDraft(BaseModel):
    channel: Literal["whatsapp", "email", "sms", "instagram_caption"]
    recipient: str
    subject: str | None
    body: str
    urgency: Literal["low", "medium", "high"]


class ActionProposal(BaseModel):
    proposal_id: str
    business_id: str
    proposed_at: str
    forecast: DemandForecast
    inventory_actions: list[InventoryItem]
    staffing_actions: list[StaffingChange]
    communications: list[CommunicationDraft]
    estimated_cost_usd: float | None
    reversible: bool
    approval_required: bool = True
    priority: Literal["low", "medium", "high", "urgent"]
    summary_for_owner: str
    confidence: float = Field(ge=0.0, le=1.0)


class ActionFeedback(BaseModel):
    feedback_id: str
    proposal_id: str
    business_id: str
    submitted_at: str
    rating: Literal["thumbs_up", "thumbs_down"]
    free_text: str | None
    was_accurate: bool | None

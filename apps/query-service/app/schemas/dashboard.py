from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

WidgetType = Literal[
    "metric",
    "line",
    "bar",
    "pie",
    "table",
    "heatmap",
]

class DashboardQuery(BaseModel):
    index: str = Field(default="normalized-logs")
    filters: dict[str, Any] = Field(default_factory=dict)
    aggregation: dict[str, Any] = Field(default_factory=dict)

class DashboardWidget(BaseModel):
    id: str
    type: WidgetType
    title: str
    description: str | None = None
    query: DashboardQuery

class DashboardSpec(BaseModel):
    title: str
    description: str | None = None
    time_range: dict[str, Any] | None = None
    widgets: list[DashboardWidget] = Field(default_factory=list)

class DashboardWidgetData(BaseModel):
    labels: list[str] = Field(default_factory=list)
    values: list[float | int] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)

class ExecutedDashboardWidget(DashboardWidget):
    data: DashboardWidgetData = Field(default_factory=DashboardWidgetData)

class ExecutedDashboard(BaseModel):
    title: str
    description: str | None = None
    time_range: dict[str, Any] | None = None
    widgets: list[ExecutedDashboardWidget] = Field(default_factory=list)

class ExecutedDashboardAgentResult(BaseModel):
    answer: str
    dashboard: ExecutedDashboard

class DashboardAgentResult(BaseModel):
    answer: str
    dashboard: DashboardSpec | ExecutedDashboard

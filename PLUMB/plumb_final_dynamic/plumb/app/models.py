from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

STATUSES = ["VERIFIED","PARTIALLY_VERIFIED","FAILED","INCONCLUSIVE","UNSUPPORTED"]
DEPTH_ORDER = ["CLAIMED","DETECTED","IMPLEMENTED","TESTED","MEASURED","VERIFIED"]

@dataclass
class Evidence:
    evidence_id: str
    analysis_id: str
    requirement_id: str | None
    acceptance_criterion_id: str | None
    kind: str
    title: str
    expected: str | None = None
    observed: str | None = None
    source: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    details: str = ""
    status: str | None = None
    raw: dict[str, Any] | None = None

    def to_dict(self): return asdict(self)

@dataclass
class Requirement:
    requirement_id: str
    title: str
    description: str
    criteria: list[dict[str, Any]]
    implementation_items: list[dict[str, Any]]
    status: str
    depth_percent: float

@dataclass
class Analysis:
    analysis_id: str
    project_name: str
    project_hash: str
    created_at: str
    claim: str
    specification: str
    languages: list[str]
    frameworks: list[str]
    files: list[dict[str, Any]]
    requirements: list[Requirement]
    evidences: list[Evidence]
    findings: list[dict[str, Any]]
    tests: list[dict[str, Any]]
    performance: dict[str, Any]
    mutations: dict[str, Any]
    security: dict[str, Any]
    verdict: str
    score: float
    capability: dict[str, str]
    metrics: dict[str, Any]

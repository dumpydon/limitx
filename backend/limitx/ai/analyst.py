from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GroundedClaim:
    claim: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Analysis:
    summary: str
    claims: tuple[GroundedClaim, ...]
    mode: str = "deterministic"
    disclaimer: str = "Simulation explanation only; not financial advice."

    def as_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "claims": [
                {"claim": claim.claim, "evidence_ids": list(claim.evidence_ids)}
                for claim in self.claims
            ],
            "mode": self.mode,
            "disclaimer": self.disclaimer,
        }


def validate_evidence(analysis: Analysis, valid_ids: set[str]) -> Analysis:
    claims = tuple(
        claim
        for claim in analysis.claims
        if claim.evidence_ids and set(claim.evidence_ids) <= valid_ids
    )
    return Analysis(analysis.summary, claims, analysis.mode, analysis.disclaimer)


class ReplayAnalyst:
    """Rule-based by default; deliberately cannot submit commands or mutate the engine."""

    def analyze(self, question: str, evidence: list[dict[str, Any]]) -> Analysis:
        valid = {f"event:{item['sequence']}" for item in evidence if "sequence" in item}
        trades = [item for item in evidence if item.get("type") == "TRADE_EXECUTED"]
        rejects = [
            item for item in evidence if item.get("type") in {"ORDER_REJECTED", "RISK_REJECTED"}
        ]
        claims: list[GroundedClaim] = []
        if trades:
            volume = sum(int(item["quantity"]) for item in trades)
            largest = max(trades, key=lambda item: int(item["quantity"]))
            claims.append(
                GroundedClaim(
                    f"The inspected window traded {volume} units; its largest execution was "
                    f"{largest['quantity']} units at {largest['price_ticks']} ticks.",
                    (f"event:{largest['sequence']}",),
                )
            )
        if rejects:
            last = rejects[-1]
            claims.append(
                GroundedClaim(
                    f"The latest rejection used reason {last.get('reason', 'unspecified')}.",
                    (f"event:{last['sequence']}",),
                )
            )
        if not claims and evidence:
            last = evidence[-1]
            claims.append(
                GroundedClaim(
                    f"The latest recorded engine event was {last.get('type', 'UNKNOWN')}.",
                    (f"event:{last['sequence']}",),
                )
            )
        analysis = Analysis(
            summary=(
                f"Deterministic replay analysis for: {question.strip() or 'What happened?'} "
                "Claims are limited to cited engine evidence."
            ),
            claims=tuple(claims),
        )
        return validate_evidence(analysis, valid)

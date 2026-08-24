from limitx.ai.analyst import Analysis, GroundedClaim, ReplayAnalyst, validate_evidence


def test_invalid_evidence_claims_are_removed():
    analysis = Analysis("test", (GroundedClaim("unsupported", ("event:999",)),))
    assert validate_evidence(analysis, {"event:1"}).claims == ()


def test_rule_based_analyst_cites_real_events():
    result = ReplayAnalyst().analyze(
        "Why?",
        [{"sequence": 4, "type": "ORDER_REJECTED", "reason": "FOK_NOT_FILLABLE"}],
    )
    assert result.claims[0].evidence_ids == ("event:4",)

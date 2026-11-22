from truth_engine import TruthEngine
from cases.case_001 import get_case


def _engine():
    return TruthEngine(get_case("case_001"))


def test_present_key_evidence_hits_contradiction():
    eng = _engine()
    res = eng.present_evidence("L1", state={"contradictions": []}, evidence_id="E5")
    # 该证据命中预设矛盾 → composure 大跌
    assert res["hit"] is True
    assert res["composure_delta"] <= -25
    assert "contradiction" in res


def test_present_non_key_evidence_no_hit():
    eng = _engine()
    res = eng.present_evidence("L1", state={"contradictions": []}, evidence_id="E2")
    assert res["hit"] is False
    assert res["composure_delta"] == 0


def test_present_wrong_lie_no_hit():
    eng = _engine()
    res = eng.present_evidence("L2", state={"contradictions": []}, evidence_id="E1")
    assert res["hit"] is False
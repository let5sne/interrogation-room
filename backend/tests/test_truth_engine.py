from truth_engine import TruthEngine
from cases.case_001 import get_case


def _engine():
    return TruthEngine(get_case("case_001"))


# --- present_evidence (Task 4) ---
def test_present_key_evidence_hits_contradiction():
    eng = _engine()
    res = eng.present_evidence("L1", state={"contradictions": []}, evidence_id="E5")
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


# --- controller fix: auto-detect + dedupe ---
def test_present_evidence_auto_detects_when_lie_id_none():
    eng = _engine()
    res = eng.present_evidence(None, state={"contradictions": []}, evidence_id="E5")
    assert res["hit"] is True
    assert res["composure_delta"] <= -25


def test_present_evidence_dedupes():
    eng = _engine()
    state = {"contradictions": [{"evidence": "E5", "note": "x"}]}
    res = eng.present_evidence(None, state=state, evidence_id="E5")
    assert res["hit"] is False


# --- Task 5: pressure / clamp / judge ---
def test_pressure_penalty():
    eng = _engine()
    res = eng.pressure(composure=80, has_evidence=False)
    assert res["composure_delta"] < 0
    assert res["lawyer_up"] is False


def test_pressure_without_evidence_triggers_lawyer():
    eng = _engine()
    res = eng.pressure(composure=80, has_evidence=False, pressure_count=2)
    assert res["lawyer_up"] is True


def test_clamp_composure():
    eng = _engine()
    assert eng.clamp(105) == 100
    assert eng.clamp(-5) == 0
    assert eng.clamp(55) == 55


def test_judge_win_on_correct_accusation():
    eng = _engine()
    res = eng.judge(accusation={"culprit": "林晚", "method": "用奖杯重击致死", "motive": "挪用资金被发现在即，杀人灭口"})
    assert res["win"] is True
    assert res["ending"] in ("full_confession", "solved")


def test_judge_lose_on_wrong_culprit():
    eng = _engine()
    res = eng.judge(accusation={"culprit": "管家", "method": "下毒", "motive": "仇杀"})
    assert res["win"] is False
from cases.case_001 import get_case


def test_case_has_valid_lie_evidence_links():
    c = get_case("case_001")
    ev_ids = {e["id"] for e in c["evidence"]}
    lie_ids = {l["lie_id"] for l in c["lies"]}
    for kc in c["key_contradictions"]:
        assert kc["evidence_id"] in ev_ids, f"未知证据 {kc['evidence_id']}"
        assert kc["contradicts_lie"] in lie_ids, f"未知谎言 {kc['contradicts_lie']}"


def test_each_lie_breakable():
    c = get_case("case_001")
    broken = {kc["contradicts_lie"] for kc in c["key_contradictions"]}
    for lie in c["lies"]:
        assert lie["lie_id"] in broken, f"谎言 {lie['lie_id']} 无证据可破"


def test_confession_threshold_sane():
    c = get_case("case_001")
    assert 0 < c["confession_threshold"] < 50
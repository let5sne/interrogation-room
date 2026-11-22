from typing import Optional


class TruthEngine:
    def __init__(self, case: dict):
        self.case = case

    def present_evidence(self, lie_id: Optional[str], state: dict, evidence_id: str) -> dict:
        """玩家出示证据。返回 {hit, composure_delta, contradiction?}。"""
        # 确定性命中：该证据被登记为可证伪该谎言
        hit = False
        note = None
        for kc in self.case["key_contradictions"]:
            if kc["evidence_id"] == evidence_id and kc["contradicts_lie"] == lie_id:
                hit = True
                note = kc["note"]
                break
        if hit:
            return {"hit": True, "composure_delta": -30, "contradiction": note}
        return {"hit": False, "composure_delta": 0}
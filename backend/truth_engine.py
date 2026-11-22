from typing import Optional


class TruthEngine:
    def __init__(self, case: dict):
        self.case = case

    def present_evidence(self, lie_id: Optional[str], state: dict, evidence_id: str) -> dict:
        """玩家出示证据。lie_id 为 None 时自动匹配任意被证伪的谎言。
        返回 {hit, composure_delta, contradiction?}。同一证据不可重复命中。"""
        already = any(
            c.get("evidence") == evidence_id for c in state.get("contradictions", [])
        )
        if already:
            return {"hit": False, "composure_delta": 0, "message": "这条证据你已经出示过了。"}
        for kc in self.case["key_contradictions"]:
            if kc["evidence_id"] != evidence_id:
                continue
            if lie_id is not None and kc["contradicts_lie"] != lie_id:
                continue
            return {"hit": True, "composure_delta": -30, "contradiction": kc["note"]}
        return {"hit": False, "composure_delta": 0}

    def clamp(self, value: int) -> int:
        return max(0, min(100, value))

    def pressure(self, composure: int, has_evidence: bool, pressure_count: int = 0) -> dict:
        """施压。无证据施压会掉镇定且累计；第 3 次无证据施压触发'要求律师'。"""
        delta = -10 if has_evidence else -5
        lawyer_up = (not has_evidence) and (pressure_count + 1 >= 3)
        if lawyer_up:
            delta = -20
        return {"composure_delta": delta, "lawyer_up": lawyer_up}

    def judge(self, accusation: dict) -> dict:
        """指认结算。关键项匹配即判胜。"""
        culprit_ok = accusation.get("culprit") == self.case["culprit"]
        method_ok = any(k in accusation.get("method", "") for k in ["奖杯", "钝器", "重击"])
        motive_ok = any(k in accusation.get("motive", "") for k in ["资金", "挪用", "灭口", "报警"])
        if culprit_ok and (method_ok or motive_ok):
            return {"win": True, "ending": "solved", "reason": "指认成立"}
        return {
            "win": False,
            "ending": "wrong_accusation",
            "reason": "指认与真相不符，嫌疑人被释放，真凶逍遥法外。",
        }
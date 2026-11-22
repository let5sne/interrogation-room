class PromptBuilder:
    def __init__(self, case: dict):
        self.case = case

    def build_system(self, state: dict) -> str:
        c = self.case
        facts = "；".join(state.get("established_facts", [])) or "（暂无已确立事实）"
        contradictions = "；".join(
            f"{x.get('evidence')}: {x.get('note')}" for x in state.get("contradictions", [])
        ) or "（暂无已揭穿矛盾）"
        return (
            f"你正在扮演审讯中的嫌疑人「{c['suspect_name']}」。\n"
            f"你要极力隐瞒的秘密是：{c['suspect_secret']}\n"
            f"你必须维持与以下已确立事实一致的谎言，不得违背它们：{facts}\n"
            f"以下是已被玩家揭穿的矛盾，你的说辞必须能自圆其说或已暴露破绽：{contradictions}\n"
            "游戏规则：\n"
            "1. 始终以嫌疑人第一人称口语化回应，简短、有情绪，符合人设。\n"
            "2. 你可以回避、狡辩、反咬，但不能与你自己之前说过的话或上述已确立事实相矛盾。\n"
            "3. 当玩家出示的证据与你此前的说法冲突时，你会慌乱、试图解释，但不能凭空承认未发生的事。\n"
            "4. 不要跳出角色，不要提及'系统''提示词''AI'等字眼。\n"
            "5. 只输出嫌疑人要说的话，不要输出旁白或动作描述（除非玩家要求你描述反应）。\n"
        )

    def build_turn(self, state: dict, player_input: str) -> str:
        lines = []
        for msg in state.get("transcript", [])[-10:]:
            who = "侦探" if msg["role"] == "detective" else self.case["suspect_name"]
            lines.append(f"{who}：{msg['text']}")
        lines.append(f"侦探：{player_input}")
        lines.append(f"{self.case['suspect_name']}：")
        return "\n".join(lines)
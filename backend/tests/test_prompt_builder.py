from prompt_builder import PromptBuilder
from cases.case_001 import get_case


def test_system_prompt_contains_secret_and_rules():
    pb = PromptBuilder(get_case("case_001"))
    sp = pb.build_system(state={"transcript": [], "established_facts": [], "contradictions": []})
    assert "林晚" in sp
    assert "隐瞒" in sp or "秘密" in sp
    assert "不得" in sp  # 一致性约束存在


def test_user_prompt_includes_history_and_input():
    pb = PromptBuilder(get_case("case_001"))
    state = {
        "transcript": [{"role": "detective", "text": "你最后一次见陈默是什么时候？"},
                       {"role": "suspect", "text": "晚上八点半我就走了。"}],
        "established_facts": [],
        "contradictions": [],
    }
    up = pb.build_turn(state=state, player_input="你撒谎，监控显示你九点还在")
    assert "晚上八点半我就走了" in up
    assert "你撒谎" in up


def test_includes_established_facts():
    pb = PromptBuilder(get_case("case_001"))
    state = {
        "transcript": [],
        "established_facts": ["21:05 林晚的车仍在楼下"],
        "contradictions": [{"evidence": "E5", "note": "监控显示她在场"}],
    }
    sp = pb.build_system(state=state)
    assert "21:05" in sp
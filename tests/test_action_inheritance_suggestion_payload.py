from types import SimpleNamespace

from api.v1.action.service import _build_inheritance_suggestions


def test_build_inheritance_suggestions_uses_idp_content():
    plan = SimpleNamespace(
        goals={"text": "提升项目管理能力，按周复盘关键里程碑"},
        actions={"text": "每周五提交项目复盘并同步风险清单"},
    )

    payload = _build_inheritance_suggestions(plan)

    assert payload["summary"].startswith("建议将")
    assert payload["recommendations"][0]["name"].endswith("完成度")
    assert payload["recommendations"][0]["target_display"] == "100%"
    assert payload["recommendations"][0]["source_goal"] == plan.goals["text"]

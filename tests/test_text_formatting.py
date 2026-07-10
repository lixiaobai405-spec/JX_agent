from utils.text_formatting import markdown_to_plain_text, normalize_markdown_text


def test_normalize_markdown_text_unwraps_json_content():
    raw = '{"content":"### 根因分析\\n\\n1. **销售回款率**\\n- 部分客户付款审批延迟。\\n\\n### 改进建议\\n- 每周三跟进应收账款。"}'

    text = normalize_markdown_text(raw)

    assert text == (
        "### 根因分析\n\n"
        "1. **销售回款率**\n"
        "- 部分客户付款审批延迟。\n\n"
        "### 改进建议\n"
        "- 每周三跟进应收账款。"
    )
    assert '{"content"' not in text
    assert "\\n" not in text


def test_normalize_markdown_text_preserves_markdown_markers():
    raw = "### 根因分析\\n1. **新品铺货率** 达成不足\\n\\n### 改进建议\\n- 锁定重点门店"

    text = normalize_markdown_text(raw)

    assert "### 根因分析" in text
    assert "**新品铺货率**" in text
    assert "- 锁定重点门店" in text
    assert "\\n" not in text


def test_markdown_to_plain_text_unwraps_json_content():
    raw = '{"content":"### 根因分析\\n\\n1. **销售回款率**\\n- 部分客户付款审批延迟。\\n\\n### 改进建议\\n- 每周三跟进应收账款。"}'

    text = markdown_to_plain_text(raw)

    assert text == (
        "根因分析\n\n"
        "1. 销售回款率\n"
        "部分客户付款审批延迟。\n\n"
        "改进建议\n"
        "每周三跟进应收账款。"
    )


def test_markdown_to_plain_text_decodes_escaped_newlines():
    raw = "### 根因分析\\n1. **新品铺货率** 达成不足\\n\\n### 改进建议\\n- 锁定重点门店"

    text = markdown_to_plain_text(raw)

    assert "\\n" not in text
    assert "###" not in text
    assert "**" not in text
    assert "根因分析\n1. 新品铺货率 达成不足" in text


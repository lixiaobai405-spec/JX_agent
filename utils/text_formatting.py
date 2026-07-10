import json
import re


_PREFERRED_TEXT_KEYS = (
    "content",
    "feedback",
    "text",
    "message",
    "root_cause_analysis",
    "improvement_suggestions",
)


def _extract_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in _PREFERRED_TEXT_KEYS:
            nested = value.get(key)
            if nested:
                return _extract_text(nested)
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "\n".join(_extract_text(item) for item in value if item)
    return str(value)


def _unwrap_json_text(text: str) -> str:
    current = text.strip()
    for _ in range(3):
        if not current:
            return ""
        try:
            parsed = json.loads(current)
        except (TypeError, json.JSONDecodeError):
            return current
        next_text = _extract_text(parsed).strip()
        if next_text == current:
            return current
        current = next_text
    return current


def _decode_escaped_newlines(text: str) -> str:
    return (
        text.replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\r", "\n")
        .replace("\\t", " ")
    )


def normalize_markdown_text(value) -> str:
    """Unwrap AI JSON-ish output while preserving readable Markdown."""
    text = _decode_escaped_newlines(_unwrap_json_text(_extract_text(value)))
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"(?<!\n)\n(#{1,6}\s+)", r"\n\n\1", text)
    text = re.sub(r"(?<!\n)\n(\d+\.\s+)", r"\n\n\1", text)
    return text.strip()


def markdown_to_plain_text(value) -> str:
    """Convert AI Markdown/JSON-ish output into readable plain text."""
    text = _decode_escaped_newlines(_unwrap_json_text(_extract_text(value)))
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = []
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue

        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*+]\s+", "", line)
        line = re.sub(r"^\s*>\s?", "", line)
        line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
        line = re.sub(r"__(.*?)__", r"\1", line)
        line = re.sub(r"`([^`]*)`", r"\1", line)
        line = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", line)
        lines.append(line.strip())

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


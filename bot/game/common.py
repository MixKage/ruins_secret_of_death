from __future__ import annotations

from typing import Dict, List

MAX_LOG_LINES = 4
MESSAGE_LIMIT = 4096
INFO_TRUNCATED_LINE = "<i>Справка обрезана.</i>"


def _append_log(state: Dict, message: str) -> None:
    state.setdefault("log", []).append(message)
    state["log"] = state["log"][-MAX_LOG_LINES:]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _percent(value: float, show_percent: bool = True) -> str:
    percent_value = int(round(value * 100))
    return f"{percent_value}%" if show_percent else str(percent_value)


def _trim_lines_to_limit(lines: List[str], limit: int) -> List[str]:
    if limit <= 0:
        return []
    result = []
    current_len = 0
    for line in lines:
        add_len = len(line) + (1 if result else 0)
        if current_len + add_len > limit:
            break
        result.append(line)
        current_len += add_len
    if len(result) < len(lines):
        trunc_line = INFO_TRUNCATED_LINE
        add_len = len(trunc_line) + (1 if result else 0)
        if current_len + add_len <= limit:
            result.append(trunc_line)
    return result

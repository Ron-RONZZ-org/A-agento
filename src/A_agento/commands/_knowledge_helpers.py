from __future__ import annotations

import json
from pathlib import Path

from A import tr_multi, info, success
from A_agento.prompt_loader import load_prompt


def _get_format_prompt(formato: str) -> str:
    return load_prompt(f"generi_{formato}")


def _looks_like_raw_json(content: str) -> bool:
    stripped = content.strip()
    if not stripped:
        return True
    if stripped.startswith("[") and stripped.endswith("]"):
        try:
            data = json.loads(stripped)
            return isinstance(data, list)
        except (json.JSONDecodeError, TypeError):
            pass
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict) and "uuid" in data:
                return True
        except (json.JSONDecodeError, TypeError):
            pass
    return False


def _clean_enc_output(content: str) -> str:
    import re

    if _looks_like_raw_json(content):
        raise ValueError("LLM returned raw tool output instead of generated content")

    fence_pattern = r'```\w*'
    fences = list(re.finditer(fence_pattern, content))
    if len(fences) >= 2:
        first = fences[-2].start()
        last = fences[-1].end()
        after_first = content[first:].split('\n', 1)
        before_last = content[:last].rsplit('\n', 1)
        if len(after_first) > 1 and len(before_last) > 1:
            start_content = first + len(after_first[0]) + 1
            end_content = last - len(before_last[-1]) - 1
            if start_content < end_content:
                content = content[start_content:end_content]
            else:
                content = content[end_content:start_content] if end_content < start_content else ""
    elif len(fences) == 1:
        f = fences[0]
        fence_text = f.group(0)
        is_opening = len(fence_text) > 3
        after_fence = content[f.end():]
        if is_opening:
            content = after_fence.lstrip('\n')
        else:
            content = content[:f.start()].rstrip('\n')

    lines = content.split('\n')
    while lines and lines[0].startswith('#') and not lines[0].startswith('##'):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)

    return '\n'.join(lines).strip()


def _resolve_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for n in range(1, 1000):
        candidate = parent / f"{stem}.{n}{suffix}"
        if not candidate.exists():
            return candidate
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return parent / f"{stem}.{ts}{suffix}"


def _save_to_file(path: Path, content: str, titolo: str = "") -> Path | None:
    import sys as _sys

    final_path = _resolve_unique_path(path)
    final_path.parent.mkdir(parents=True, exist_ok=True)

    if final_path != path:
        info(tr_multi(
            f"{path} jam ekzistas. Konservas kiel {final_path}",
            f"{path} already exists. Saving as {final_path}",
            f"{path} existe déjà. Enregistre comme {final_path}",
        ))

    try:
        with open(str(final_path), "w", encoding="utf-8") as _f:
            _f.write(content)
    except Exception as e:
        _sys.stderr.write(f"[SAVE_ERROR] {type(e).__name__}: {e}\n")
        _sys.stderr.flush()
        raise

    success(
        tr_multi(
            f"Konservita al {final_path}",
            f"Saved to {final_path}",
            f"Enregistré dans {final_path}",
        )
    )
    return final_path


def _build_context_block(topic: str, max_entries: int = 20) -> str:
    try:
        from A_encik.service import get_service

        svc = get_service()
        entries = svc.search_like(topic, limit=max_entries)
        if not entries:
            return ""

        lines: list[str] = []
        for e in entries:
            uid = (e.get("uuid") or "")[:8]
            title = e.get("titolo") or ""
            preview = (e.get("difinio") or "")[:80].replace("\n", " ")
            if uid and title:
                lines.append(f"- {title} (#{uid}): {preview}" if preview else f"- {title} (#{uid})")
        return "\n".join(lines) if lines else ""
    except ImportError:
        return ""
    except Exception:
        return ""

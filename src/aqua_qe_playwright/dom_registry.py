"""DOM knowledge registry — persiste snapshots, diffs e contracts de UI."""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from typing import Any

_TAG_RE = re.compile(r"<[^>]+>")
_H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_ARIA_LABEL_RE = re.compile(r'aria-label="([^"]+)"', re.IGNORECASE)
_ROLE_RE = re.compile(r'role="([^"]+)"', re.IGNORECASE)
_BUTTON_RE = re.compile(r"<button\b[^>]*>(.*?)</button>", re.IGNORECASE | re.DOTALL)
_HEADER_RE = re.compile(r"<th\b[^>]*>(.*?)</th>", re.IGNORECASE | re.DOTALL)
_DATA_TESTID_RE = re.compile(r'data-testid="([^"]+)"', re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class DomRegistrationResult:
    module: str
    change_id: str
    snapshot_path: str
    contract_path: str
    history_path: str
    diff_path: str | None
    detected_screen_name: str | None
    warnings: list[str]


class DomKnowledgeRegistry:
    """Persiste snapshots DOM, histórico de mudanças e contracts compactos."""

    def __init__(self, knowledge_root: Path) -> None:
        self.knowledge_root = knowledge_root
        self.dom_root = knowledge_root / "dom"
        self.index_path = self.dom_root / "index.json"

    def register_snapshot(
        self,
        *,
        module: str,
        html: str,
        source_label: str,
        expected_module: str | None = None,
        story_id: str | None = None,
        screen_name: str | None = None,
        captured_at: datetime | None = None,
    ) -> DomRegistrationResult:
        captured_at = captured_at or datetime.now(UTC)
        module_slug = _slugify(module)
        module_dir = self.dom_root / "modules" / module_slug
        snapshots_dir = module_dir / "snapshots"
        diffs_dir = module_dir / "diffs"
        contracts_dir = module_dir / "contracts"
        locators_dir = module_dir / "locators"
        for d in (snapshots_dir, diffs_dir, contracts_dir, locators_dir):
            d.mkdir(parents=True, exist_ok=True)

        index = self._load_index()
        module_entry = index.setdefault("modules", {}).setdefault(
            module_slug,
            {
                "module": module_slug,
                "created_at": captured_at.date().isoformat(),
                "snapshots": [],
            },
        )

        sequence = len(module_entry["snapshots"]) + 1
        change_id = f"DOM-{module_slug.upper()}-{captured_at:%Y%m%d}-{sequence:03d}"
        detected_screen_name = screen_name or _extract_h1(html)
        normalized_html = normalize_html(html)
        fingerprint = hashlib.sha256(normalized_html.encode("utf-8")).hexdigest()[:16]

        snapshot_filename = f"{change_id}.html"
        snapshot_path = snapshots_dir / snapshot_filename
        snapshot_path.write_text(html, encoding="utf-8")

        warnings: list[str] = []
        if expected_module and _slugify(expected_module) != module_slug:
            warnings.append(
                f"expected_module='{_slugify(expected_module)}' difere do módulo registrado '{module_slug}'"
            )
        if detected_screen_name and not _screen_matches_module(
            detected_screen_name, module_slug
        ):
            warnings.append(
                f"heading='{detected_screen_name}' não coincide com o módulo '{module_slug}'"
            )

        # Diff em relação ao snapshot anterior
        diff_path: Path | None = None
        previous_snapshot = (
            module_entry["snapshots"][-1] if module_entry["snapshots"] else None
        )
        if previous_snapshot:
            old_path = module_dir / previous_snapshot["relative_snapshot_path"]
            if old_path.exists():
                old_normalized = normalize_html(old_path.read_text(encoding="utf-8"))
                diff_lines = list(
                    difflib.unified_diff(
                        old_normalized.splitlines(),
                        normalized_html.splitlines(),
                        fromfile=previous_snapshot["change_id"],
                        tofile=change_id,
                        lineterm="",
                    )
                )
                if diff_lines:
                    diff_path = diffs_dir / f"{change_id}.diff"
                    diff_path.write_text("\n".join(diff_lines) + "\n", encoding="utf-8")

        # Contract DOM
        contract = {
            "module": module_slug,
            "expected_module": _slugify(expected_module) if expected_module else None,
            "story_id": story_id,
            "source_label": source_label,
            "screen_name": screen_name,
            "detected_screen_name": detected_screen_name,
            "latest_change_id": change_id,
            "latest_fingerprint": fingerprint,
            "captured_at": captured_at.isoformat(timespec="seconds"),
            "warnings": warnings,
            "dom_summary": build_dom_summary(html),
        }
        contract_path = contracts_dir / "dom_contract.json"
        contract_path.write_text(
            json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        # Mapa de locators (placeholder na primeira vez) — prioriza data-testid (Playwright)
        locators_path = locators_dir / "locators_map.json"
        if not locators_path.exists():
            data_testid_attrs = _DATA_TESTID_RE.findall(html)[:20]
            suggested = [
                {"name": f"LOC_{attr.upper().replace('-', '_')}", "selector": f'[data-testid="{attr}"]'}
                for attr in data_testid_attrs
            ]
            locators_path.write_text(
                json.dumps(
                    {
                        "module": module_slug,
                        "source": "manual-curation-required",
                        "selector_strategy": "getByRole() > getByTestId() > getByLabel() > getByText() > locator('[data-testid=\"...\"]')",
                        "notes": [
                            "Preencher com locators aprovados pelo time a partir do DOM snapshot.",
                            "Priorizar getByRole() e getByTestId() quando disponíveis.",
                            "Usar formato: LOC_{ELEMENTO_UPPER} = '[data-testid=\"...\"]'",
                        ],
                        "suggested_from_dom": suggested,
                        "locators": [],
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

        # Histórico em Markdown
        history_path = diffs_dir / "history.md"
        history_entry = _build_history_entry(
            change_id=change_id,
            captured_at=captured_at,
            fingerprint=fingerprint,
            snapshot_relative_path=(Path("snapshots") / snapshot_filename).as_posix(),
            source_label=source_label,
            story_id=story_id,
            detected_screen_name=detected_screen_name,
            warnings=warnings,
            diff_relative_path=(Path("diffs") / diff_path.name).as_posix()
            if diff_path
            else None,
        )
        previous_history = (
            history_path.read_text(encoding="utf-8")
            if history_path.exists()
            else "# Histórico de mudanças DOM\n"
        )
        history_path.write_text(
            previous_history.rstrip() + "\n\n" + history_entry, encoding="utf-8"
        )

        # Atualiza índice global
        module_entry["snapshots"].append(
            {
                "change_id": change_id,
                "captured_at": captured_at.isoformat(timespec="seconds"),
                "source_label": source_label,
                "story_id": story_id,
                "fingerprint": fingerprint,
                "relative_snapshot_path": (
                    Path("snapshots") / snapshot_filename
                ).as_posix(),
                "relative_diff_path": (Path("diffs") / diff_path.name).as_posix()
                if diff_path
                else None,
                "detected_screen_name": detected_screen_name,
                "warnings": warnings,
            }
        )
        index["updated_at"] = captured_at.date().isoformat()
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        return DomRegistrationResult(
            module=module_slug,
            change_id=change_id,
            snapshot_path=str(snapshot_path),
            contract_path=str(contract_path),
            history_path=str(history_path),
            diff_path=str(diff_path) if diff_path else None,
            detected_screen_name=detected_screen_name,
            warnings=warnings,
        )

    def _load_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {"version": 1, "updated_at": None, "modules": {}}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def load_current_contract(self, module: str) -> dict | None:
        module_slug = _slugify(module)
        contract_path = (
            self.dom_root / "modules" / module_slug / "contracts" / "dom_contract.json"
        )
        if not contract_path.exists():
            return None
        return json.loads(contract_path.read_text(encoding="utf-8"))


def normalize_html(html: str) -> str:
    lines: list[str] = []
    for raw_line in re.sub(r">\s*<", ">\n<", html).splitlines():
        compact = _WHITESPACE_RE.sub(" ", raw_line).strip()
        if compact:
            lines.append(compact)
    return "\n".join(lines)


def build_dom_summary(html: str) -> dict[str, Any]:
    return {
        "heading_h1": _extract_h1(html),
        "aria_labels": _unique_preserve_order(_ARIA_LABEL_RE.findall(html))[:20],
        "roles": _unique_preserve_order(_ROLE_RE.findall(html))[:20],
        "buttons": _extract_button_texts(html)[:20],
        "table_headers": _extract_table_headers(html)[:20],
        "data_testid_attrs": _unique_preserve_order(_DATA_TESTID_RE.findall(html))[:20],
    }


def _build_history_entry(
    *,
    change_id: str,
    captured_at: datetime,
    fingerprint: str,
    snapshot_relative_path: str,
    source_label: str,
    story_id: str | None,
    detected_screen_name: str | None,
    warnings: list[str],
    diff_relative_path: str | None,
) -> str:
    lines = [
        f"## {change_id}",
        f"- captured_at: {captured_at.isoformat(timespec='seconds')}",
        f"- fingerprint: `{fingerprint}`",
        f"- snapshot: `{snapshot_relative_path}`",
        f"- source_label: `{source_label}`",
    ]
    if story_id:
        lines.append(f"- story_id: `{story_id}`")
    if detected_screen_name:
        lines.append(f"- detected_screen_name: `{detected_screen_name}`")
    if diff_relative_path:
        lines.append(f"- diff: `{diff_relative_path}`")
    if warnings:
        lines.append("- warnings:")
        lines.extend(f"  - {w}" for w in warnings)
    return "\n".join(lines)


def _extract_h1(html: str) -> str | None:
    match = _H1_RE.search(html)
    return (_strip_tags(match.group(1)) or None) if match else None


def _extract_button_texts(html: str) -> list[str]:
    return _unique_preserve_order(
        [t for t in (_strip_tags(m) for m in _BUTTON_RE.findall(html)) if t]
    )


def _extract_table_headers(html: str) -> list[str]:
    return _unique_preserve_order(
        [t for t in (_strip_tags(m) for m in _HEADER_RE.findall(html)) if t]
    )


def _strip_tags(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", unescape(_TAG_RE.sub(" ", value))).strip()


def _slugify(value: str | None) -> str:
    if not value:
        return ""
    cleaned = value.lower()
    for src, tgt in {
        "á": "a",
        "à": "a",
        "â": "a",
        "ã": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }.items():
        cleaned = cleaned.replace(src, tgt)
    return re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for v in values:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result


def _screen_matches_module(screen_name: str, module_slug: str) -> bool:
    screen_tokens = _normalized_tokens(screen_name)
    module_tokens = _normalized_tokens(module_slug)
    if not screen_tokens or not module_tokens:
        return False
    overlap = screen_tokens & module_tokens
    return len(overlap) >= max(1, min(len(screen_tokens), len(module_tokens)) - 1)


def _normalized_tokens(value: str) -> set[str]:
    tokens = [t for t in _slugify(value).split("_") if t]
    normalized: set[str] = set()
    for token in tokens:
        normalized.add(token)
        if token.endswith("s") and len(token) > 4:
            normalized.add(token[:-1])
    return normalized

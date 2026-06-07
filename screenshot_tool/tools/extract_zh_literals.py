import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PACK = ROOT / "locales" / "zh_CN.json"

EXCLUDE_DIRS = {
    "venv",
    "build",
    "dist",
    "dist_installer",
    "installer_output",
    "__pycache__",
    "locales",
}
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
HTML_RE = re.compile(r"<[^>]+>")
THIS_SCRIPT = "tools/extract_zh_literals.py"


def contains_chinese(text: str) -> bool:
    return bool(text and CHINESE_RE.search(text))


def clean_string(s: str) -> str:
    return s.replace("\r\n", "\n").strip()


def is_probably_html(text: str) -> bool:
    return "<html" in text.lower() or "<body" in text.lower() or len(HTML_RE.findall(text)) >= 2


def is_technical_literal(path: Path, text: str, source_line: str) -> bool:
    low = text.lower()
    line_low = source_line.lower()

    if is_probably_html(text):
        return True
    if low.startswith("<a href="):
        return True
    if re.match(r"^[a-z]:\\", low):
        return True
    if low.endswith((".png", ".ico", ".jpg", ".jpeg", ".svg", ".exe", ".dll", ".zip", ".json")):
        return True
    if "print(" in line_low or "logger." in line_low or "logging." in line_low:
        return True
    if "response.text" in text:
        return True
    if any(token in low for token in ("traceback", "stdout", "stderr", "debug")):
        return True
    if path.as_posix() == THIS_SCRIPT:
        return True
    return False


class Extractor(ast.NodeVisitor):
    def __init__(self):
        self.results = []
        self._parents = {}

    def visit(self, node):
        for child in ast.iter_child_nodes(node):
            self._parents[child] = node
        return super().visit(node)

    def _is_docstring(self, node: ast.AST) -> bool:
        return isinstance(self._parents.get(node), ast.Expr)

    def _add(self, text: str, lineno: int):
        text = clean_string(text)
        if contains_chinese(text):
            self.results.append((lineno, text))

    def visit_Constant(self, node: ast.Constant):
        parent = self._parents.get(node)
        if isinstance(node.value, str) and not self._is_docstring(node) and not isinstance(parent, ast.JoinedStr):
            self._add(node.value, getattr(node, "lineno", 0))
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                try:
                    expr = ast.unparse(value.value)
                except Exception:
                    expr = "expr"
                parts.append("{" + expr + "}")
        self._add("".join(parts), getattr(node, "lineno", 0))
        self.generic_visit(node)


def make_key(file_key: str, line_no: int, index: int, text: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "_", file_key).strip("_").lower()
    snippet = re.sub(r"\s+", " ", text)[:24]
    snippet = re.sub(r"[^\w\u4e00-\u9fff]+", "_", snippet).strip("_")
    if snippet:
        return f"{base}.l{line_no:04d}.{index:02d}.{snippet}"
    return f"{base}.l{line_no:04d}.{index:02d}"


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)


def extract_file(path: Path):
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    extractor = Extractor()
    extractor.visit(tree)
    lines = source.splitlines()

    dedup = []
    seen = set()
    for lineno, text in extractor.results:
        entry_key = (lineno, text)
        if entry_key in seen:
            continue
        seen.add(entry_key)
        source_line = lines[lineno - 1] if 0 < lineno <= len(lines) else ""
        dedup.append((lineno, text, source_line))
    return dedup


def main():
    mapping = {}
    py_files = sorted(p for p in ROOT.rglob("*.py") if not should_skip(p))
    for path in py_files:
        rel = path.relative_to(ROOT).as_posix()
        if rel == THIS_SCRIPT:
            continue

        entries = extract_file(path)
        if not entries:
            continue

        file_key = rel[:-3].replace("/", ".")
        for idx, (lineno, text, source_line) in enumerate(entries, start=1):
            if is_technical_literal(Path(rel), text, source_line):
                continue
            key = make_key(file_key, lineno, idx, text)
            mapping[key] = text

    OUTPUT_PACK.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PACK.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Locale entries: {len(mapping)} -> {OUTPUT_PACK}")


if __name__ == "__main__":
    main()

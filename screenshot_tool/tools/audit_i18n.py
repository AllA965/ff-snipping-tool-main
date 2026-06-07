import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ROOT / 'locales'
ZH = LOCALES / 'zh_CN.json'
LANG_RE = re.compile(r'[\u4e00-\u9fff]')
BAD_CHAR = '�'
SKIP_DIRS = {'venv','build','dist','dist_installer','installer_output','__pycache__','.git'}


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def find_bad_source_strings():
    results = []
    for path in ROOT.rglob('*.py'):
        if should_skip(path):
            continue
        try:
            src = path.read_text(encoding='utf-8')
        except Exception:
            continue
        try:
            tree = ast.parse(src)
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value
                if BAD_CHAR in text:
                    results.append({
                        'path': str(path.relative_to(ROOT)).replace('\\', '/'),
                        'line': getattr(node, 'lineno', 0),
                        'text': text,
                    })
    return results


def find_hardcoded_chinese():
    results = []
    for path in ROOT.rglob('*.py'):
        if should_skip(path) or 'locales' in path.parts or 'tools' in path.parts:
            continue
        try:
            src = path.read_text(encoding='utf-8')
        except Exception:
            continue
        try:
            tree = ast.parse(src)
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value.strip()
                if not text or not LANG_RE.search(text):
                    continue
                if BAD_CHAR in text:
                    continue
                results.append({
                    'path': str(path.relative_to(ROOT)).replace('\\', '/'),
                    'line': getattr(node, 'lineno', 0),
                    'text': text,
                })
    return results


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        return {'__error__': str(e)}


def flatten(obj, prefix=''):
    out = {}
    if not isinstance(obj, dict):
        return out
    for k, v in obj.items():
        key = f'{prefix}.{k}' if prefix else str(k)
        if isinstance(v, dict):
            out.update(flatten(v, key))
        else:
            out[key] = v
    return out


def audit_locales():
    report = {'files': {}, 'missing_vs_zh': {}}
    zh = load_json(ZH)
    zh_flat = flatten(zh) if '__error__' not in zh else {}
    zh_keys = set(zh_flat.keys())
    for p in sorted(LOCALES.glob('*.json')):
        data = load_json(p)
        if '__error__' in data:
            report['files'][p.name] = {'valid': False, 'error': data['__error__']}
            continue
        flat = flatten(data)
        bad_keys = [k for k in flat.keys() if BAD_CHAR in k]
        bad_values = [k for k, v in flat.items() if isinstance(v, str) and BAD_CHAR in v]
        report['files'][p.name] = {
            'valid': True,
            'entries': len(flat),
            'bad_keys': bad_keys[:100],
            'bad_values': bad_values[:100],
        }
        if p.name != 'zh_CN.json' and zh_keys:
            missing = sorted(list(zh_keys - set(flat.keys())))
            report['missing_vs_zh'][p.name] = missing[:300]
    return report


def main():
    out = {
        'bad_source_strings': find_bad_source_strings(),
        'hardcoded_chinese': find_hardcoded_chinese()[:500],
        'locale_audit': audit_locales(),
    }
    out_path = ROOT / 'i18n_audit_report.json'
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(out_path)
    print(f"bad_source_strings={len(out['bad_source_strings'])}")
    print(f"hardcoded_chinese={len(out['hardcoded_chinese'])}")


if __name__ == '__main__':
    main()

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / 'locales'
ZH = json.loads((BASE / 'zh_CN.json').read_text('utf-8'))
EN = json.loads((BASE / 'en.json').read_text('utf-8'))
KO = json.loads((BASE / 'ko.json').read_text('utf-8'))

# support both {{var}} and {var} styles
PH = re.compile(r"\{\{\s*[^{}]+\s*\}\}|\{[^{}]+\}")

def ph(s: str):
    return set(PH.findall(s)) if isinstance(s, str) else set()


def check(name: str, data: dict):
    if not isinstance(data, dict):
        return {'ok': False, 'error': f'root not dict: {type(data)}'}
    missing = [k for k in ZH if k not in data]
    extra = [k for k in data if k not in ZH]
    mism = [k for k in ZH if k in data and ph(ZH[k]) != ph(data[k])]
    same = sum(1 for k in ZH if k in data and data[k] == ZH[k])
    return {
        'ok': True,
        'keys_zh': len(ZH),
        'keys_lang': len(data),
        'missing': len(missing),
        'extra': len(extra),
        'placeholder_mismatch': len(mism),
        'same_as_zh': same,
        'mismatch_sample': mism[:10],
    }


print('en', check('en', EN))
print('ko', check('ko', KO))

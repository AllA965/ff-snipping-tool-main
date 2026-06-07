import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / 'locales'
ZH = json.loads((BASE/'zh_CN.json').read_text('utf-8'))
EN = json.loads((BASE/'en.json').read_text('utf-8'))
KO = json.loads((BASE/'ko.json').read_text('utf-8'))

PH = re.compile(r"\{\{\s*[^{}]+\s*\}\}|\{[^{}]+\}")

def ph(s: str):
    return set(PH.findall(s)) if isinstance(s,str) else set()

mism = [k for k in ZH if k in EN and ph(ZH[k])!=ph(EN[k])]
print('mismatch_count', len(mism))
for k in mism:
    print('KEY', k)
    print(' zh', ZH[k])
    print(' en', EN[k])
    ko_val = KO.get(k)
    if isinstance(ko_val, str):
        print(' ko', repr(ko_val))
    else:
        print(' ko', ko_val)
    print(' zh_ph', sorted(ph(ZH[k])))
    print(' en_ph', sorted(ph(EN[k])))
    print('---')

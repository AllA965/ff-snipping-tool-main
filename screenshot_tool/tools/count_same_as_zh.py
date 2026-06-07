import json
from pathlib import Path
base = Path(__file__).resolve().parents[1] / 'locales'
ko = json.loads((base/'ko.json').read_text('utf-8'))
zh = json.loads((base/'zh_CN.json').read_text('utf-8'))
same = sum(1 for k,v in zh.items() if k in ko and ko[k] == v)
print('keys zh', len(zh), 'ko', len(ko), 'same_as_zh', same)

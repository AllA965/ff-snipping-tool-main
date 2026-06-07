import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / 'locales'
ZH_PATH = BASE / 'zh_CN.json'
EN_PATH = BASE / 'en.json'
KO_PATH = BASE / 'ko.json'

PH_RE = re.compile(r"\{[^{}]+\}")

def placeholders(s: str):
    return set(PH_RE.findall(s)) if isinstance(s, str) else set()


def main():
    zh = json.loads(ZH_PATH.read_text('utf-8'))
    en = json.loads(EN_PATH.read_text('utf-8'))
    ko = json.loads(KO_PATH.read_text('utf-8')) if KO_PATH.exists() else {}

    # Build mapping en_text -> key (only when unique)
    en_text_to_key = {}
    dup = set()
    for k, v in en.items():
        if not isinstance(v, str):
            continue
        if v in en_text_to_key:
            dup.add(v)
        else:
            en_text_to_key[v] = k
    for v in dup:
        en_text_to_key.pop(v, None)

    # Create new ko by copying en strings (as requested: translate by referencing English)
    new_ko = {}
    for k, vzh in zh.items():
        ven = en.get(k)
        if isinstance(ven, str) and ven:
            new_ko[k] = ven
        else:
            # fallback: if old ko has something and placeholders match zh, keep it
            old = ko.get(k)
            if isinstance(old, str) and placeholders(old) == placeholders(vzh):
                new_ko[k] = old
            else:
                # last resort: zh
                new_ko[k] = vzh

        # Ensure placeholder set matches zh
        if placeholders(new_ko[k]) != placeholders(vzh):
            # try to use en if it matches placeholders
            if isinstance(ven, str) and placeholders(ven) == placeholders(vzh):
                new_ko[k] = ven
            else:
                new_ko[k] = vzh

    KO_PATH.write_text(json.dumps(new_ko, ensure_ascii=False, indent=2), 'utf-8')

    same_as_zh = sum(1 for k, v in zh.items() if new_ko.get(k) == v)
    same_as_en = sum(1 for k, v in en.items() if new_ko.get(k) == v)
    print('rebuild_done')
    print('keys', len(new_ko), 'same_as_zh', same_as_zh, 'same_as_en', same_as_en)


if __name__ == '__main__':
    main()

import json
import shutil
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
TRASH = BASE / "_trash"
TRASH.mkdir(exist_ok=True)

PH_RE = re.compile(r"\{[^{}]+\}")

def placeholders(s: str):
    return set(PH_RE.findall(s)) if isinstance(s, str) else set()


def load_json(p: Path):
    return json.loads(p.read_text("utf-8"))


def main():
    zh_path = BASE / "zh_CN.json"
    if not zh_path.exists():
        raise SystemExit("Missing zh_CN.json in locales dir")
    zh = load_json(zh_path)
    zh_keys = set(zh.keys())

    keep = set(["zh_CN.json", "zh_TW.json", "en.json", "ja.json"])

    moved = []
    repaired = []
    deleted = []

    # 1) Move obviously non-locale artifacts
    for p in BASE.iterdir():
        if p.is_dir():
            continue
        name = p.name
        if name.startswith("_") and name not in keep:
            # move to trash
            dest = TRASH / name
            if dest.exists():
                dest.unlink()
            shutil.move(str(p), str(dest))
            moved.append(name)

    # 2) Validate and repair locale jsons (except zh_CN)
    for p in BASE.glob("*.json"):
        if p.name == "zh_CN.json":
            continue
        try:
            data = load_json(p)
        except Exception:
            # corrupted json -> move to trash
            dest = TRASH / p.name
            if dest.exists():
                dest.unlink()
            shutil.move(str(p), str(dest))
            moved.append(p.name)
            continue

        if not isinstance(data, dict):
            # not a dict -> trash
            dest = TRASH / p.name
            if dest.exists():
                dest.unlink()
            shutil.move(str(p), str(dest))
            moved.append(p.name)
            continue

        # repair: ensure keys match zh, and placeholders match
        changed = False

        # remove extra keys
        extra = [k for k in data.keys() if k not in zh_keys]
        for k in extra:
            data.pop(k, None)
            changed = True

        # add missing keys (fallback to zh)
        missing = [k for k in zh_keys if k not in data]
        for k in missing:
            data[k] = zh[k]
            changed = True

        # fix placeholder mismatches by copying zh string
        for k in zh_keys:
            vzh = zh[k]
            v = data.get(k)
            if placeholders(vzh) != placeholders(v):
                data[k] = vzh
                changed = True

        if changed:
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
            repaired.append(p.name)

        keep.add(p.name)

    # 3) Move *.issues.json into trash (optional) — keep only if you want them
    for p in BASE.glob("*.issues.json"):
        dest = TRASH / p.name
        if dest.exists():
            dest.unlink()
        shutil.move(str(p), str(dest))
        moved.append(p.name)

    # 4) Move any other files (non-json) to trash
    for p in BASE.iterdir():
        if p.is_dir():
            continue
        if p.suffix.lower() != ".json":
            if p.name == "clean_locales.py":
                continue
            dest = TRASH / p.name
            if dest.exists():
                dest.unlink()
            shutil.move(str(p), str(dest))
            moved.append(p.name)

    print("Repaired:", len(repaired), repaired)
    print("Moved to _trash:", len(moved))


if __name__ == "__main__":
    main()

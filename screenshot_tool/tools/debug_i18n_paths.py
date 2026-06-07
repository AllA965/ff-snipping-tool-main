import os
from core import i18n as m

print('ROOT', m.ROOT)
print('LOCALES_DIR', m.LOCALES_DIR)
print('LOCALES_DIR.exists', m.LOCALES_DIR.exists())
print('list locales files', [p.name for p in m.LOCALES_DIR.glob('*.json')][:5])

mgr = m._MANAGER
mgr._load_locale_packs()
print('after _load_locale_packs: packs', len(mgr.locale_packs))
print('available_codes', sorted(mgr.available_codes)[:20])

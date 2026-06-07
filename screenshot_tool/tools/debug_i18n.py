from core import i18n

print('before init: available_codes_count', len(i18n.get_available_language_codes()))
print('before init: available_codes', i18n.get_available_language_codes())
print('supported_count', len(i18n.get_supported_languages()))
print('current_before', i18n.current_language())

print('apply ko ->', i18n.apply_language('ko', app=None))
print('current_after', i18n.current_language())
print('after apply: available_codes_count', len(i18n.get_available_language_codes()))
print('after apply: available_codes', i18n.get_available_language_codes())

from __future__ import annotations

import json
import locale
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Pattern

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QAction, QPainter
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QRadioButton,
    QStatusBar,
    QSystemTrayIcon,
    QTabWidget,
    QWidget,
)

ROOT = Path(__file__).resolve().parents[1]
LOCALES_DIR = ROOT / "locales"
SOURCE_LANG = "zh_CN"
SOURCE_PACK_PATH = LOCALES_DIR / f"{SOURCE_LANG}.json"
_PLACEHOLDER_RE = re.compile(r"\{[^{}]+\}")

SUPPORTED_LANGUAGES = [
    ("auto", "Auto (System)"),
    ("zh_CN", "简体中文"),
    ("zh_TW", "繁體中文"),
    ("en", "English"),
    ("ar", "العربية"),
    ("bn", "বাংলা"),
    ("de", "Deutsch"),
    ("es", "Español"),
    ("fa", "فارسی"),
    ("fr", "Français"),
    ("ha", "Hausa"),
    ("he", "עברית"),
    ("hi", "हिन्दी"),
    ("id", "Bahasa Indonesia"),
    ("it", "Italiano"),
    ("ja", "日本語"),
    ("jv", "Basa Jawa"),
    ("ko", "한국어"),
    ("ms", "Bahasa Melayu"),
    ("nl", "Nederlands"),
    ("pl", "Polski"),
    ("pt", "Português"),
    ("pt_BR", "Português (Brasil)"),
    ("ru", "Русский"),
    ("sw", "Kiswahili"),
    ("ta", "தமிழ்"),
    ("th", "ไทย"),
    ("tl", "Filipino"),
    ("tr", "Türkçe"),
    ("uk", "Українська"),
    ("ur", "اردو"),
    ("vi", "Tiếng Việt"),
]
LANG_NAME_BY_CODE = {code: name for code, name in SUPPORTED_LANGUAGES}
_LANG_CHOOSABLE = {code for code, _ in SUPPORTED_LANGUAGES if code != "auto"}


@dataclass(frozen=True)
class _TemplateRule:
    key: str
    template: str
    regex: Pattern[str]


class _I18NManager:
    def __init__(self):
        self.language = SOURCE_LANG
        self.source_pack: Dict[str, str] = {}
        self.active_pack: Dict[str, str] = {}
        self.locale_packs: Dict[str, Dict[str, str]] = {}
        self.available_codes: set[str] = set()
        self.text_to_keys: Dict[str, List[str]] = {}
        self.template_rules: List[_TemplateRule] = []
        self.translation_cache: Dict[tuple[str, str], str] = {}

    def _flatten_locale_object(self, obj: dict, prefix: str = "", acc: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        if acc is None:
            acc = {}
        for key, value in obj.items():
            if not isinstance(key, str):
                continue
            path_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self._flatten_locale_object(value, path_key, acc)
            elif isinstance(value, str):
                acc[path_key] = value
        return acc

    def _load_json(self, path: Path) -> Dict[str, str]:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        return self._flatten_locale_object(data)

    def _load_locale_packs(self):
        packs: Dict[str, Dict[str, str]] = {}
        search_dirs: List[Path] = []
        if LOCALES_DIR.exists():
            search_dirs.append(LOCALES_DIR)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidate = Path(meipass) / "locales"
            if candidate.exists():
                search_dirs.append(candidate)
        exe = getattr(sys, "executable", None)
        if exe:
            candidate = Path(exe).resolve().parent / "locales"
            if candidate.exists():
                search_dirs.append(candidate)
        seen = set()
        deduped: List[Path] = []
        for d in search_dirs:
            rp = str(d.resolve())
            if rp in seen:
                continue
            seen.add(rp)
            deduped.append(d)
        search_dirs = deduped
        for loc_dir in search_dirs:
            for path in sorted(loc_dir.glob("*.json")):
                if path.name.endswith(".issues.json"):
                    continue
                code = path.stem
                data = self._load_json(path)
                if data:
                    packs[code] = data
        source_pack = packs.get(SOURCE_LANG)
        if not source_pack:
            source_pack = self._load_json(SOURCE_PACK_PATH)
            if source_pack:
                packs[SOURCE_LANG] = source_pack
        self.locale_packs = packs
        self.source_pack = packs.get(SOURCE_LANG, {})
        self.available_codes = set(packs.keys())

    def _detect_system_language(self) -> str:
        candidates = [locale.getlocale()[0], os.environ.get("LC_ALL"), os.environ.get("LANG")]
        for value in candidates:
            if isinstance(value, str) and value:
                return value
        return SOURCE_LANG

    def _normalize_language(self, language: Optional[str]) -> str:
        if not language or language == "auto":
            language = self._detect_system_language()
        normalized = str(language).replace("-", "_").split(".")[0]
        lowered = normalized.lower()
        alias_map = {
            "zh": "zh_CN",
            "zh_cn": "zh_CN",
            "zh_hans": "zh_CN",
            "zh_tw": "zh_TW",
            "zh_hant": "zh_TW",
            "en_us": "en",
            "en_gb": "en",
        }
        if lowered in alias_map:
            return alias_map[lowered]
        if normalized in _LANG_CHOOSABLE:
            return normalized
        if "_" in normalized:
            base = normalized.split("_", 1)[0].lower()
            if base in _LANG_CHOOSABLE:
                return base
        if lowered in _LANG_CHOOSABLE:
            return lowered
        if lowered.startswith("zh"):
            return SOURCE_LANG
        return SOURCE_LANG

    def _build_template_regex(self, template: str) -> Optional[Pattern[str]]:
        placeholders = _PLACEHOLDER_RE.findall(template)
        if not placeholders:
            return None
        pattern = re.escape(template)
        for index, placeholder in enumerate(placeholders):
            pattern = pattern.replace(re.escape(placeholder), f"(?P<p{index}>.+?)", 1)
        return re.compile(rf"^{pattern}$", re.DOTALL)

    def _build_reverse_index(self):
        mapping: Dict[str, List[str]] = {}
        for _, pack in self.locale_packs.items():
            for key, text in pack.items():
                keys = mapping.setdefault(text, [])
                if key not in keys:
                    keys.append(key)
        self.text_to_keys = mapping

    def _build_template_rules(self):
        rules: List[_TemplateRule] = []
        seen: set[tuple[str, str]] = set()
        for _, pack in self.locale_packs.items():
            for key, template in pack.items():
                token = (key, template)
                if token in seen:
                    continue
                seen.add(token)
                regex = self._build_template_regex(template)
                if regex is None:
                    continue
                rules.append(_TemplateRule(key=key, template=template, regex=regex))
        rules.sort(key=lambda item: len(item.template), reverse=True)
        self.template_rules = rules

    def initialize(self, language: Optional[str] = "auto"):
        self._load_locale_packs()
        self._build_reverse_index()
        self._build_template_rules()
        normalized = self._normalize_language(language)
        self.language = normalized
        if normalized == SOURCE_LANG:
            self.active_pack = self.source_pack
        else:
            self.active_pack = self.locale_packs.get(normalized, {})
        self.translation_cache = {}

    def _lookup(self, key: str, fallback: str) -> str:
        if self.language == SOURCE_LANG:
            return self.source_pack.get(key, fallback)
        return self.active_pack.get(key, fallback)

    def _render_with_captures(self, template: str, captures: List[str]) -> str:
        if not captures:
            return template
        index = 0
        def _replace(match: re.Match[str]) -> str:
            nonlocal index
            if index >= len(captures):
                return match.group(0)
            value = captures[index]
            index += 1
            return value
        return _PLACEHOLDER_RE.sub(_replace, template)

    def translate(self, text):
        if not isinstance(text, str) or not text:
            return text
        cache_key = (self.language, text)
        cached = self.translation_cache.get(cache_key)
        if cached is not None:
            return cached
        # 优先：按完整文本匹配
        keys = self.text_to_keys.get(text)
        if keys:
            for key in keys:
                if key in self.active_pack:
                    translated = self.active_pack[key]
                    self.translation_cache[cache_key] = translated
                    return translated
            if self.language == SOURCE_LANG:
                translated = self.source_pack.get(keys[0], text)
                self.translation_cache[cache_key] = translated
                return translated
        # 次级：模板匹配
        for rule in self.template_rules:
            match = rule.regex.match(text)
            if not match:
                continue
            if self.language == SOURCE_LANG:
                translated_template = self.source_pack.get(rule.key, rule.template)
            else:
                translated_template = self.active_pack.get(rule.key)
                if translated_template is None:
                    continue
            captures = [match.group(name) for name in sorted(match.groupdict().keys())]
            translated = self._render_with_captures(translated_template, captures)
            self.translation_cache[cache_key] = translated
            return translated
        # 兜底1：将文本作为键直接查找（支持语言包中以中文原文为键的情况）
        if self.language != SOURCE_LANG:
            direct = self.active_pack.get(text)
            if isinstance(direct, str):
                self.translation_cache[cache_key] = direct
                return direct
        else:
            direct = self.source_pack.get(text)
            if isinstance(direct, str):
                self.translation_cache[cache_key] = direct
                return direct
        # 兜底2：去除前导图标或表情后再次尝试（例如 "📁 新任务" -> "新任务"）
        if " " in text:
            prefix, tail = text.split(" ", 1)
            if tail and tail != text:
                alt_cache_key = (self.language, tail)
                alt = self.translation_cache.get(alt_cache_key)
                if alt is None:
                    # 复用完整流程的部分逻辑进行一次简化查找
                    alt_keys = self.text_to_keys.get(tail)
                    if alt_keys:
                        for key in alt_keys:
                            if key in self.active_pack:
                                translated = self.active_pack[key]
                                # 若回退匹配得到的翻译不以符号开头，则补回原始图标前缀
                                try:
                                    first = translated[:1]
                                    has_leading_symbol = first and unicodedata.category(first).startswith("So")
                                except Exception:
                                    has_leading_symbol = False
                                if not has_leading_symbol and prefix:
                                    translated = f"{prefix} {translated}"
                                self.translation_cache[alt_cache_key] = translated
                                self.translation_cache[cache_key] = translated
                                return translated
                    direct_alt = self.active_pack.get(tail) if self.language != SOURCE_LANG else self.source_pack.get(tail)
                    if isinstance(direct_alt, str):
                        try:
                            first = direct_alt[:1]
                            has_leading_symbol = first and unicodedata.category(first).startswith("So")
                        except Exception:
                            has_leading_symbol = False
                        out = direct_alt if has_leading_symbol or not prefix else f"{prefix} {direct_alt}"
                        self.translation_cache[alt_cache_key] = out
                        self.translation_cache[cache_key] = out
                        return out
                # 继续：按“路径最后一段”匹配（例如 *.新任务）
                leaf = tail
                pack = self.source_pack if self.language == SOURCE_LANG else self.active_pack
                for k, v in pack.items():
                    try:
                        if k.rsplit(".", 1)[-1] == leaf:
                            try:
                                first = v[:1]
                                has_leading_symbol = first and unicodedata.category(first).startswith("So")
                            except Exception:
                                has_leading_symbol = False
                            out = v if has_leading_symbol or not prefix else f"{prefix} {v}"
                            self.translation_cache[cache_key] = out
                            return out
                    except Exception:
                        continue
        # 兜底3：直接按“路径最后一段”匹配原文本
        leaf = text
        pack = self.source_pack if self.language == SOURCE_LANG else self.active_pack
        for k, v in pack.items():
            try:
                if k.rsplit(".", 1)[-1] == leaf:
                    self.translation_cache[cache_key] = v
                    return v
            except Exception:
                continue
        self.translation_cache[cache_key] = text
        return text


_MANAGER = _I18NManager()
_PATCHED = False
_ORIGINALS = {}
_EVENT_FILTER = None


def tr(text):
    return _MANAGER.translate(text)


def current_language() -> str:
    return _MANAGER.language


def get_supported_languages() -> List[Dict[str, object]]:
    return [
        {"code": code, "name": name, "available": True if code == "auto" else code in _MANAGER.available_codes}
        for code, name in SUPPORTED_LANGUAGES
    ]


def get_available_language_codes() -> List[str]:
    return sorted(_MANAGER.available_codes)


def is_language_available(code: str) -> bool:
    return code in _MANAGER.available_codes


def _patch_method(cls, method_name, wrapper_builder):
    key = f"{cls.__name__}.{method_name}"
    if key in _ORIGINALS:
        return
    original = getattr(cls, method_name)
    _ORIGINALS[key] = original
    setattr(cls, method_name, wrapper_builder(original))


def _translate_first_str(args):
    args_list = list(args)
    for idx, value in enumerate(args_list):
        if isinstance(value, str) and value:
            args_list[idx] = tr(value)
            break
    return tuple(args_list)


def _wrap_init_with_text(original_init):
    def wrapped(self, *args, **kwargs):
        args = _translate_first_str(args)
        for key in ("text", "title", "caption", "label"):
            if isinstance(kwargs.get(key), str) and kwargs[key]:
                kwargs[key] = tr(kwargs[key])
        return original_init(self, *args, **kwargs)
    return wrapped


def _wrap_set_text(original_method):
    def wrapped(self, text):
        if isinstance(text, str) and text:
            text = tr(text)
        return original_method(self, text)
    return wrapped


def _wrap_set_title(original_method):
    def wrapped(self, title):
        if isinstance(title, str) and title:
            title = tr(title)
        return original_method(self, title)
    return wrapped


def _wrap_show_message(original_method):
    def wrapped(self, message, timeout=0):
        if isinstance(message, str) and message:
            message = tr(message)
        return original_method(self, message, timeout)
    return wrapped


def _wrap_first_string_arg_method(original_method):
    def wrapped(self, *args):
        args = _translate_first_str(args)
        return original_method(self, *args)
    return wrapped


def _wrap_add_items(original_method):
    def wrapped(self, texts):
        if isinstance(texts, list):
            texts = [tr(item) if isinstance(item, str) else item for item in texts]
        return original_method(self, texts)
    return wrapped


def _wrap_draw_text(original_method):
    def wrapped(self, *args):
        if not args:
            return original_method(self, *args)
        new_args = list(args)
        changed = False
        for idx, value in enumerate(new_args):
            if isinstance(value, str) and value:
                new_value = tr(value)
                if new_value != value:
                    changed = True
                new_args[idx] = new_value
        if changed:
            return original_method(self, *tuple(new_args))
        return original_method(self, *args)
    return wrapped


def install_qt_text_patches():
    global _PATCHED
    if _PATCHED:
        return
    init_patch_classes = [QLabel, QPushButton, QCheckBox, QRadioButton, QAction, QGroupBox, QDockWidget, QMenu]
    for cls in init_patch_classes:
        _patch_method(cls, "__init__", _wrap_init_with_text)
    _patch_method(QWidget, "setWindowTitle", _wrap_set_title)
    _patch_method(QWidget, "setToolTip", _wrap_set_text)
    _patch_method(QLabel, "setText", _wrap_set_text)
    _patch_method(QAbstractButton, "setText", _wrap_set_text)
    _patch_method(QAction, "setText", _wrap_set_text)
    _patch_method(QAction, "setToolTip", _wrap_set_text)
    _patch_method(QAction, "setStatusTip", _wrap_set_text)
    _patch_method(QGroupBox, "setTitle", _wrap_set_title)
    _patch_method(QMenu, "setTitle", _wrap_set_title)
    _patch_method(QLineEdit, "setPlaceholderText", _wrap_set_text)
    _patch_method(QStatusBar, "showMessage", _wrap_show_message)
    _patch_method(QSystemTrayIcon, "setToolTip", _wrap_set_text)
    _patch_method(QComboBox, "addItem", _wrap_first_string_arg_method)
    _patch_method(QComboBox, "insertItem", _wrap_first_string_arg_method)
    _patch_method(QComboBox, "setItemText", _wrap_first_string_arg_method)
    _patch_method(QComboBox, "addItems", _wrap_add_items)
    _patch_method(QTabWidget, "addTab", _wrap_first_string_arg_method)
    _patch_method(QTabWidget, "insertTab", _wrap_first_string_arg_method)
    _patch_method(QTabWidget, "setTabText", _wrap_first_string_arg_method)
    _patch_method(QPainter, "drawText", _wrap_draw_text)
    _PATCHED = True


def _translate_widget_text(widget: QWidget):
    try:
        title = widget.windowTitle()
        if title:
            widget.setWindowTitle(title)
    except Exception:
        pass
    if hasattr(widget, "text") and hasattr(widget, "setText"):
        try:
            text = widget.text()
            if isinstance(text, str) and text:
                widget.setText(text)
        except Exception:
            pass
    if hasattr(widget, "toolTip") and hasattr(widget, "setToolTip"):
        try:
            tooltip = widget.toolTip()
            if isinstance(tooltip, str) and tooltip:
                widget.setToolTip(tooltip)
        except Exception:
            pass
    if isinstance(widget, QLineEdit):
        try:
            placeholder = widget.placeholderText()
            if placeholder:
                widget.setPlaceholderText(placeholder)
        except Exception:
            pass
    if isinstance(widget, QComboBox):
        try:
            for i in range(widget.count()):
                current = widget.itemText(i)
                if current:
                    widget.setItemText(i, current)
        except Exception:
            pass
    if isinstance(widget, QTabWidget):
        try:
            for i in range(widget.count()):
                current = widget.tabText(i)
                if current:
                    widget.setTabText(i, current)
        except Exception:
            pass


def translate_widget_tree(root: QObject):
    if isinstance(root, QWidget):
        _translate_widget_text(root)
        for child in root.findChildren(QWidget):
            _translate_widget_text(child)
    if isinstance(root, QWidget):
        for action in root.findChildren(QAction):
            try:
                text = action.text()
                if text:
                    action.setText(text)
                tooltip = action.toolTip()
                if tooltip:
                    action.setToolTip(tooltip)
                status_tip = action.statusTip()
                if status_tip:
                    action.setStatusTip(status_tip)
            except Exception:
                continue


def refresh_all_widgets(app=None):
    app = app or QApplication.instance()
    if app is None:
        return
    for widget in app.topLevelWidgets():
        translate_widget_tree(widget)
        widget.update()


class _I18nEventFilter(QObject):
    def eventFilter(self, watched: QObject, event: QEvent):
        if event.type() in (QEvent.Type.Show, QEvent.Type.Polish):
            translate_widget_tree(watched)
        return False


def install_app_filter(app):
    global _EVENT_FILTER
    if app is None:
        return
    if _EVENT_FILTER is None:
        _EVENT_FILTER = _I18nEventFilter(app)
        app.installEventFilter(_EVENT_FILTER)
    refresh_all_widgets(app)


def apply_language(language: Optional[str] = "auto", app=None) -> str:
    _MANAGER.initialize(language)
    install_qt_text_patches()
    install_app_filter(app)
    refresh_all_widgets(app)
    return _MANAGER.language


def init_i18n(language: Optional[str] = "auto", app=None) -> str:
    return apply_language(language, app)

import json
import os
import sys


_FALLBACK_CONFIG = {
    "title_presets": [
        "\u667a\u80fd\u529e\u516c\u52a9\u624b [F9/Ctrl+Alt+H \u9690\u85cf]",
    ],
    "theme_presets": {
        "\u9ed8\u8ba4": {
            "bg": "#F0F0F0",
            "fg": "#000000",
            "entry_bg": "#FFFFFF",
            "accent": "#0078D4",
            "keyword": "#0000FF",
            "string": "#A31515",
            "comment": "#008000",
            "style": "normal",
        }
    },
    "font_presets": {
        "VS Code \u9ed8\u8ba4": "Consolas, 'Courier New', monospace",
    },
    "websites": [
        ["GitHub", "https://github.com"],
    ],
}


def _config_path():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "autofish", "config.json")
    return os.path.join(os.path.dirname(__file__), "config.json")


def load_config():
    path = _config_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    merged = dict(_FALLBACK_CONFIG)
    merged.update({k: v for k, v in data.items() if v is not None})
    return merged

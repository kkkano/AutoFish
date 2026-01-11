import os
import sys


def app_root():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def resource_path(relative_path):
    return os.path.join(app_root(), relative_path)

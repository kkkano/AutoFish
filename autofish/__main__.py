import sys

from . import browser_kernel
from .app import main as app_main


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--browser-kernel":
        browser_kernel.main(sys.argv[2:])
        return
    app_main()


if __name__ == "__main__":
    main()

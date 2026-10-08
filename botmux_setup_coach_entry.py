"""Console entry point bundled beside the windowed Seele application."""

import sys

from botmux_setup_coach import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

"""Frozen as a separate one-file executable by all release builds."""
from app_update import main

if __name__ == "__main__":
    raise SystemExit(main())

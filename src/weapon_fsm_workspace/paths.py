"""Editable weapon assets and profile paths, independent of the working directory."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_ROOT = PROJECT_ROOT / "assets"
PROFILES_ROOT = ASSETS_ROOT / "profiles"


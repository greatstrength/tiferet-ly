"""Tiferet-Ly Version and Global Exports"""

# *** exports

# ** app
# Export the main package objects.
# Use a try-except block to avoid import errors on build systems.
try:
    from .domain import (
        Grammar,
        ProductionRule,
        SimpleProductionRule,
        ComplexProductionRule,
        TokenRule,
        SimpleTokenRule,
        ComplexTokenRule,
    )
except Exception as e:
    import os, sys
    # Only print warning if TIFERET_LY_SILENT_IMPORTS is not set to a truthy value
    if not os.getenv('TIFERET_LY_SILENT_IMPORTS'):
        print(f"Warning: Failed to import Tiferet-Ly core modules: {e}", file=sys.stderr)
    pass

# *** version

__version__ = '1.0.0a5'

#!/usr/bin/env python3
"""
Akku SDK v4.0 - Blender Entry Script

This script is designed to be called by Blender's --python flag.
Arguments are passed after -- separator and parsed safely.

Usage:
  blender --background --python akku_sdk/run.py -- <prompt> <style> <poly_level> <output_path> [gender] [body_type] [use_remesh] [equipment]
"""

import sys
import os

# Add parent directory to path for imports
_script_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_script_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Now import and run main
from akku_sdk.main import main

if __name__ == "__main__":
    main()

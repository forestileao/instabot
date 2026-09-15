import os
import sys

# Ensure the repository root is importable so tests can do
# `from insta_bot.src.insta_bot import InstaBot` regardless of how
# pytest is invoked (e.g. from a CI runner or a subdirectory).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

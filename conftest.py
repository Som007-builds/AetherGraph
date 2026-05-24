# conftest.py  — place this in the project ROOT (same level as agents/, graph/, etc.)
# Adds the project root to sys.path so pytest can find all packages
# regardless of where pytest is invoked from.

import sys
from pathlib import Path

# Insert project root at the front of sys.path
ROOT = Path(__file__).parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
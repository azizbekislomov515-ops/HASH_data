"""Select the headless Qt platform before GUI test modules are imported."""

import os


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

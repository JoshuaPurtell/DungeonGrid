"""DungeonGrid OpenEnv package."""

from .env import DungeonGridEnvironment, DungeonGridEnv
from .models import DungeonGridAction, DungeonGridObservation, DungeonGridState, DungeonGridStep

__version__ = "0.1.0a0"

# Compatibility aliases for early NanoCoop integration code that used the old
# prototype name before the standalone package was split out.
TorchGridEnvironment = DungeonGridEnvironment
TorchGridEnv = DungeonGridEnv
TorchGridAction = DungeonGridAction
TorchGridObservation = DungeonGridObservation
TorchGridState = DungeonGridState
TorchGridStep = DungeonGridStep

__all__ = [
    "__version__",
    "DungeonGridEnvironment",
    "DungeonGridEnv",
    "DungeonGridAction",
    "DungeonGridObservation",
    "DungeonGridState",
    "DungeonGridStep",
    "TorchGridEnvironment",
    "TorchGridEnv",
    "TorchGridAction",
    "TorchGridObservation",
    "TorchGridState",
    "TorchGridStep",
]

"""DungeonGrid OpenEnv package."""

from .action_contracts import DungeonGridActionType, DungeonGridDirection, DungeonGridTargetKind
from .contracts import dungeongrid_act_schema, dungeongrid_rules, dungeongrid_rules_schema
from .env import DungeonGridEnvironment, DungeonGridEnv
from .models import DungeonGridAction, DungeonGridObservation, DungeonGridPlanResult, DungeonGridState, DungeonGridStep

__version__ = "0.1.0a6"

# Compatibility aliases for early NanoCoop integration code that used the old
# prototype name before the standalone package was split out.
TorchGridEnvironment = DungeonGridEnvironment
TorchGridEnv = DungeonGridEnv
TorchGridAction = DungeonGridAction
TorchGridObservation = DungeonGridObservation
TorchGridPlanResult = DungeonGridPlanResult
TorchGridState = DungeonGridState
TorchGridStep = DungeonGridStep

__all__ = [
    "__version__",
    "DungeonGridEnvironment",
    "DungeonGridEnv",
    "DungeonGridAction",
    "DungeonGridObservation",
    "DungeonGridPlanResult",
    "DungeonGridState",
    "DungeonGridStep",
    "DungeonGridActionType",
    "DungeonGridDirection",
    "DungeonGridTargetKind",
    "dungeongrid_act_schema",
    "dungeongrid_rules",
    "dungeongrid_rules_schema",
    "TorchGridEnvironment",
    "TorchGridEnv",
    "TorchGridAction",
    "TorchGridObservation",
    "TorchGridPlanResult",
    "TorchGridState",
    "TorchGridStep",
]

"""
Akku SDK v3.6 - AI-Powered 3D Character Generation
Modular architecture with context-independent operations
"""

import sys
import os

sdk_path = os.path.dirname(os.path.abspath(__file__))
if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

from .core import AkkuConfig, AkkuLogger, MeshStats, StepResult, ErrorReport
from .tools import ToolRegistry, tool, StyleAnalyzer, MeshAnalyzer
from .mesh import MeshTools, UndoManager, BooleanRemeshTools
from .shader import StylizedShaderSystem, StylizedShaderParams, MaterialSystem
from .body import BodyTypeSystem, BodyTypeParams, BodyTypePresets
from .kitbash import KitbashLibrary, KitbashEquipper, SemanticPart, SocketInfo
from .rigging import AutoWeightTransfer, WeightTransferResult
from .finalize import (
    FinalizePipeline, MeshOptimizer, MaterialOptimizer,
    DecimateEngine, MeshJoiner, LODGenerator,
    PlatformTarget, PlatformProfile, PLATFORM_PROFILES
)
from .handlers import FBXHandler, GLBHandler
from .main import (
    clear_scene, import_base_mesh, apply_body_type,
    apply_shader, equip_part, equip_set,
    finalize, export_glb, auto_rig_all, list_parts,
    execute_plan, run_cli
)

__version__ = "3.6.0"
__all__ = [
    "AkkuConfig", "AkkuLogger", "MeshStats", "StepResult", "ErrorReport",
    "ToolRegistry", "tool", "StyleAnalyzer", "MeshAnalyzer",
    "MeshTools", "UndoManager", "BooleanRemeshTools",
    "StylizedShaderSystem", "StylizedShaderParams", "MaterialSystem",
    "BodyTypeSystem", "BodyTypeParams", "BodyTypePresets",
    "KitbashLibrary", "KitbashEquipper", "SemanticPart", "SocketInfo",
    "AutoWeightTransfer", "WeightTransferResult",
    "FinalizePipeline", "MeshOptimizer", "MaterialOptimizer",
    "DecimateEngine", "MeshJoiner", "LODGenerator",
    "PlatformTarget", "PlatformProfile", "PLATFORM_PROFILES",
    "FBXHandler", "GLBHandler",
    "clear_scene", "import_base_mesh", "apply_body_type",
    "apply_shader", "equip_part", "equip_set",
    "finalize", "export_glb", "auto_rig_all", "list_parts",
    "execute_plan", "run_cli"
]

AkkuLogger.info(f"Akku SDK v{__version__} loaded")

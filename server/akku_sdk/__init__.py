"""
Akku SDK v3.7 - Modular Low-Poly Character Generation Toolkit

Modules:
- core: Configuration, Logging, Error Handling
- tools: Tool Registry, Style Analyzer, Mesh Analyzer
- mesh: Mesh Operations, Undo System, Boolean/Remesh
- shader: GLB-Compatible Material System
- body: Body Type System with Direct Mesh Deformation
- kitbash: Semantic Component Library with Direct Bone Parenting
- rigging: Auto Weight Transfer System
- finalize: Game Engine Optimization Pipeline
- handlers: FBX Import, GLB Export, Mesh Freezing
- procedural: Procedural Humanoid Generation (no Mixamo dependency)
- bmesh_tools: Low-level BMesh Direct Manipulation Tools
"""

import sys
import os

_package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _package_dir not in sys.path:
    sys.path.insert(0, _package_dir)

from .core import (
    AkkuConfig,
    AkkuLogger,
    LogLevel,
    MeshStats,
    StepResult,
    ErrorReport,
)

from .tools import (
    ToolRegistry,
    tool,
    StyleAnalyzer,
    MeshAnalyzer,
)

from .mesh import (
    MeshTools,
    MeshSnapshot,
    UndoManager,
    BooleanRemeshTools,
)

from .shader import (
    GLBMaterialParams,
    GLBMaterialSystem,
    StyleToGLBConverter,
    StylizedShaderSystem,
    MaterialSystem,
)

from .body import (
    BodyTypeParams,
    BodyTypePresets,
    DirectMeshDeformer,
    BodyTypeSystem,
)

from .kitbash import (
    SocketInfo,
    SemanticPart,
    KitbashLibrary,
    DirectBoneParenting,
    KitbashEquipper,
)

from .rigging import (
    WeightTransferResult,
    AutoWeightTransfer,
)

from .finalize import (
    OptimizationResult,
    TargetProfile,
    PlatformTargets,
    MeshOptimizer,
    MaterialOptimizer,
    DecimateEngine,
    MeshJoiner,
    FinalizePipeline,
)

from .handlers import (
    FBXHandler,
    MeshFreezer,
    GLBHandler,
)

from .procedural import (
    ProportionPreset,
    StyleProportions,
    PolyLevelSettings,
    PolyLevelPresets,
    ProceduralHumanoid,
)

from .bmesh_tools import (
    BmeshTools,
    CharacterBuilder,
    ExtrudeResult,
    LoopCutResult,
    MirrorResult,
    add_primitive_box,
    smart_extrude,
    loop_cut_and_slide,
    mirror_and_weld,
    RigAwareExtrudeResult,
    RigAwareExtruder,
    NormalRecalcResult,
    NormalRecalculator,
    EdgeLoopResult,
    EdgeLoopCutter,
    AtomicMeshOps,
    rig_aware_extrude,
    recalculate_normals,
    cut_edge_loop,
)

__version__ = "3.8.0"
__all__ = [
    # Core
    "AkkuConfig",
    "AkkuLogger",
    "LogLevel",
    "MeshStats",
    "StepResult",
    "ErrorReport",
    # Tools
    "ToolRegistry",
    "tool",
    "StyleAnalyzer",
    "MeshAnalyzer",
    # Mesh
    "MeshTools",
    "MeshSnapshot",
    "UndoManager",
    "BooleanRemeshTools",
    # Shader (GLB-compatible)
    "GLBMaterialParams",
    "GLBMaterialSystem",
    "StyleToGLBConverter",
    "StylizedShaderSystem",
    "MaterialSystem",
    # Body
    "BodyTypeParams",
    "BodyTypePresets",
    "DirectMeshDeformer",
    "BodyTypeSystem",
    # Kitbash
    "SocketInfo",
    "SemanticPart",
    "KitbashLibrary",
    "DirectBoneParenting",
    "KitbashEquipper",
    # Rigging
    "WeightTransferResult",
    "AutoWeightTransfer",
    # Finalize
    "OptimizationResult",
    "TargetProfile",
    "PlatformTargets",
    "MeshOptimizer",
    "MaterialOptimizer",
    "DecimateEngine",
    "MeshJoiner",
    "FinalizePipeline",
    # Handlers
    "FBXHandler",
    "MeshFreezer",
    "GLBHandler",
    # Procedural
    "ProportionPreset",
    "StyleProportions",
    "PolyLevelSettings",
    "PolyLevelPresets",
    "ProceduralHumanoid",
    # BMesh Tools
    "BmeshTools",
    "CharacterBuilder",
    "ExtrudeResult",
    "LoopCutResult",
    "MirrorResult",
    "add_primitive_box",
    "smart_extrude",
    "loop_cut_and_slide",
    "mirror_and_weld",
    # Atomic Operations
    "RigAwareExtrudeResult",
    "RigAwareExtruder",
    "NormalRecalcResult",
    "NormalRecalculator",
    "EdgeLoopResult",
    "EdgeLoopCutter",
    "AtomicMeshOps",
    "rig_aware_extrude",
    "recalculate_normals",
    "cut_edge_loop",
]

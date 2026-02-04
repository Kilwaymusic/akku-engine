"""
Akku SDK v3.5 - Modular Low-Poly Character Generation Toolkit

Modules:
- core: Configuration, Logging, Error Handling
- tools: Tool Registry, Style Analyzer, Mesh Analyzer
- mesh: Mesh Operations, Undo System, Boolean/Remesh
- shader: Material and Stylized Shader System
- body: Body Type System with Deformation
- kitbash: Semantic Component Library for Equipment
- handlers: FBX Import and GLB Export
"""

# Ensure the package directory is in sys.path for Blender imports
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
    MaterialSystem,
    StylizedShaderParams,
    StylizedShaderSystem,
)

from .body import (
    BodyTypeParams,
    BodyTypePresets,
    BodyTypeSystem,
)

from .kitbash import (
    SocketInfo,
    SemanticPart,
    KitbashLibrary,
    KitbashEquipper,
)

from .handlers import (
    FBXHandler,
    GLBHandler,
)

__version__ = "3.5.0"
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
    # Shader
    "MaterialSystem",
    "StylizedShaderParams",
    "StylizedShaderSystem",
    # Body
    "BodyTypeParams",
    "BodyTypePresets",
    "BodyTypeSystem",
    # Kitbash
    "SocketInfo",
    "SemanticPart",
    "KitbashLibrary",
    "KitbashEquipper",
    # Handlers
    "FBXHandler",
    "GLBHandler",
]

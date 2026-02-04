# Akku SDK v3.6 API Documentation

Low-poly 3D character generation toolkit for game engines (Unity/Unreal).

## Quick Start

```python
import bpy
from akku_sdk import (
    MeshTools,
    BodyTypePresets,
    BodyTypeSystem,
    StylizedShaderSystem,
    FinalizePipeline,
    GLBHandler,
    FBXHandler,
)

# 1. Load Mixamo FBX base mesh
MeshTools.clear_scene()
objects = FBXHandler.import_fbx("/path/to/mixamo_character.fbx")
mesh_obj = [o for o in objects if o.type == 'MESH'][0]

# 2. Apply body type
params = BodyTypePresets.get_preset("muscular")
BodyTypeSystem.apply_body_type(mesh_obj, params)

# 3. Apply stylized shader
StylizedShaderSystem.apply_stylized_shader(mesh_obj, (0.8, 0.2, 0.2), "stylized")

# 4. Optimize for platform
pipeline = FinalizePipeline("mobile")
result = pipeline.optimize_object(mesh_obj)

# 5. Export
GLBHandler.export_glb("/output/character.glb")
```

---

## Core Modules

### AkkuConfig
Global configuration settings.

```python
from akku_sdk import AkkuConfig

AkkuConfig.TARGET_HEIGHT = 2.0  # Default character height
AkkuConfig.OUTPUT_DIR = "/tmp/output"
AkkuConfig.LOG_LEVEL = "INFO"
```

### AkkuLogger
Structured logging system.

```python
from akku_sdk import AkkuLogger

AkkuLogger.info("Message", {"key": "value"})
AkkuLogger.error("Error message")
AkkuLogger.debug("Debug info")
```

---

## Mesh Operations

### MeshTools
Core mesh manipulation (context-independent, uses bmesh).

```python
from akku_sdk import MeshTools

# Clear scene
MeshTools.clear_scene()

# Normalize scale to target height
MeshTools.normalize_scale(obj, target_height=2.0)

# Decimate mesh
MeshTools.decimate_mesh(obj, ratio=0.5)

# Triangulate
MeshTools.triangulate_mesh(obj)

# Get triangle count
tris = MeshTools.get_triangle_count(obj)
```

### MeshAnalyzer
Mesh statistics and analysis.

```python
from akku_sdk import MeshAnalyzer

# Log mesh stats
MeshAnalyzer.log_stats(obj, "After processing")

# Get detailed stats
stats = MeshAnalyzer.get_stats(obj)
print(stats.vertex_count, stats.face_count, stats.triangle_count)
```

---

## Body Type System

### BodyTypePresets
12 predefined body type presets with Korean support.

| Preset | Korean | Description |
|--------|--------|-------------|
| `default` | 기본 | Standard proportions |
| `muscular` | 근육질 | Wide shoulders, narrow waist |
| `thin` | 마른 | Slim overall |
| `fat` | 뚱뚱한 | Wide torso |
| `tall` | 키큰 | Long legs/arms |
| `athletic` | 운동선수 | Balanced muscular |
| `heroic` | 영웅 | Muscular + tall |
| `chibi` | 치비 | Large head, small body |

```python
from akku_sdk import BodyTypePresets, BodyTypeSystem

# Get preset
params = BodyTypePresets.get_preset("heroic")

# Customize parameters
params.muscular = 0.8
params.shoulder_width = 1.3

# Apply to mesh
BodyTypeSystem.apply_body_type(obj, params)
```

### BodyTypeParams
Custom body type parameters.

```python
from akku_sdk import BodyTypeParams

custom = BodyTypeParams(
    muscular=0.7,
    fat=0.0,
    height=1.1,
    shoulder_width=1.2,
    hip_width=0.9,
    head_scale=1.0,
    arm_length=1.0,
    leg_length=1.0
)
```

---

## Stylized Shader System

### StylizedShaderSystem
Procedural shading for low-poly characters.

```python
from akku_sdk import StylizedShaderSystem

# Apply shader with color and style
StylizedShaderSystem.apply_stylized_shader(
    obj,
    color=(0.8, 0.2, 0.2),  # RGB tuple
    style="stylized"
)
```

**Style Presets:**
- `stylized` - Default, versatile
- `chibi` - Cute, simplified
- `heroic` - Bold, dramatic
- `cartoon` - Bright, flat
- `realistic` - Subtle effects
- `mobile` - Optimized for mobile
- `minifig` - Block-style

### StylizedShaderParams
Custom shader parameters.

```python
from akku_sdk import StylizedShaderParams

params = StylizedShaderParams(
    edge_strength=0.3,      # Edge highlighting
    cavity_strength=0.2,    # Cavity darkening
    fresnel_strength=0.15,  # Rim lighting
    saturation_boost=1.1,   # Color saturation
    value_boost=1.05        # Brightness
)
```

---

## Kitbash Equipment System

### KitbashLibrary
Semantic equipment component library.

```python
from akku_sdk import KitbashLibrary

# Get available parts
parts = KitbashLibrary.get_all_parts()

# Get part by ID
helmet = KitbashLibrary.get_part("helmet_warrior")

# Get parts by category
weapons = KitbashLibrary.get_parts_by_category("weapons")
```

**Part Categories:**
- `helmet` - Head protection
- `shoulder` - Shoulder armor
- `chest` - Body armor
- `boots` - Footwear
- `gauntlet` - Hand armor
- `weapon` - Weapons (sword, staff, dagger)
- `shield` - Defensive shields

### KitbashEquipper
Attach equipment to characters.

```python
from akku_sdk import KitbashEquipper

# Equip part to character
success = KitbashEquipper.equip_part(
    armature,
    "helmet_warrior",
    auto_rig=True  # Auto weight transfer
)

# Equip multiple parts
KitbashEquipper.equip_loadout(
    armature,
    ["helmet_warrior", "shoulder_heavy", "weapon_sword"]
)
```

---

## Rigging & Weight Transfer

### AutoWeightTransfer
Automatic vertex weight transfer for equipment.

```python
from akku_sdk import AutoWeightTransfer

# Transfer weights from base mesh to part
result = AutoWeightTransfer.transfer_weights(
    source_mesh,
    target_part,
    cleanup_zero=True
)

print(result.success, result.groups_transferred)
```

---

## Game Engine Optimization

### FinalizePipeline
Complete optimization pipeline for game engines.

```python
from akku_sdk import FinalizePipeline

# Create pipeline for target platform
pipeline = FinalizePipeline("mobile")

# Optimize single object
result = pipeline.optimize_object(obj)

print(f"Triangles: {result.original_tris} → {result.final_tris}")
print(f"Reduction: {result.reduction_percent:.1f}%")

# Optimize entire character (multiple parts)
result = pipeline.optimize_character(
    root_obj=armature,
    join_meshes=True
)
```

### PlatformTargets
Predefined platform optimization profiles.

| Platform | Max Triangles | Max Materials | Use Case |
|----------|---------------|---------------|----------|
| `mobile_low` | 300 | 1 | Low-end mobile |
| `mobile` | 800 | 2 | Standard mobile |
| `mobile_high` | 1500 | 3 | High-end mobile |
| `pc_low` | 3000 | 4 | Low-end PC |
| `pc` | 5000 | 6 | Standard PC |
| `pc_high` | 10000 | 8 | High-end PC/Console |

```python
from akku_sdk import PlatformTargets

# Get profile
profile = PlatformTargets.get_profile("mobile")
print(profile.max_triangles, profile.max_materials)

# List all profiles
for name, p in PlatformTargets.PROFILES.items():
    print(f"{name}: {p.max_triangles} tris, {p.max_materials} mats")
```

### MeshOptimizer
Low-level mesh optimization (context-independent).

```python
from akku_sdk import MeshOptimizer

# Remove duplicate vertices
MeshOptimizer.remove_doubles(obj, merge_distance=0.0001)

# Remove degenerate faces
MeshOptimizer.dissolve_degenerate(obj)

# Recalculate normals
MeshOptimizer.recalculate_normals(obj, inside=False)

# Get triangle count
tris = MeshOptimizer.get_triangle_count(obj)
```

### MaterialOptimizer
Material slot optimization.

```python
from akku_sdk import MaterialOptimizer

# Merge identical materials
MaterialOptimizer.merge_identical_materials(obj)

# Remove unused material slots
MaterialOptimizer.remove_unused_slots(obj)

# Consolidate to single material
MaterialOptimizer.consolidate_to_single_material(obj)

# Reduce to limit (e.g., 2 materials max)
MaterialOptimizer.reduce_to_limit(obj, max_materials=2)
```

### DecimateEngine
Polygon count reduction.

```python
from akku_sdk import DecimateEngine

# Decimate to target triangle count
original, final = DecimateEngine.decimate_to_target(
    obj,
    target_tris=800,
    method="collapse"  # or "planar", "unsubdiv"
)

# Decimate by ratio
original, final = DecimateEngine.decimate_by_ratio(obj, ratio=0.5)
```

### MeshJoiner
Join multiple mesh objects (UV-preserving).

```python
from akku_sdk import MeshJoiner

# Join meshes into one
joined = MeshJoiner.join_objects(
    [mesh1, mesh2, mesh3],
    new_name="Character_Joined"
)
```

### LOD Generation
Create Level of Detail chain.

```python
from akku_sdk import FinalizePipeline

# Create LOD0-LOD3
lod_chain = FinalizePipeline.create_lod_chain(obj)

for lod_name, lod_obj in lod_chain.items():
    print(f"{lod_name}: {len(lod_obj.data.polygons)} faces")
```

---

## Import/Export Handlers

### FBXHandler
FBX file import.

```python
from akku_sdk import FBXHandler

# Import FBX
objects = FBXHandler.import_fbx("/path/to/model.fbx")
```

### GLBHandler
glTF 2.0 (GLB) export.

```python
from akku_sdk import GLBHandler

# Export to GLB
GLBHandler.export_glb("/output/character.glb")
```

---

## Tool Registry

### @tool Decorator
Register functions as SDK tools.

```python
from akku_sdk import tool

@tool("my_tool", "Description of my tool")
def my_custom_tool(param1: str, param2: int = 10):
    # Tool implementation
    return {"success": True}
```

### ToolRegistry
Access registered tools.

```python
from akku_sdk import ToolRegistry

# List all tools
tools = ToolRegistry.list_tools()

# Get tool info
info = ToolRegistry.get_tool("my_tool")

# Execute tool
result = ToolRegistry.execute("my_tool", {"param1": "value"})
```

---

## Error Handling

### StepResult
Standard result format for operations.

```python
from akku_sdk import StepResult

result = StepResult(
    success=True,
    message="Operation completed",
    data={"triangles": 800}
)
```

### ErrorReport
Structured error reporting.

```python
from akku_sdk import ErrorReport

report = ErrorReport(
    step="optimization",
    error="Mesh has no faces",
    recoverable=True
)
```

---

## Running Tests

```bash
# Run archetype test suite
blender --background --python server/akku_sdk/test_all_archetypes.py

# Output directory: /tmp/akku_test_output/
# - test_report.json (JSON results)
# - quality_report.md (Markdown report)
# - *.glb files (generated models)
```

---

## Version History

- **v3.6.0** - Game Engine Optimization Pipeline
- **v3.5.0** - Modular architecture, Rigging module
- **v3.4.0** - Kitbash 2.0, Semantic equipment
- **v3.3.0** - Body Type System, Stylized Shaders
- **v3.2.0** - Korean language support
- **v3.1.0** - GCP Worker integration
- **v3.0.0** - Initial modular release

---

## License

Akku SDK is proprietary software. All rights reserved.

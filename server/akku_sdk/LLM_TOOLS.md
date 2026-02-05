# Akku SDK v5.0 - LLM Tool Reference

This document is designed for AI/LLM agents to understand and use the Akku SDK for procedural 3D character generation.

## Overview

The Akku SDK provides tools for creating game-ready low-poly humanoid characters in Blender. All tools are headless-safe and can be executed via CLI.

## Core Design Principle: Extrude-First Policy

**CRITICAL FOR AI UNDERSTANDING:**

The SDK creates characters using **Extrude-First methodology** - NOT by assembling separate primitives:

```
❌ OLD (Bad): Box + Cylinder + Sphere = Disconnected shapes
✅ NEW (Good): Torso → Extrude neck → Extrude head → Extrude arms → Extrude legs = Single connected mesh
```

**Why this matters:**
- Produces organic, natural-looking characters (not "stacked shapes")
- Single connected mesh = better for game engines
- Proper topology for rigging and animation
- AI should understand: ALL body parts come FROM the base torso via extrusion

## Tool Categories

1. **Base Generation** - Create unified humanoid mesh (Extrude-First)
2. **Body Modification** - Adjust body proportions and type
3. **Style & Materials** - Apply shaders and vertex colors
4. **Equipment** - Add armor, weapons, accessories (also uses Extrude from mesh faces)
5. **Verification** - Capture screenshots for review
6. **Export** - Save as GLB file

## AI Decision Flow

When generating a character, follow this decision tree:

```
1. Analyze prompt → mapPromptToParameters()
   ↓
2. Determine style (realistic/stylized/chibi/etc.)
   ↓
3. Determine body type (muscular/thin/athletic/etc.)
   ↓
4. Determine equipment (armor/robe/default)
   ↓
5. Call generate_procedural_base with all parameters
   ↓
6. Capture screenshot for verification
   ↓
7. Analyze with VLM → Need refinement?
   ├─ Yes → Apply body_type/style adjustments → Go to step 6
   └─ No → Export GLB
```

---

## Available Tools (JSON Schema)

### 1. generate_procedural_base

Creates a procedural humanoid mesh using **Extrude-First methodology** (single connected mesh, not separate primitives).

```json
{
  "tool": "generate_procedural_base",
  "params": {
    "style": {
      "type": "string",
      "enum": ["realistic", "stylized", "chibi", "sd", "mobile", "minifig", "cartoon"],
      "default": "stylized",
      "description": "Character proportion style"
    },
    "poly_level": {
      "type": "string",
      "enum": ["ultra_low", "low", "medium", "high"],
      "default": "medium",
      "description": "Polygon complexity (ultra_low=300 tris, high=3000 tris)"
    },
    "gender": {
      "type": "string",
      "enum": ["male", "female", "neutral"],
      "default": "male",
      "description": "Affects body proportions"
    },
    "equipment": {
      "type": "string",
      "enum": ["default", "armor", "robe"],
      "default": "default",
      "description": "Vertex color preset for equipment type"
    },
    "hierarchical": {
      "type": "boolean",
      "default": false,
      "description": "DEPRECATED: Always use false for Extrude-First unified mesh. True produces multi-part (legacy) mesh."
    }
  },
  "returns": {
    "mesh_count": "number",
    "mesh_names": "string[]",
    "total_triangles": "number",
    "generation_mode": "string"
  }
}
```

**Example:**
```python
ToolRegistry.execute("generate_procedural_base", {
    "style": "stylized",
    "poly_level": "medium",
    "gender": "male",
    "equipment": "armor"
})
```

---

### 2. apply_body_type

Applies body type deformation to the character mesh.

```json
{
  "tool": "apply_body_type",
  "params": {
    "body_type": {
      "type": "string",
      "enum": ["default", "muscular", "thin", "fat", "tall", "short", "athletic", "stocky", "slim", "heroic", "chibi", "giant"],
      "default": "default",
      "description": "Preset body type"
    },
    "muscular": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "default": null,
      "description": "Override muscle definition (0=none, 1=bodybuilder)"
    },
    "fat": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "default": null,
      "description": "Override body fat (0=thin, 1=overweight)"
    },
    "height": {
      "type": "number",
      "minimum": 0.7,
      "maximum": 1.3,
      "default": null,
      "description": "Height multiplier (1.0=normal)"
    },
    "shoulder_width": {
      "type": "number",
      "minimum": 0.7,
      "maximum": 1.5,
      "default": null,
      "description": "Shoulder width multiplier"
    },
    "hip_width": {
      "type": "number",
      "minimum": 0.7,
      "maximum": 1.3,
      "default": null,
      "description": "Hip width multiplier"
    }
  }
}
```

**Body Type Reference:**
| Preset | Muscular | Fat | Height | Shoulders |
|--------|----------|-----|--------|-----------|
| muscular | 1.0 | 0.0 | 1.0 | 1.4 |
| heroic | 1.0 | 0.0 | 1.1 | 1.5 |
| athletic | 0.6 | 0.0 | 1.0 | 1.1 |
| fat | 0.0 | 1.0 | 1.0 | 1.1 |
| thin | 0.0 | 0.0 | 1.0 | 0.8 |
| chibi | 0.0 | 0.3 | 0.75 | 0.9 |

**Example:**
```python
ToolRegistry.execute("apply_body_type", {
    "body_type": "muscular",
    "shoulder_width": 1.4
})
```

---

### 3. apply_style

Applies style transformations based on prompt analysis.

```json
{
  "tool": "apply_style",
  "params": {
    "prompt": {
      "type": "string",
      "description": "Character description for color/style detection"
    },
    "style": {
      "type": "string",
      "enum": ["realistic", "stylized", "chibi", "sd", "mobile", "minifig", "cartoon"],
      "default": "stylized"
    },
    "poly_level": {
      "type": "string",
      "enum": ["ultra_low", "low", "medium", "high"],
      "default": "medium"
    }
  }
}
```

---

### 4. equip_item

Attaches equipment from the Kitbash library.

```json
{
  "tool": "equip_item",
  "params": {
    "category": {
      "type": "string",
      "enum": ["helmet", "shoulder", "chest", "gauntlet", "boots", "weapon", "shield"],
      "description": "Equipment category"
    },
    "style": {
      "type": "string",
      "enum": ["knight", "scifi", "mage", "rogue"],
      "description": "Equipment style"
    },
    "part_name": {
      "type": "string",
      "description": "Specific part ID (optional, overrides category/style)"
    },
    "color": {
      "type": "array",
      "items": {"type": "number"},
      "description": "RGB color [0.0-1.0, 0.0-1.0, 0.0-1.0]"
    }
  }
}
```

**Available Parts:**
- Helmets: knight_helmet, scifi_helmet, mage_hood
- Shoulders: knight_shoulder, scifi_shoulder
- Chest: knight_chestplate, scifi_chestplate
- Weapons: knight_sword, scifi_blaster, mage_staff

---

### 5. capture_screenshot

Captures viewport screenshot for self-verification (headless-safe).

```json
{
  "tool": "capture_screenshot",
  "params": {
    "output_path": {
      "type": "string",
      "description": "Output PNG file path (e.g., /tmp/preview.png)"
    },
    "view": {
      "type": "string",
      "enum": ["front", "side", "quarter", "top"],
      "default": "front",
      "description": "Camera angle preset"
    },
    "resolution": {
      "type": "integer",
      "minimum": 256,
      "maximum": 2048,
      "default": 768,
      "description": "Image resolution (square)"
    },
    "include_composite": {
      "type": "boolean",
      "default": false,
      "description": "Create front+side 2-up composite"
    }
  },
  "returns": {
    "path": "string",
    "exists": "boolean",
    "size_bytes": "number",
    "bounds": {
      "min": "[x, y, z]",
      "max": "[x, y, z]",
      "center": "[x, y, z]",
      "size": "[width, depth, height]"
    },
    "scene_info": {
      "mesh_count": "number",
      "total_vertices": "number",
      "total_faces": "number"
    }
  }
}
```

**Example:**
```python
result = ToolRegistry.execute("capture_screenshot", {
    "output_path": "/tmp/character_preview.png",
    "view": "quarter",
    "resolution": 768,
    "include_composite": True
})
# Returns: {"path": "/tmp/character_preview.png", "exists": true, "size_bytes": 45678, ...}
```

---

### 6. get_scene_info

Gets current scene statistics for context.

```json
{
  "tool": "get_scene_info",
  "params": {},
  "returns": {
    "mesh_count": "number",
    "mesh_names": "string[]",
    "total_vertices": "number",
    "total_faces": "number",
    "armature_count": "number",
    "bounds": {
      "min": "[x, y, z]",
      "max": "[x, y, z]",
      "center": "[x, y, z]",
      "size": "[width, depth, height]"
    }
  }
}
```

---

### 7. export_glb

Exports scene as GLB file for game engines.

```json
{
  "tool": "export_glb",
  "params": {
    "output_path": {
      "type": "string",
      "description": "Output GLB file path"
    }
  },
  "returns": {
    "path": "string",
    "size_bytes": "number",
    "success": "boolean"
  }
}
```

---

### 8. generate_character

Complete pipeline that combines all steps.

```json
{
  "tool": "generate_character",
  "params": {
    "prompt": {"type": "string", "description": "Character description"},
    "style": {"type": "string", "enum": ["realistic", "stylized", "chibi", "sd", "mobile", "minifig", "cartoon"]},
    "poly_level": {"type": "string", "enum": ["ultra_low", "low", "medium", "high"]},
    "output_path": {"type": "string"},
    "gender": {"type": "string", "enum": ["male", "female", "neutral"]},
    "body_type": {"type": "string"},
    "equipment": {"type": "string", "enum": ["default", "armor", "robe"]}
  }
}
```

---

## Iterative Refinement Workflow

For autonomous 3D agent with self-verification:

1. **Generate** → Create base mesh with `generate_procedural_base`
2. **Capture** → Take screenshot with `capture_screenshot`
3. **Analyze** → Send screenshot to Gemini VLM for review
4. **Refine** → Apply adjustments based on feedback
5. **Repeat** → Steps 2-4 up to 3 times
6. **Export** → Save final GLB with `export_glb`

**Refinement Example:**
```python
# Iteration 1: Generate base
ToolRegistry.execute("generate_procedural_base", {"style": "stylized", "poly_level": "medium"})

# Take screenshot for review
result = ToolRegistry.execute("capture_screenshot", {"output_path": "/tmp/iter1.png", "view": "quarter"})

# [Gemini analyzes screenshot and returns adjustment params]

# Iteration 2: Apply refinements
ToolRegistry.execute("apply_body_type", {"muscular": 0.8, "shoulder_width": 1.3})

# Take new screenshot
result = ToolRegistry.execute("capture_screenshot", {"output_path": "/tmp/iter2.png", "view": "quarter"})

# [Repeat until satisfied]

# Export final
ToolRegistry.execute("export_glb", {"output_path": "/output/character.glb"})
```

---

## Korean Keyword Reference

The SDK recognizes Korean character archetypes:

| Korean | English | Body Type | Equipment |
|--------|---------|-----------|-----------|
| 전사 | Warrior | muscular | armor |
| 기사 | Knight | muscular | plate armor |
| 마법사 | Mage | thin | robe, staff |
| 도적 | Rogue | athletic | leather |
| 치비 | Chibi | chibi | default |
| 영웅 | Hero | heroic | armor |

---

## Error Handling

All tools return structured results:

```json
{
  "status": "success" | "error",
  "result": { ... },
  "message": "Error description if failed",
  "error_report": {
    "tool_name": "...",
    "error_type": "...",
    "error_message": "...",
    "mesh_stats_at_failure": { ... }
  }
}
```

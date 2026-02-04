# Akku Engine - AI 3D Character Generator

## Overview

Akku Engine is an AI-powered 3D humanoid character generation platform. Users input text prompts describing characters, and the system generates game-ready 3D assets in GLB format. The application features a React frontend with a Babylon.js 3D viewer, an Express backend for job management, and uses Blender for procedural 3D model generation.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React 18 with TypeScript, bundled with Vite
- **Routing**: Wouter for lightweight client-side routing
- **State Management**: TanStack React Query for server state and caching
- **UI Components**: shadcn/ui component library built on Radix UI primitives
- **Styling**: Tailwind CSS with CSS variables for theming (dark/light mode support)
- **3D Rendering**: Babylon.js for real-time WebGL model viewing with GLB loader support
- **Path Aliases**: `@/` maps to `client/src/`, `@shared/` maps to `shared/`

### Backend Architecture
- **Framework**: Express.js with TypeScript running on Node.js
- **API Pattern**: RESTful endpoints under `/api/` prefix
- **Development**: Vite dev server middleware integrated with Express for HMR
- **Production**: esbuild bundles server code, static files served from `dist/public`
- **Job Processing**: Asynchronous job queue pattern - jobs are created, then processed in background

### Data Storage
- **Schema Definition**: Drizzle ORM with PostgreSQL dialect (`shared/schema.ts`)
- **Current Implementation**: In-memory storage (`MemStorage` class) for development
- **Database Ready**: Drizzle config points to `DATABASE_URL` environment variable for PostgreSQL
- **Job Table**: Stores job ID, prompt, status (pending/processing/completed/failed), model URL, error message, and timestamp

### 3D Model Generation Pipeline (GCP Worker)

The system uses a **remote GCP Worker server** for Blender operations, solving Replit's headless Blender limitations.

#### Architecture: Remote GCP Worker
- **Worker URL**: `http://34.134.82.224:5000/generate`
- **Flow**: Replit sends POST request with prompt → GCP Worker runs Blender → Returns GLB file
- **Components**:
  - `server/routes.ts` - HTTP client that sends requests to GCP Worker
  - GCP Worker - External server running Blender with full capabilities

#### Request/Response Format
**Request (POST /generate)**:
```json
{
  "prompt": "red robot warrior",
  "style": "stylized",
  "polyLevel": "medium",
  "jobId": "abc123"
}
```

**Response**: Binary GLB file

#### Advantages
- Full Blender capabilities (no headless limitations)
- Mixamo FBX support with proper rigging
- Scalable architecture
- Stable and reliable generation

### AI Integration (Gemini)
- **File**: `server/gemini.ts`
- **API Key**: Uses `GEMINI_API_KEY` from secrets (custom), or falls back to Replit AI Integrations
- **Model**: gemini-2.5-flash
- **Functions**:
  - `generateAkkuPlan()` - Multi-step Akku SDK generation plan for MCP mode
  - `analyzePromptWithGemini()` - Simple parameters for CLI mode
- **Output**: JSON with SDK tool calls, parameters, and execution order
- **Korean Support**: Color terms (빨강/파랑/초록/etc.) and prompts supported

### Build System
- **Client Build**: Vite compiles React app to `dist/public`
- **Server Build**: esbuild bundles server with selective dependency bundling for faster cold starts
- **Database Migrations**: `drizzle-kit push` for schema synchronization

## Key Files

| File | Purpose |
|------|---------|
| `server/routes.ts` | API routes with GCP Worker integration |
| `server/gcp-app.py` | GCP Worker Flask server (v3.7) |
| `server/image-analyzer.ts` | Gemini Vision image analysis for reference images (NEW) |
| `client/src/components/BabylonViewer.tsx` | 3D model viewer component |
| `server/akku_sdk/` | Modular Blender SDK package (v3.8) |

### Akku SDK v3.8 Modules

| Module | Lines | Purpose |
|--------|-------|---------|
| `core.py` | 163 | AkkuConfig, AkkuLogger, MeshStats, StepResult, ErrorReport |
| `tools.py` | 241 | ToolRegistry with @tool decorator, StyleAnalyzer, MeshAnalyzer |
| `mesh.py` | 438 | MeshTools, UndoManager, BooleanRemeshTools |
| `shader.py` | 328 | MaterialSystem, StylizedShaderParams, StylizedShaderSystem |
| `body.py` | 321 | BodyTypeParams, BodyTypePresets, BodyTypeSystem |
| `kitbash.py` | 419 | SocketInfo, SemanticPart, KitbashLibrary, KitbashEquipper |
| `rigging.py` | 324 | AutoWeightTransfer, WeightTransferResult (Data Transfer modifier) |
| `finalize.py` | 1028 | FinalizePipeline, MeshOptimizer, DecimateEngine, MeshJoiner, LOD generation |
| `procedural.py` | 600+ | ProceduralHumanoid, StyleProportions, PolyLevelPresets |
| `bmesh_tools.py` | 3100+ | BmeshTools, TopologyOps, SemanticSelector, GameOptimizer, AI Macros |

### v3.8 New Features (2026-02-04)

#### 1. Procedural Humanoid Generation
- **No Mixamo dependency**: Characters can now be generated from scratch using bmesh primitives
- **Styles**: realistic, stylized, chibi, sd, mobile, minifig, cartoon
- **Poly Levels**: ultra_low (~300 tris), low (~800 tris), medium (~1500 tris), high (~3000 tris)
- **Auto-rigging**: Basic humanoid armature created automatically
- **Usage**: Set `use_procedural=true` (default) in generation request

#### 2. Image Prompt Analysis
- **Gemini Vision Integration**: Upload reference images to extract character attributes
- **Auto-detection**: Style, body type, colors, archetype, equipment
- **Korean support**: Suggested prompts in Korean/English
- **Endpoint**: POST `/api/analyze-image` with base64 image data

#### 3. Enhanced Quality
- **Style-specific proportions**: Each style has optimized body ratios
- **Better topology**: Improved mesh generation with proper edge flow
- **Gender variations**: Subtle proportion adjustments for male/female

#### 4. BMesh Direct Manipulation Tools (v3.8)
Core low-level mesh editing primitives for procedural character building:
- `add_primitive_box()`: Creates starting box for all modeling
- `smart_extrude(face_index, length)`: Extrudes face with auto vertex group assignment
- `loop_cut_and_slide(edge_index, count)`: Adds edge loops for smooth joint deformation
- `mirror_and_weld()`: Mirrors geometry and welds center vertices for symmetry

#### 5. Atomic Operations System (v3.8)
Feature-based SDK with atomic mesh operations:
- `RigAwareExtruder`: Extrude with automatic weight inheritance from parent vertices
- `EdgeLoopCutter`: Advanced loop cutting that follows edge flow for joint creation
- `NormalRecalculator`: Automatic normal recalculation after any mesh operation
- `AtomicMeshOps`: Unified interface wrapping all atomic operations
- `cut_edge_loop()`: Loop cuts with weight inheritance for smooth deformation

#### 6. Geometric Precision Controls (v3.8)
Essential precision functions for production-quality meshes:
- `SymmetryMirror`: Real-time mirroring with automatic center vertex welding
- `FaceNormalOrient`: Force all normals outward (prevents shader artifacts)
- `TransformSpace`: Local (face normal) vs Global (world XYZ) transforms
- `SelectionFilter`: Position-based face selection ('top', 'front', 'left', etc.)

#### 7. Game-Ready Atomic Operations (v3.8)
Complete toolkit for game asset creation:
- **Topology Ops**: `TopologyOps` - Inset, Bevel, Bridge edge loops
- **Semantic Selection**: `SemanticSelector` - Select by loop/ring/sharp edges/boundary
- **Transform Ops**: `TransformOps` - Proportional editing, flatten, snap to symmetry
- **Game Optimizer**: `GameOptimizer` - Merge doubles, triangulate, decimate, UV project, shading

#### 8. AI-Friendly Macro Functions (v3.8)
High-level functions designed for LLM orchestration:
- `extrude_and_scale(face, length, scale)`: Combined extrude + scale
- `inset_and_extrude(face, inset, depth)`: For eye sockets, buttons, etc.
- `bevel_sharp_edges(angle, width)`: Auto-bevel all sharp edges
- `select_and_extrude(position, length)`: "Extrude top face 0.2 units"
- `optimize_for_game()`: Full game pipeline (merge + triangulate + smooth)
| `handlers.py` | 62 | FBXHandler, GLBHandler |
| `main.py` | 444 | CLI interface and registered tools |
| `run.py` | 25 | Blender entry script (safe subprocess invocation) |
| `__init__.py` | 135 | Clean API with all exports, sys.path registration |
| `test_all_archetypes.py` | 450 | Comprehensive test suite for all archetypes |
| `API_DOCS.md` | 350 | Complete SDK API documentation |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/jobs` | GET | List all jobs |
| `/api/jobs/:id` | GET | Get job by ID |
| `/api/jobs` | POST | Create new generation job |
| `/api/status` | GET | Get system status (GCP Worker mode) |

## External Dependencies

### Core Services
- **GCP Worker**: Remote Blender server at `http://34.134.82.224:5000` for 3D model generation
- **PostgreSQL**: Database backend (configured via `DATABASE_URL` environment variable, uses Drizzle ORM)
- **Gemini API**: Google AI for prompt analysis and generation planning (optional)

### Secrets
- `GEMINI_API_KEY` - Custom Gemini API key
- `SESSION_SECRET` - Session encryption key

### Frontend Libraries
- **Babylon.js**: 3D rendering engine with glTF/GLB loader support
- **Radix UI**: Headless UI component primitives (dialog, dropdown, tabs, etc.)
- **TanStack Query**: Async state management with polling for job status updates
- **date-fns**: Date formatting with Korean locale support

### Backend Libraries
- **Drizzle ORM**: Type-safe database queries with PostgreSQL driver
- **Express Session**: Session management with connect-pg-simple for PostgreSQL session store
- **Zod**: Runtime schema validation for API inputs
- **@google/genai**: Google Generative AI SDK for Gemini integration

## Character Generation Options

### Proportion Types (7 styles)
**Note**: With Mixamo FBX meshes, all proportion types use the same base body shape. The type name affects uniform scale factor and is passed to AI for style guidance.

| Type | Scale | Description |
|------|-------|-------------|
| `stylized` | 1.0 | Default, versatile |
| `chibi` | 0.7 | Smaller scale (cute style) |
| `sd` | 0.7 | Smaller scale (super-deformed style) |
| `mobile` | 0.8 | Optimized for mobile |
| `minifig` | 0.6 | Smallest scale (block style) |
| `cartoon` | 0.9 | Slightly smaller (cartoon style) |
| `realistic` | 1.0 | Full scale, human-like |

### Polygon Levels (4 levels)
| Level | Triangle Count | Target Platform |
|-------|----------------|-----------------|
| `ultra_low` | ~300 tris | Mobile, web games |
| `low` | ~800 tris | Low-end devices |
| `medium` | ~1500 tris | Balanced quality |
| `high` | ~3000 tris | PC/Console games |

### Body Type System (SDK v3.3)
12 body type presets with Korean language support:

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

### Stylized Shader System (SDK v3.3)
Procedural material system for low-poly characters:

| Node | Function |
|------|----------|
| Geometry (Pointiness) | Edge highlighting - bright edges |
| Ambient Occlusion | Cavity darkening - dark creases |
| Fresnel | Rim lighting effect |

Style presets adjust shader parameters automatically (stylized, chibi, heroic, cartoon, realistic, mobile, minifig).

## Recent Changes
- 2026-02-04: **Enhanced Body Deformation & Kitbash Integration** - Major visual differentiation update
  - Doubled body deformation scaling factors (0.12-0.25 → 0.25-0.50) for dramatic visible changes
  - Increased all preset values (muscular: 0.6→1.0, fat: 0.5→1.0, heroic: 0.5→0.9, etc.)
  - Added MIN_SCALE/MAX_SCALE clamping (0.4-2.0) to prevent mesh distortion
  - Integrated kitbash equipment into generate_character pipeline with archetype detection
  - Maps archetype to equipment style: warrior/knight→heavy, mage/wizard→magic, rogue→light, robot→scifi
  - Auto-runs weight transfer after successful equipment attachment
  - Created sync_to_gcp.sh script for deploying SDK updates to GCP Worker
- 2026-02-04: **Direct Data Manipulation Refactoring** - Ensures GLB export compatibility
  - `shader.py`: Replaced complex shader nodes with GLB-standard Principled BSDF (Base Color, Metallic, Roughness, Emission only)
  - `body.py`: Added DirectMeshDeformer class - all vertex deformations via bmesh, baked into mesh data
  - `kitbash.py`: Added DirectBoneParenting - parts created at origin, immediately parented with BONE parent type
  - `handlers.py`: Added MeshFreezer class - freezes modifiers AND transforms before GLB export
  - Reduced body scaling factors from 0.4-0.5 to 0.12-0.25 for natural-looking results
- 2026-02-04: **Added Game Engine Optimization Pipeline** - finalize.py module (1028 lines)
  - FinalizePipeline for Unity/Unreal-ready export with context-independent operations
  - MeshOptimizer: remove_doubles, dissolve_degenerate, recalculate_normals (bmesh-based)
  - MaterialOptimizer: merge_identical, consolidate_to_single, reduce_to_limit
  - DecimateEngine: decimate_to_target with depsgraph + bmesh fallback for headless
  - PlatformTargets: 6 profiles (mobile_low, mobile, mobile_high, pc_low, pc, pc_high)
  - MeshJoiner: join_objects with UV preservation (bmesh-based, no bpy.ops)
  - LOD chain generation (LOD0-LOD3) for distance-based detail
  - Note: Optimized for low-poly procedural models; complex rigged assets may need bpy.ops
- 2026-02-04: **Added Prompt-to-Parameter Mapping Engine** - Enhanced gemini.ts
  - mapPromptToParameters() converts abstract prompts to SDK parameters
  - AkkuSDKParameters interface with bodyType, style, shader, equipment
  - SDK_PARAMETER_SCHEMA for strict JSON validation
  - Comprehensive mapping tables for archetypes, materials, colors
  - Korean language support (강력한 전사 → muscular:0.8, armorStyle:plate)
- 2026-02-04: **Added Strict TypeScript Types** - Union literals for all SDK parameters
  - BodyPreset, ProportionType, PolyLevel, Gender, StylePreset, ArmorStyle, Archetype
  - Equipment types: HelmetType, ShoulderType, ChestType, etc.
  - VALID_* arrays for runtime enum validation
  - validateEnum<T>() and validateEquipment<T>() helpers
- 2026-02-04: **Added Auto Weight Transfer System** - rigging.py module (324 lines)
  - Uses Data Transfer modifier to copy vertex weights from base mesh to parts
  - Enables equipment to deform with animations without manual weight painting
  - Integrated with KitbashEquipper (auto_rig=True by default)
  - cleanup_zero_weights() removes empty vertex groups
- 2026-02-04: **SDK v3.5 Modular Refactoring** - Split monolithic file into 9 focused modules
  - 2,878 total lines across modules (increased from base due to rigging module)
  - Clean imports via `from akku_sdk import ...`
  - All operations remain context-independent (bmesh-based)
- 2026-02-04: **Added Kitbash 2.0 Semantic Component Library** - AI-driven equipment system
  - 20+ SemanticPart definitions (helmets, shoulders, chest, boots, gauntlets, weapons, shields)
  - Category taxonomy: "armor" → [helmet, shoulder, chest, boots, gauntlet], "weapons" → [weapon, shield]
  - SocketInfo with bone_name, offset, rotation, scale for precise attachment
  - bmesh-based mesh creation (context-independent, no bpy.ops)
  - Bone rotation composition for proper equipment orientation
- 2026-02-04: **Added Stylized Shader System** - Edge highlighting + cavity darkening for low-poly models
  - Geometry (Pointiness) + AO nodes for procedural shading
  - 8 style presets with different shader parameters
  - Fresnel rim lighting support
- 2026-02-04: **Added Body Type System** - 12 presets with Korean support
  - Lattice/Vertex deformation for natural body shapes
  - Auto-detection from prompts (e.g., "근육질 전사")
- 2026-02-04: **Migrated to GCP Worker architecture** - Remote Blender server for reliable 3D generation
  - Removed local Blender MCP/CLI execution (Replit headless limitations)
  - Added HTTP client with timeout (2 min), GLB validation, error handling
  - GCP Worker at `http://34.134.82.224:5000/generate`
- 2026-02-04: Added UI style selector with 7 proportion types and 4 poly levels
- 2026-02-04: Implemented character generation with Mixamo FBX base meshes
- 2026-02-04: Added Korean language support for color terms and prompts

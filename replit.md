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

### 3D Model Generation Pipeline (Akku Low-poly SDK)

The system uses the **Akku Low-poly SDK** architecture with Mixamo FBX base meshes (Y Bot / X Bot) for high-quality rigged humanoids.

#### Mode 1: Akku SDK via MCP (Primary)
- **Architecture**: Persistent Blender process with TCP socket communication
- **Base Meshes**: Mixamo Y Bot (neutral/female) and X Bot (male) FBX files in `assets/base_meshes/`
- **Components**:
  - `scripts/blender_mcp_addon.py` - Blender addon with Akku SDK implementation
  - `server/blender-mcp-client.ts` - Node.js TCP client with SDK methods
  - `server/mcp-manager.ts` - Process lifecycle manager
- **SDK Tools (8 total across 4 categories)**:

| Category | Tool | Description |
|----------|------|-------------|
| Base Generation | `spawn_humanoid_base` | Load Mixamo FBX with proportions, poly level, and gender |
| Base Generation | `deform_body` | Scale entire body (limited: only "body" + "scale" supported) |
| Kitbashing | `attach_armor_plate` | Add armor pieces (7 styles: knight/samurai/scifi/heavy/rogue/mage/tribal) |
| Kitbashing | `add_scifi_detail` | Add sci-fi elements (antenna/visor/jetpack/tubes/panel) |
| PBR Shading | `apply_akku_pbr` | Apply PBR materials (10 presets: metal/cloth/leather/skin/etc.) |
| PBR Shading | `set_material_property` | Fine-tune material properties |
| Rigging | `finalize_and_bind` | Finalize mesh and export (rigging included from FBX) |
| Rigging | `test_animation` | Apply animation clips (idle/walk/run/attack) |

- **Object Naming**: 
  - `AkkuBase_Armature` - Rigged skeleton
  - `AkkuBase_Surface` - Main character mesh (target for materials)
  - `AkkuBase_Aux_*` - Auxiliary meshes (joints, eyes)
  - `Armor_*` - Armor plates from kitbashing
- **Advantages**: Pre-rigged Mixamo skeleton, clean topology, Mixamo animation compatible

#### Mode 2: CLI (Command Line Interface) - Fallback
- **Generator**: Python script (`scripts/generate_humanoid.py`) runs in Blender's background mode
- **Process Flow**: Express spawns Blender subprocess → Single-shot generation → Exports GLB file
- **Used when**: MCP server unavailable or fails

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
| `server/gemini.ts` | Gemini AI integration for prompt analysis |
| `server/blender-mcp-client.ts` | TCP client for Blender MCP communication |
| `server/mcp-manager.ts` | Blender process lifecycle management |
| `scripts/blender_mcp_addon.py` | Blender MCP server addon |
| `scripts/generate_humanoid.py` | Legacy CLI-based generation script |
| `server/routes.ts` | API routes with dual-mode generation |
| `client/src/components/BabylonViewer.tsx` | 3D model viewer component |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/jobs` | GET | List all jobs |
| `/api/jobs/:id` | GET | Get job by ID |
| `/api/jobs` | POST | Create new generation job |
| `/api/status` | GET | Get system status (MCP mode, Blender ready) |
| `/api/mode` | POST | Toggle MCP/CLI mode |

## External Dependencies

### Core Services
- **PostgreSQL**: Database backend (configured via `DATABASE_URL` environment variable, uses Drizzle ORM)
- **Blender**: External 3D software required for model generation (must be installed and available in PATH)
- **Gemini API**: Google AI for prompt analysis and generation planning

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

## Recent Changes
- 2026-02-04: **Integrated Mixamo FBX base meshes** - Replaced procedural generation with Y Bot / X Bot
  - High-quality pre-rigged humanoid meshes with Mixamo bone hierarchy
  - Clean topology suitable for animation and games
  - Consistent object naming: `AkkuBase_Surface` (mesh), `AkkuBase_Armature` (rig)
  - Decimation applied only to main surface mesh
- 2026-02-04: **Fixed MCP headless mode** - All SDK functions now work in Blender's background mode
  - Replaced `bpy.context.active_object` with `bpy.data.objects` lookups
  - Used `bpy.context.evaluated_depsgraph_get()` for modifier application
  - Export uses subprocess approach to avoid glTF exporter context issues
  - `finalize_and_bind` exports mesh-only (rigging included from FBX)
  - `test_animation` gracefully skips when no armature present
- 2026-02-04: Added UI style selector with 7 proportion types and 4 poly levels
- 2026-02-04: Optimized GLB export for game engines (mesh joining, Y-up orientation)
- 2026-02-04: Extended spawn_humanoid_base with poly_level parameter
- 2026-02-04: Added new proportion types (mobile, minifig, cartoon)
- 2026-02-04: Implemented Akku Low-poly SDK with 8 structured tools across 4 categories
- 2026-02-04: Updated Gemini prompt to use Akku SDK API exclusively
- 2026-02-04: Added Korean language support for color terms and prompts
- 2026-02-04: Integrated Blender MCP for advanced procedural generation
- 2026-02-04: Added Gemini AI for multi-step generation plan creation
- 2026-02-04: Implemented dual-mode generation (MCP primary, CLI fallback)
- 2026-02-04: Added custom GEMINI_API_KEY support via secrets

## Headless Mode Compatibility Notes

The Blender MCP server runs in background/headless mode, which has limitations:
1. **No `bpy.context.active_object`** - Use `bpy.data.objects['name']` instead
2. **No `bpy.context.selected_objects`** - Track objects manually or iterate `bpy.context.scene.objects`
3. **glTF exporter requires window context** - Export via subprocess with `-b` flag
4. **Object naming is consistent** - Main mesh is always `AkkuBase_Surface`, armature is `AkkuBase_Armature`

## Mixamo Integration Notes

- **Base Meshes**: `assets/base_meshes/Y_Bot.fbx` and `assets/base_meshes/X_Bot.fbx`
- **Gender Selection**: `gender: "neutral"|"female"` uses Y Bot, `gender: "male"` uses X Bot
- **Proportion Types**: Control overall scale only (all types use same Mixamo proportions)
- **Polygon Reduction**: Decimate modifier applied only to main surface mesh
- **Pre-rigged**: Meshes come with complete Mixamo rig, compatible with Mixamo animations

### Current Limitations
- `deform_body` only supports scaling entire body, not individual parts (due to Mixamo unified mesh)
- Proportion types (chibi/SD/minifig) only affect scale, not actual body proportions
- Custom proportions would require separate FBX files with different body shapes

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

### 3D Model Generation Pipeline (Dual Mode)

The system supports two generation modes with automatic fallback:

#### Mode 1: MCP (Model Context Protocol) - Primary
- **Architecture**: Persistent Blender process with TCP socket communication
- **Components**:
  - `scripts/blender_mcp_addon.py` - Blender addon running MCP server
  - `server/blender-mcp-client.ts` - Node.js TCP client
  - `server/mcp-manager.ts` - Process lifecycle manager
- **Process Flow**:
  1. User prompt → Gemini AI generates multi-step generation plan
  2. Node.js connects to Blender MCP server via TCP (port 9876)
  3. Sends JSON commands for each step (create_base, apply_modifier, setup_material, etc.)
  4. Blender executes commands and returns results
  5. Final GLB export
- **Advantages**: Real-time state inspection, iterative refinement, advanced modifiers

#### Mode 2: CLI (Command Line Interface) - Fallback
- **Generator**: Python script (`scripts/generate_humanoid.py`) runs in Blender's background mode
- **Process Flow**: Express spawns Blender subprocess → Single-shot generation → Exports GLB file
- **Used when**: MCP server unavailable or fails

### AI Integration (Gemini)
- **File**: `server/gemini.ts`
- **API Key**: Uses `GEMINI_API_KEY` from secrets (custom), or falls back to Replit AI Integrations
- **Model**: gemini-2.5-flash
- **Functions**:
  - `generateCharacterPlan()` - Multi-step procedural generation plan for MCP mode
  - `analyzePromptWithGemini()` - Simple parameters for CLI mode
- **Output**: JSON with character type, colors, proportions, modifiers, materials

### MCP Command Types
- `create_base` - Create base humanoid mesh with proportions
- `apply_modifier` - Apply SUBSURF, SMOOTH, BEVEL, SOLIDIFY modifiers
- `setup_material` - Configure PBR materials (Principled BSDF)
- `execute_code` - Run arbitrary Blender Python code
- `export` - Export scene to GLB

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

## Recent Changes
- 2026-02-04: Integrated Blender MCP for advanced procedural generation
- 2026-02-04: Added Gemini AI for multi-step generation plan creation
- 2026-02-04: Implemented dual-mode generation (MCP primary, CLI fallback)
- 2026-02-04: Added custom GEMINI_API_KEY support via secrets

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
| `server/gemini.ts` | Gemini AI integration for prompt analysis (legacy) |
| `client/src/components/BabylonViewer.tsx` | 3D model viewer component |

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

## Recent Changes
- 2026-02-04: **Migrated to GCP Worker architecture** - Remote Blender server for reliable 3D generation
  - Removed local Blender MCP/CLI execution (Replit headless limitations)
  - Added HTTP client with timeout (2 min), GLB validation, error handling
  - GCP Worker at `http://34.134.82.224:5000/generate`
- 2026-02-04: Added UI style selector with 7 proportion types and 4 poly levels
- 2026-02-04: Implemented character generation with Mixamo FBX base meshes
- 2026-02-04: Added Korean language support for color terms and prompts

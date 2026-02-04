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
- **Job Processing**: Asynchronous job queue pattern - jobs are created, then processed in background via Blender subprocess

### Data Storage
- **Schema Definition**: Drizzle ORM with PostgreSQL dialect (`shared/schema.ts`)
- **Current Implementation**: In-memory storage (`MemStorage` class) for development
- **Database Ready**: Drizzle config points to `DATABASE_URL` environment variable for PostgreSQL
- **Job Table**: Stores job ID, prompt, status (pending/processing/completed/failed), model URL, error message, and timestamp

### 3D Model Generation Pipeline
- **Generator**: Python script (`scripts/generate_humanoid.py`) runs in Blender's background mode
- **Process Flow**: Express spawns Blender subprocess → Blender generates humanoid mesh → Exports GLB file → Updates job status
- **Output Location**: Generated models saved to `public/models/` directory
- **Model Format**: GLB (binary glTF) for efficient loading in Babylon.js viewer

### Build System
- **Client Build**: Vite compiles React app to `dist/public`
- **Server Build**: esbuild bundles server with selective dependency bundling for faster cold starts
- **Database Migrations**: `drizzle-kit push` for schema synchronization

## External Dependencies

### Core Services
- **PostgreSQL**: Database backend (configured via `DATABASE_URL` environment variable, uses Drizzle ORM)
- **Blender**: External 3D software required for model generation (must be installed and available in PATH)

### Frontend Libraries
- **Babylon.js**: 3D rendering engine with glTF/GLB loader support
- **Radix UI**: Headless UI component primitives (dialog, dropdown, tabs, etc.)
- **TanStack Query**: Async state management with polling for job status updates
- **date-fns**: Date formatting with Korean locale support

### Backend Libraries
- **Drizzle ORM**: Type-safe database queries with PostgreSQL driver
- **Express Session**: Session management with connect-pg-simple for PostgreSQL session store
- **Zod**: Runtime schema validation for API inputs
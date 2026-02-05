# Akku Engine - AI 3D Character Generator

## Overview

Akku Engine is an AI-powered platform for generating game-ready 3D humanoid characters from text prompts. It produces GLB assets suitable for various game engines. The project aims to provide an accessible and efficient solution for 3D content creation, leveraging AI for creative assistance and automated asset generation.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend
- **Technology**: React 18 with TypeScript, Vite, Wouter for routing, TanStack React Query for state management.
- **UI/UX**: shadcn/ui component library, Tailwind CSS for styling with dark/light mode, Babylon.js for 3D model viewing.

### Backend
- **Technology**: Express.js with TypeScript, Node.js.
- **API**: RESTful endpoints, integrated with Vite for development and esbuild for production bundling.
- **Job Processing**: Asynchronous job queue for background 3D model generation.

### Data Storage
- **ORM**: Drizzle ORM with PostgreSQL dialect for schema definition.
- **Current State**: In-memory storage for development, but configured for PostgreSQL.
- **Job Management**: Stores generation job details (ID, prompt, status, model URL).

### 3D Model Generation Pipeline (GCP Worker)
- **Architecture**: Leverages a remote GCP Worker server to run Blender for 3D model generation, bypassing local headless Blender limitations.
- **Process Flow**: 
    1. Replit backend receives text prompt from user
    2. Gemini analyzes prompt via `mapPromptToParameters()` to extract SDK parameters (bodyType, style, equipment, shader)
    3. Parameters are sent to GCP Worker as `geminiParams` JSON
    4. GCP Worker parses and passes parameters to Blender SDK
    5. GLB file is returned to Replit and served to frontend
- **SDK**: Utilizes a modular Akku SDK (v5.0) with **Extrude-First Policy** for procedural character building, featuring:
    - **Extrude-First Unified Mesh**: Core design principle - all body parts (head, arms, legs) are extruded from a single base torso mesh, creating a single connected mesh instead of separate primitives. This produces organic, natural-looking characters.
    - Procedural Humanoid Generation: Creates characters from scratch with various styles (realistic, stylized, chibi, etc.) and polygon levels (ultra_low to high). Includes auto-rigging.
    - BMesh Direct Manipulation Tools: Low-level mesh editing primitives for precise control.
    - Atomic Operations System: Feature-based SDK with operations like `RigAwareExtruder` and `EdgeLoopCutter`.
    - Geometric Precision Controls: Functions for symmetry, normal orientation, and transform spaces.
    - Game-Ready Atomic Operations: Tools for topology, semantic selection, and game optimization (merge doubles, triangulate, decimate).
    - AI-Friendly Macro Functions: High-level functions designed for LLM orchestration (e.g., `extrude_and_scale`, `optimize_for_game`).
    - Auto Weight Transfer System: Uses Data Transfer modifier for equipment to deform with animations.
    - Kitbash 2.0 Semantic Component Library: AI-driven equipment system with semantic part definitions and precise attachment.
    - Stylized Shader System: Procedural material system for low-poly characters (edge highlighting, cavity darkening, Fresnel).
    - Body Type System: 12 presets with Korean language support, using lattice/vertex deformation.

### AI Integration (Gemini)
- **Purpose**: Intelligent prompt-to-parameter mapping for SDK orchestration.
- **Functionality**:
    - `mapPromptToParameters()`: Analyzes text prompts and outputs precise SDK parameters (bodyType, style, shader, equipment)
    - `analyzeImage()`: Vision API for reference image analysis
    - `generateAkkuPlan()`: Multi-step generation planning for complex characters
    - `analyzeScreenshotForRefinement()`: VLM-based self-verification for autonomous agent loop
- **Parameter Schema**: AkkuSDKParameters interface with validated fields for bodyType (preset, muscular, fat, height), style (proportionType, polyLevel, gender), shader (baseColor, metallic, roughness), equipment (helmet, shoulders, chest, weapon)
- **Korean Support**: Recognizes Korean keywords for archetypes (전사, 마법사, 기사, 도적) and body types

### Autonomous 3D Agent (v4.0)
- **Self-Verification Loop**: Iterative generation with Gemini VLM analysis
- **Process Flow**:
    1. Get initial parameters from `mapPromptToParameters()`
    2. Generate character with GCP Worker (with screenshot capture)
    3. Fetch screenshot and send to Gemini VLM for analysis
    4. If not satisfactory, apply refinements and repeat (up to 3 iterations)
    5. Return final GLB when satisfactory or max iterations reached
- **Endpoints**:
    - `POST /api/jobs/iterative`: Orchestrates the full iterative loop
    - `GET /api/iterative/:sessionId/screenshot/:iteration`: Fetch iteration screenshot
- **Screenshot Handler**: Headless-safe Eevee rendering with auto-framing based on mesh bounds
- **LLM-Friendly Tools**: JSON schemas in LLM_TOOLS.md for SDK tool documentation

### Build System
- **Client**: Vite for React application.
- **Server**: esbuild for bundling with selective dependency bundling.
- **Database**: Drizzle-kit for schema migrations.

## External Dependencies

### Core Services
- **GCP Worker**: Remote Blender server at `http://34.69.185.91:5000` for 3D model generation.
- **PostgreSQL**: Database backend (configured via `DATABASE_URL`).
- **Gemini API**: Google AI for prompt analysis and generation planning.

### Frontend Libraries
- **Babylon.js**: 3D rendering engine.
- **Radix UI**: Headless UI component primitives.
- **TanStack Query**: Asynchronous state management.
- **date-fns**: Date formatting.

### Backend Libraries
- **Drizzle ORM**: Type-safe database queries.
- **Express Session**: Session management.
- **Zod**: Runtime schema validation.
- **@google/genai**: Google Generative AI SDK.
# Akku Engine - System Architecture v1.0

## Overview

Akku Engine은 AI 기반 3D 캐릭터 생성 시스템입니다. 사용자 프롬프트를 받아 Gemini가 분석하고, GCP Worker에서 Blender SDK를 실행하여 GLB 파일을 생성합니다.

## System Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           REPLIT ENVIRONMENT                            │
├────────────────────────────────┬────────────────────────────────────────┤
│         FRONTEND               │              BACKEND                   │
│   (React + TypeScript)         │        (Express + TypeScript)          │
│                                │                                        │
│  client/src/                   │  server/                               │
│  ├── pages/Home.tsx           │  ├── routes.ts                         │
│  ├── components/              │  ├── gemini.ts                         │
│  │   └── ModelViewer.tsx      │  ├── storage.ts                        │
│  └── lib/queryClient.ts       │  └── index.ts                          │
│                                │                                        │
│  [User Prompt Input]           │  [API Endpoints]                       │
│         │                      │         │                              │
│         └──────────────────────┼─────────┘                              │
│                                │                                        │
└────────────────────────────────┴────────────────────────────────────────┘
                                 │
                                 │ HTTP POST /api/jobs
                                 │ HTTP GET /api/jobs/:id
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        GCP WORKER (VM Instance)                         │
│                     http://34.134.82.224:5000                           │
├─────────────────────────────────────────────────────────────────────────┤
│  server/gcp-app.py (Flask)                                              │
│                                                                         │
│  Endpoints:                                                             │
│  ├── GET  /health          - Health check                               │
│  ├── GET  /tools           - List SDK tools (JSON schema)               │
│  ├── POST /generate        - Generate character                         │
│  └── POST /generate_iterative - Autonomous agent loop                   │
│                                                                         │
│  Process:                                                               │
│  1. Receive JSON request                                                │
│  2. Parse parameters (style, polyLevel, gender, bodyType, equipment)    │
│  3. Build Blender command line                                          │
│  4. Execute: blender --background --python run.py -- [args]             │
│  5. Return GLB binary response                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ subprocess.run()
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          BLENDER SDK                                    │
│                     server/akku_sdk/                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  Entry Point:                                                           │
│  └── run.py → main.py → ToolRegistry.execute("generate_character")     │
│                                                                         │
│  Core Modules:                                                          │
│  ├── main.py          - CLI interface, tool registration               │
│  ├── procedural.py    - ProceduralHumanoid mesh generation              │
│  ├── body.py          - Body type presets & deformation                 │
│  ├── shader.py        - Stylized shader system                          │
│  ├── kitbash.py       - Equipment library                               │
│  ├── rigging.py       - Auto weight transfer                            │
│  ├── handlers.py      - FBX/GLB import/export, screenshots              │
│  └── mesh.py          - Low-level mesh tools                            │
│                                                                         │
│  Generation Flow:                                                       │
│  1. generate_procedural_base() - Create base humanoid mesh              │
│  2. apply_body_type() - Apply body type deformations                    │
│  3. apply_stylized_shader() - Apply materials/colors                    │
│  4. equip_items() - Attach equipment (optional)                         │
│  5. export_glb() - Export to GLB format                                 │
└─────────────────────────────────────────────────────────────────────────┘

## Data Flow

```
USER INPUT                    GEMINI ANALYSIS               GCP GENERATION
─────────────────────────────────────────────────────────────────────────────

"SF 로봇 전사,               mapPromptToParameters()        /generate endpoint
 메탈릭 블루 아머"           
        │                           │                              │
        ▼                           ▼                              ▼
┌──────────────────┐    ┌────────────────────────┐    ┌────────────────────┐
│ User Prompt      │───▶│ AkkuSDKParameters      │───▶│ Blender CLI Args   │
│ (natural lang)   │    │ {                      │    │                    │
└──────────────────┘    │   bodyType: {          │    │ prompt: "SF..."    │
                        │     preset: "muscular", │    │ style: "stylized"  │
                        │     muscular: 0.8      │    │ polyLevel: "medium"│
                        │   },                   │    │ bodyType: {...}    │
                        │   style: {             │    │ equipment: "armor" │
                        │     proportionType:    │    │ geminiParams: {...}│
                        │       "stylized"       │    │                    │
                        │   },                   │    └────────────────────┘
                        │   equipment: {         │              │
                        │     armorStyle: "scifi"│              ▼
                        │   },                   │    ┌────────────────────┐
                        │   shader: {            │    │ Generated GLB      │
                        │     baseColor: [...]   │    │ (binary file)      │
                        │   }                    │    └────────────────────┘
                        │ }                      │
                        └────────────────────────┘
```

## API Specification

### Replit Backend → GCP Worker

**POST /generate**
```json
Request:
{
  "prompt": "string - character description",
  "style": "realistic|stylized|chibi|sd|mobile|minifig|cartoon",
  "polyLevel": "ultra_low|low|medium|high",
  "jobId": "string - unique job identifier",
  "gender": "male|female|neutral",
  "bodyType": "JSON string - {preset, muscular, fat, height, ...}",
  "equipment": "default|armor|robe",
  "geminiParams": "JSON string - full Gemini analysis",
  "captureScreenshot": "boolean",
  "sessionId": "string - for iterative generation",
  "iteration": "number - current iteration"
}

Response:
- Success: Binary GLB file (model/gltf-binary)
- Error: JSON { "error": "message" }
```

### GCP Worker → Blender SDK

**Command Line Arguments:**
```bash
blender --background --python run.py -- \
  <prompt> \
  <style> \
  <poly_level> \
  <output_path> \
  [gender] \
  [body_type_json] \
  [use_remesh] \
  [equipment] \
  [gemini_params_json] \
  [screenshot_path]
```

## File Structure

```
akku-engine/
├── client/                    # React Frontend
│   └── src/
│       ├── pages/
│       │   └── Home.tsx      # Main UI
│       └── components/
│           └── ModelViewer.tsx  # Babylon.js 3D viewer
│
├── server/                    # Express Backend
│   ├── routes.ts             # API endpoints
│   ├── gemini.ts             # Gemini AI integration
│   ├── storage.ts            # Job storage
│   ├── gcp-app.py            # GCP Worker Flask server
│   │
│   └── akku_sdk/             # Blender Python SDK
│       ├── run.py            # Entry point
│       ├── main.py           # CLI & tool registry
│       ├── procedural.py     # Mesh generation
│       ├── body.py           # Body types
│       ├── shader.py         # Materials
│       ├── kitbash.py        # Equipment
│       ├── handlers.py       # Import/Export
│       └── LLM_TOOLS.md      # AI documentation
│
├── public/
│   └── models/               # Generated GLB files
│
└── shared/
    └── schema.ts             # TypeScript types
```

## Connection Points to Verify

| # | From | To | Method | Endpoint/Path |
|---|------|-----|--------|---------------|
| 1 | Frontend | Backend | HTTP POST | /api/jobs |
| 2 | Backend | Gemini | API Call | mapPromptToParameters() |
| 3 | Backend | GCP Worker | HTTP POST | /generate |
| 4 | GCP Worker | Blender | subprocess | run.py |
| 5 | Blender | SDK | Python import | main.py |
| 6 | SDK | Procedural | Function call | ProceduralHumanoid.generate() |
| 7 | Blender | GCP Worker | File system | output.glb |
| 8 | GCP Worker | Backend | HTTP Response | Binary GLB |
| 9 | Backend | Public | File system | public/models/*.glb |
| 10 | Frontend | Public | HTTP GET | /models/*.glb |

## Current Issues (To Investigate)

1. **Connection #6: SDK → Procedural Generation**
   - ProceduralHumanoid.generate() may not be producing proper humanoid shapes
   - Output looks like stacked primitives instead of organic connected mesh

2. **Verification Needed:**
   - [ ] Is generate_unified_mesh() being called?
   - [ ] Are extrude operations working correctly?
   - [ ] Is the mesh topology correct?
   - [ ] Are body type deformations applied?

## Next Steps

1. Test SDK directly on GCP VM with manual Blender CLI
2. Verify each module outputs expected results
3. Fix core mesh generation before adding features

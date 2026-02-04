import { GoogleGenAI } from "@google/genai";
import type { AkkuGenerationPlan, CharacterGenerationPlan } from "./blender-mcp-client";

// Use custom API key from secrets, fallback to Replit AI Integrations
const apiKey = process.env.GEMINI_API_KEY || process.env.AI_INTEGRATIONS_GEMINI_API_KEY;
const baseUrl = process.env.GEMINI_API_KEY 
  ? undefined  // Use default Google API endpoint when using custom key
  : process.env.AI_INTEGRATIONS_GEMINI_BASE_URL;

const ai = new GoogleGenAI({
  apiKey: apiKey,
  ...(baseUrl && {
    httpOptions: {
      apiVersion: "",
      baseUrl: baseUrl,
    },
  }),
});

// ============================================================
// SDK PARAMETER SCHEMA - Strict Type Definitions
// ============================================================

// Strict union types for validation
export type BodyPreset = "default" | "muscular" | "thin" | "fat" | "tall" | "athletic" | "heroic" | "chibi" | "cute" | "slim" | "broad" | "stocky";
export type ProportionType = "stylized" | "chibi" | "sd" | "mobile" | "minifig" | "cartoon" | "realistic";
export type PolyLevel = "ultra_low" | "low" | "medium" | "high";
export type Gender = "male" | "female" | "neutral";
export type StylePreset = "stylized" | "chibi" | "heroic" | "cartoon" | "realistic" | "mobile" | "minifig" | "sd";
export type ArmorStyle = "none" | "light" | "heavy" | "scifi" | "magic" | "plate" | "leather" | "cloth";
export type Archetype = "warrior" | "knight" | "mage" | "rogue" | "robot" | "monster" | "chibi" | "civilian" | "humanoid";

// Equipment item types
export type HelmetType = "Knight_Helmet" | "SciFi_Helmet" | "Light_Hood" | null;
export type ShoulderType = "Knight_Shoulder" | "SciFi_Shoulder" | null;
export type ChestType = "Knight_Chestplate" | "SciFi_Chestplate" | null;
export type GauntletType = "Knight_Gauntlet" | null;
export type BootType = "Heavy_Boots" | "SciFi_Boots" | null;
export type WeaponType = "Knight_Sword" | "SciFi_Blaster" | "Staff" | null;
export type ShieldType = "Knight_Shield" | null;

// Valid value arrays for runtime validation
const VALID_BODY_PRESETS: BodyPreset[] = ["default", "muscular", "thin", "fat", "tall", "athletic", "heroic", "chibi", "cute", "slim", "broad", "stocky"];
const VALID_PROPORTION_TYPES: ProportionType[] = ["stylized", "chibi", "sd", "mobile", "minifig", "cartoon", "realistic"];
const VALID_POLY_LEVELS: PolyLevel[] = ["ultra_low", "low", "medium", "high"];
const VALID_GENDERS: Gender[] = ["male", "female", "neutral"];
const VALID_STYLE_PRESETS: StylePreset[] = ["stylized", "chibi", "heroic", "cartoon", "realistic", "mobile", "minifig", "sd"];
const VALID_ARMOR_STYLES: ArmorStyle[] = ["none", "light", "heavy", "scifi", "magic", "plate", "leather", "cloth"];
const VALID_ARCHETYPES: Archetype[] = ["warrior", "knight", "mage", "rogue", "robot", "monster", "chibi", "civilian", "humanoid"];
const VALID_HELMETS: (string | null)[] = ["Knight_Helmet", "SciFi_Helmet", "Light_Hood", null];
const VALID_SHOULDERS: (string | null)[] = ["Knight_Shoulder", "SciFi_Shoulder", null];
const VALID_CHESTS: (string | null)[] = ["Knight_Chestplate", "SciFi_Chestplate", null];
const VALID_GAUNTLETS: (string | null)[] = ["Knight_Gauntlet", null];
const VALID_BOOTS: (string | null)[] = ["Heavy_Boots", "SciFi_Boots", null];
const VALID_WEAPONS: (string | null)[] = ["Knight_Sword", "SciFi_Blaster", "Staff", null];
const VALID_SHIELDS: (string | null)[] = ["Knight_Shield", null];

export interface AkkuSDKParameters {
  bodyType: {
    preset: BodyPreset;
    muscular: number;
    fat: number;
    height: number;
    shoulderWidth: number;
    hipWidth: number;
  };
  style: {
    proportionType: ProportionType;
    polyLevel: PolyLevel;
    gender: Gender;
  };
  shader: {
    baseColor: [number, number, number];
    metallic: number;
    roughness: number;
    edgeBrightness: number;
    cavityDarkness: number;
    fresnelStrength: number;
    stylePreset: StylePreset;
  };
  equipment: {
    helmet: HelmetType;
    shoulders: ShoulderType;
    chest: ChestType;
    gauntlets: GauntletType;
    boots: BootType;
    weapon: WeaponType;
    shield: ShieldType;
    armorStyle: ArmorStyle;
  };
  archetype: Archetype;
  description: string;
}

// JSON Schema for validation
export const SDK_PARAMETER_SCHEMA = {
  type: "object",
  required: ["bodyType", "style", "shader", "equipment", "archetype", "description"],
  properties: {
    bodyType: {
      type: "object",
      required: ["preset", "muscular", "fat", "height", "shoulderWidth", "hipWidth"],
      properties: {
        preset: { type: "string", enum: ["default", "muscular", "thin", "fat", "tall", "athletic", "heroic", "chibi", "cute", "slim", "broad", "stocky"] },
        muscular: { type: "number", minimum: 0, maximum: 1 },
        fat: { type: "number", minimum: 0, maximum: 1 },
        height: { type: "number", minimum: 0.7, maximum: 1.3 },
        shoulderWidth: { type: "number", minimum: 0.7, maximum: 1.5 },
        hipWidth: { type: "number", minimum: 0.7, maximum: 1.3 }
      }
    },
    style: {
      type: "object",
      required: ["proportionType", "polyLevel", "gender"],
      properties: {
        proportionType: { type: "string", enum: ["stylized", "chibi", "sd", "mobile", "minifig", "cartoon", "realistic"] },
        polyLevel: { type: "string", enum: ["ultra_low", "low", "medium", "high"] },
        gender: { type: "string", enum: ["male", "female", "neutral"] }
      }
    },
    shader: {
      type: "object",
      required: ["baseColor", "metallic", "roughness", "stylePreset"],
      properties: {
        baseColor: { type: "array", items: { type: "number", minimum: 0, maximum: 1 }, minItems: 3, maxItems: 3 },
        metallic: { type: "number", minimum: 0, maximum: 1 },
        roughness: { type: "number", minimum: 0, maximum: 1 },
        edgeBrightness: { type: "number", minimum: 0, maximum: 2 },
        cavityDarkness: { type: "number", minimum: 0, maximum: 1 },
        fresnelStrength: { type: "number", minimum: 0, maximum: 1 },
        stylePreset: { type: "string", enum: ["stylized", "chibi", "heroic", "cartoon", "realistic", "mobile", "minifig", "sd"] }
      }
    },
    equipment: {
      type: "object",
      properties: {
        helmet: { type: ["string", "null"] },
        shoulders: { type: ["string", "null"] },
        chest: { type: ["string", "null"] },
        gauntlets: { type: ["string", "null"] },
        boots: { type: ["string", "null"] },
        weapon: { type: ["string", "null"] },
        shield: { type: ["string", "null"] },
        armorStyle: { type: "string", enum: ["none", "light", "heavy", "scifi", "magic", "plate", "leather", "cloth"] }
      }
    },
    archetype: { type: "string" },
    description: { type: "string" }
  }
};

// Prompt-to-Parameter Mapping Engine System Prompt
const PARAMETER_MAPPING_PROMPT = `You are the Akku Engine Parameter Mapping AI. Your role is to convert natural language character descriptions into precise SDK parameters.

## Your Task
Analyze the user's character description and output a STRICT JSON object with exact numerical values for the Akku Low-poly SDK.

## Output JSON Schema (FOLLOW EXACTLY)

{
  "bodyType": {
    "preset": "default|muscular|thin|fat|tall|athletic|heroic|chibi|cute|slim|broad|stocky",
    "muscular": 0.0-1.0,    // Muscle definition (0=none, 1=bodybuilder)
    "fat": 0.0-1.0,         // Body fat (0=thin, 1=overweight)
    "height": 0.7-1.3,      // Height multiplier (1.0=normal)
    "shoulderWidth": 0.7-1.5, // Shoulder width (1.0=normal)
    "hipWidth": 0.7-1.3     // Hip width (1.0=normal)
  },
  "style": {
    "proportionType": "stylized|chibi|sd|mobile|minifig|cartoon|realistic",
    "polyLevel": "ultra_low|low|medium|high",
    "gender": "male|female|neutral"
  },
  "shader": {
    "baseColor": [R, G, B], // RGB values 0.0-1.0
    "metallic": 0.0-1.0,    // Metal appearance
    "roughness": 0.0-1.0,   // Surface roughness
    "edgeBrightness": 0.0-2.0, // Edge highlighting intensity
    "cavityDarkness": 0.0-1.0, // Cavity/crease darkening
    "fresnelStrength": 0.0-1.0, // Rim lighting
    "stylePreset": "stylized|chibi|heroic|cartoon|realistic|mobile|minifig|sd"
  },
  "equipment": {
    "helmet": "Knight_Helmet|SciFi_Helmet|Light_Hood|null",
    "shoulders": "Knight_Shoulder|SciFi_Shoulder|null",
    "chest": "Knight_Chestplate|SciFi_Chestplate|null",
    "gauntlets": "Knight_Gauntlet|null",
    "boots": "Heavy_Boots|SciFi_Boots|null",
    "weapon": "Knight_Sword|SciFi_Blaster|Staff|null",
    "shield": "Knight_Shield|null",
    "armorStyle": "none|light|heavy|scifi|magic|plate|leather|cloth"
  },
  "archetype": "warrior|knight|mage|rogue|robot|monster|chibi|civilian",
  "description": "Brief description"
}

## Mapping Rules

### Character Archetypes → Body Type Presets
IMPORTANT: USE MAXIMUM VALUES (1.0) for dramatic visual differences! Don't be conservative!
| Archetype Keywords | Body Preset | Muscular | Fat | Shoulders | Style |
|-------------------|-------------|----------|-----|-----------|-------|
| 강력한/powerful/strong | heroic | 1.0 | 0.0 | 1.5 | stylized |
| 전사/warrior/fighter | muscular | 1.0 | 0.0 | 1.4 | stylized |
| 기사/knight/paladin | muscular | 0.9 | 0.1 | 1.4 | realistic |
| 마법사/mage/wizard | thin | 0.0 | 0.0 | 0.7 | stylized |
| 도적/rogue/assassin | athletic | 0.6 | 0.0 | 1.0 | stylized |
| 로봇/robot/mech | muscular | 0.8 | 0.0 | 1.3 | stylized |
| 몬스터/monster/beast | broad | 1.0 | 0.5 | 1.5 | cartoon |
| 치비/chibi/cute | chibi | 0.0 | 0.3 | 0.7 | chibi |
| 날씬한/slim/slender | slim | 0.0 | 0.0 | 0.7 | stylized |
| 뚱뚱한/fat/heavy | stocky | 0.0 | 1.0 | 1.0 | cartoon |
| 영웅/hero | heroic | 1.0 | 0.0 | 1.5 | stylized |

### Armor Style Mappings
| Keywords | Armor Style | Equipment Set |
|----------|-------------|---------------|
| 판금/plate/heavy armor | plate | Knight set (full) |
| 가죽/leather/light armor | leather | Light_Hood + boots |
| 천/cloth/robes | cloth | Light_Hood only |
| SF/scifi/tech/사이버 | scifi | SciFi set (full) |
| 마법/magic/enchanted | magic | Light_Hood + Staff |

### Material Mappings
| Keywords | Metallic | Roughness | Edge | Cavity |
|----------|----------|-----------|------|--------|
| 금속/metal/steel | 0.9 | 0.3 | 1.2 | 0.4 |
| 광택/shiny/polished | 0.7 | 0.1 | 1.5 | 0.3 |
| 무광/matte/dull | 0.2 | 0.8 | 0.8 | 0.5 |
| 가죽/leather | 0.1 | 0.6 | 0.9 | 0.6 |
| 천/cloth/fabric | 0.0 | 0.9 | 0.7 | 0.7 |
| 크롬/chrome/mirror | 1.0 | 0.05 | 1.8 | 0.2 |
| 금/gold/황금 | 0.95 | 0.2 | 1.4 | 0.3 |

### Korean Color Mappings
| 한글 | English | RGB |
|------|---------|-----|
| 빨간/빨강 | red | [0.8, 0.2, 0.2] |
| 파란/파랑 | blue | [0.2, 0.4, 0.8] |
| 녹색/초록 | green | [0.2, 0.7, 0.3] |
| 노란/노랑 | yellow | [0.9, 0.8, 0.2] |
| 보라 | purple | [0.6, 0.2, 0.8] |
| 주황 | orange | [0.9, 0.5, 0.1] |
| 분홍 | pink | [0.9, 0.5, 0.7] |
| 검은/검정 | black | [0.1, 0.1, 0.1] |
| 흰/하얀 | white | [0.95, 0.95, 0.95] |
| 금색/황금 | gold | [0.85, 0.65, 0.2] |
| 은색 | silver | [0.75, 0.75, 0.8] |
| 하늘색 | sky blue | [0.5, 0.8, 1.0] |
| 청록색 | cyan | [0.2, 0.8, 0.7] |
| 갈색 | brown | [0.4, 0.25, 0.1] |
| 회색 | gray | [0.5, 0.5, 0.5] |

### Poly Level Selection
| Keywords | Poly Level |
|----------|------------|
| 모바일/mobile/저폴리 | ultra_low |
| 가벼운/lightweight | low |
| 기본/default/standard | medium |
| 고품질/highquality/detailed | high |

## Examples

Input: "강력한 전사"
Output:
{
  "bodyType": {"preset": "heroic", "muscular": 1.0, "fat": 0.0, "height": 1.15, "shoulderWidth": 1.5, "hipWidth": 1.0},
  "style": {"proportionType": "stylized", "polyLevel": "medium", "gender": "male"},
  "shader": {"baseColor": [0.5, 0.5, 0.55], "metallic": 0.95, "roughness": 0.2, "edgeBrightness": 1.5, "cavityDarkness": 0.5, "fresnelStrength": 0.4, "stylePreset": "heroic"},
  "equipment": {"helmet": "Knight_Helmet", "shoulders": "Knight_Shoulder", "chest": "Knight_Chestplate", "gauntlets": "Knight_Gauntlet", "boots": "Heavy_Boots", "weapon": "Knight_Sword", "shield": "Knight_Shield", "armorStyle": "plate"},
  "archetype": "warrior",
  "description": "Powerful warrior with full plate armor and massive muscular build"
}

Input: "빨간 로봇"
Output:
{
  "bodyType": {"preset": "default", "muscular": 0.3, "fat": 0.0, "height": 1.0, "shoulderWidth": 1.1, "hipWidth": 0.95},
  "style": {"proportionType": "stylized", "polyLevel": "medium", "gender": "neutral"},
  "shader": {"baseColor": [0.8, 0.2, 0.2], "metallic": 0.95, "roughness": 0.2, "edgeBrightness": 1.5, "cavityDarkness": 0.3, "fresnelStrength": 0.4, "stylePreset": "stylized"},
  "equipment": {"helmet": "SciFi_Helmet", "shoulders": "SciFi_Shoulder", "chest": "SciFi_Chestplate", "gauntlets": null, "boots": "SciFi_Boots", "weapon": null, "shield": null, "armorStyle": "scifi"},
  "archetype": "robot",
  "description": "Red robot with sci-fi armor"
}

Input: "귀여운 치비 마법사"
Output:
{
  "bodyType": {"preset": "chibi", "muscular": 0.0, "fat": 0.2, "height": 0.75, "shoulderWidth": 0.8, "hipWidth": 0.9},
  "style": {"proportionType": "chibi", "polyLevel": "medium", "gender": "neutral"},
  "shader": {"baseColor": [0.6, 0.2, 0.8], "metallic": 0.1, "roughness": 0.7, "edgeBrightness": 0.9, "cavityDarkness": 0.5, "fresnelStrength": 0.5, "stylePreset": "chibi"},
  "equipment": {"helmet": "Light_Hood", "shoulders": null, "chest": null, "gauntlets": null, "boots": null, "weapon": "Staff", "shield": null, "armorStyle": "cloth"},
  "archetype": "mage",
  "description": "Cute chibi mage with purple robes and staff"
}

## Rules
1. Output ONLY valid JSON, no explanations or markdown
2. All numeric values must be within specified ranges
3. Use null for equipment slots that should be empty
4. Match Korean keywords first, then English
5. Combine multiple attributes when present (e.g., "강력한 빨간 기사" = powerful + red + knight)
6. Default to "stylized" proportionType and "medium" polyLevel if not specified`;

// ============================================================
// AKKU LOW-POLY SDK SYSTEM PROMPT
// ============================================================

const AKKU_SDK_PROMPT = `You are the Akku Engine procedural artist AI. You convert natural language character descriptions into structured generation plans using the Akku Low-poly SDK.

## Akku SDK API Reference

You can ONLY use these 8 tools organized in 4 categories:

### Category 1: Base Generation (구조적 안정성)

#### spawn_humanoid_base
Load Mixamo Y Bot or X Bot as base mesh with proportion adjustments.
{
  "action": "spawn_humanoid_base",
  "params": { 
    "proportion_type": "sd|stylized|realistic|chibi|mobile|minifig|cartoon",
    "poly_level": "ultra_low|low|medium|high",  // Optional, default: "medium"
    "gender": "neutral|male|female"  // Optional, default: "neutral"
  },
  "description": "Load Y Bot with chibi proportions"
}

Gender options:
- "neutral" or "female": Y Bot (slimmer silhouette)
- "male": X Bot (broader build)

Proportion types (NOTE: All types use same Mixamo mesh, only affects uniform scale):
- "sd": Smaller scale (0.7x) for super-deformed style
- "stylized": Default scale (1.0x), versatile
- "realistic": Default scale (1.0x), human-like
- "chibi": Smaller scale (0.7x) for cute style
- "mobile": Smaller scale (0.8x) for mobile games
- "minifig": Smallest scale (0.6x) for block style
- "cartoon": Slightly smaller scale (0.9x)

Poly levels:
- "ultra_low": ~300 triangles, for mobile games
- "low": ~800 triangles, for low-end devices
- "medium": ~1500 triangles, balanced quality
- "high": ~3000 triangles, for PC/console

#### deform_body (LIMITED - use sparingly)
Scale the entire body mesh. Note: Individual body part scaling is not supported with Mixamo meshes.
{
  "action": "deform_body",
  "params": { 
    "part": "body",  // Only "body" is reliably supported
    "strength": 0.5,  // -1.0 to 1.0
    "deform_type": "scale"  // Only "scale" is reliably supported
  },
  "description": "Scale entire body larger"
}
NOTE: This tool has LIMITED functionality. Prefer using different proportion_type values instead.

### Category 2: Hard-Surface Kitbashing (디테일 상향)

#### attach_armor_plate
Attach armor/accessory parts at key locations.
{
  "action": "attach_armor_plate",
  "params": {
    "location": "left_shoulder|right_shoulder|chest|back|left_knee|right_knee|left_gauntlet|right_gauntlet|helmet|belt|left_boot|right_boot",
    "style": "shoulder_pad|chest_plate|knee_guard|gauntlet|helmet_visor|belt_buckle|boot_plate",
    "scale": 1.0  // Size multiplier
  },
  "description": "Attach shoulder armor"
}

#### add_scifi_detail
Add procedural panel lines and sci-fi details.
{
  "action": "add_scifi_detail",
  "params": {
    "target_obj": "ObjectName",  // e.g., "Armor_chest_chest_plate"
    "detail_level": "low|medium|high"
  },
  "description": "Add panel details to chest plate"
}

### Category 3: Game-Ready PBR Shading (질감 완성)

#### apply_akku_pbr
Apply a PBR material preset.
{
  "action": "apply_akku_pbr",
  "params": {
    "object_name": "ObjectName",
    "preset_name": "metal|brushed_metal|plastic|rubber|cloth|leather|skin|glow|chrome|gold",
    "base_color": [R, G, B]  // Optional, 0-1 range
  },
  "description": "Apply chrome material to armor"
}

PBR Presets:
- "metal": Standard metallic, semi-reflective
- "brushed_metal": Matte metal with directional grain
- "plastic": Shiny non-metal, colored
- "rubber": Matte, soft feel
- "cloth": Fabric texture, diffuse
- "leather": Organic leather look
- "skin": Character skin with subsurface
- "glow": Emissive material
- "chrome": Mirror-like reflection
- "gold": Warm metallic gold

#### set_material_property
Fine-tune PBR values on existing material.
{
  "action": "set_material_property",
  "params": {
    "object_name": "ObjectName",
    "metallic": 0.9,   // 0.0 to 1.0
    "roughness": 0.2,  // 0.0 to 1.0
    "emission": 0      // Emission strength
  },
  "description": "Increase metallic value"
}

### Category 4: Finalize & Animation (플레이 가능)

#### finalize_and_bind (OPTIONAL - Mixamo already has rigging)
Finalize mesh and prepare for export. Note: Mixamo FBX meshes are already rigged.
{
  "action": "finalize_and_bind",
  "params": {},
  "description": "Finalize mesh for export"
}

#### test_animation
Apply test animation clip for verification.
{
  "action": "test_animation",
  "params": { "clip_name": "idle|walk|attack|jump" },
  "description": "Test walk animation"
}

### Export (항상 마지막)

{
  "action": "export",
  "params": {},
  "description": "Export GLB model"
}

## Output Format

Return ONLY valid JSON:
{
  "characterType": "robot|warrior|fantasy|creature|chibi|humanoid",
  "description": "Brief character description",
  "steps": [ ... step objects ... ]
}

## Guidelines

### Character Archetypes
- Robot/Mech: stylized/realistic base + armor plates + metal/chrome materials
- Warrior/Knight: stylized base + armor (shoulders, chest, gauntlets) + brushed_metal
- Fantasy/Magic: stylized base + glow materials with emission
- Creature/Monster: sd/chibi base + organic materials (skip deform_body)
- Chibi/Cute: chibi base + minimal armor + plastic/colorful materials

### Korean Color Terms
- 빨간/빨강: [0.8, 0.2, 0.2]
- 파란/파랑: [0.2, 0.4, 0.8]
- 녹색/초록: [0.2, 0.7, 0.3]
- 노란/노랑: [0.9, 0.8, 0.2]
- 보라: [0.6, 0.2, 0.8]
- 주황: [0.9, 0.5, 0.1]
- 분홍: [0.9, 0.5, 0.7]
- 검은/검정: [0.1, 0.1, 0.1]
- 흰/하얀: [0.95, 0.95, 0.95]
- 금색: [0.85, 0.65, 0.2]
- 은색: [0.75, 0.75, 0.8]
- 하늘색: [0.5, 0.8, 1.0]
- 청록색: [0.2, 0.8, 0.7]

### Object Naming Convention (CRITICAL)
After spawn_humanoid_base, the following objects exist:
- AkkuBase_Armature (rigged skeleton with Mixamo bone hierarchy)
- AkkuBase_Surface (main character body mesh - always use this for materials)
- AkkuBase_Aux_* (auxiliary meshes like joints, eyes - usually not targeted)

For materials, ALWAYS target:
- "AkkuBase_Surface" for the main body mesh

IMPORTANT: The character is a single unified mesh, not separate body parts!

After attach_armor_plate:
- Armor_{location}_{style} (e.g., "Armor_chest_chest_plate")

### Best Practices
1. Always start with spawn_humanoid_base
2. SKIP deform_body unless scaling entire body is needed (Mixamo mesh is pre-proportioned)
3. Add armor plates in logical order (body center → extremities)
4. Apply materials AFTER all geometry is placed
5. finalize_and_bind is optional (Mixamo FBX already has rigging)
6. test_animation is optional, only if user requests animation
7. ALWAYS end with export

Output ONLY valid JSON, no explanations or markdown.`;

// Legacy interface for backward compatibility
export interface BlenderParams {
  skinColor: [number, number, number];
  bodyColor: [number, number, number];
  headScale: [number, number, number];
  torsoScale: [number, number, number];
  armLength: number;
  legLength: number;
  characterType: string;
  accessories: string[];
  materialType: "matte" | "metallic" | "glossy";
  roughness: number;
  metallic: number;
}

// Legacy procedural artist prompt (CLI fallback mode only - NOT compatible with Mixamo/MCP mode)
// Note: headScale/armLength/legLength parameters only work with procedural generation, not Mixamo FBX
const PROCEDURAL_ARTIST_PROMPT = `You are an expert Blender procedural artist AI. Your role is to convert natural language character descriptions into detailed, multi-step generation plans that leverage Blender's advanced features.

You output JSON generation plans with these step types:

## Step Types

### 1. create_base - Create the base character mesh
{
  "action": "create_base",
  "params": {
    "headScale": 1.0,
    "torsoScale": 1.0,
    "armLength": 1.0,
    "legLength": 1.0,
    "skinColor": [R, G, B],
    "bodyColor": [R, G, B],
    "roughness": 0.5,
    "metallic": 0.0
  },
  "description": "Create base humanoid with parameters"
}

### 2. apply_modifier - Apply mesh modifiers for detail
{
  "action": "apply_modifier",
  "target": "ObjectName",
  "params": {
    "type": "SUBSURF|SMOOTH|BEVEL|SOLIDIFY",
    "levels": 2,
    "factor": 0.5,
    "width": 0.02
  },
  "description": "Apply subdivision for smooth surface"
}

### 3. setup_material - Configure PBR materials
{
  "action": "setup_material",
  "target": "ObjectName",
  "params": {
    "name": "MaterialName",
    "color": [R, G, B],
    "metallic": 0.0,
    "roughness": 0.5
  },
  "description": "Apply metallic material to torso"
}

### 4. export - Final GLB export (always last step)
{
  "action": "export",
  "params": {},
  "description": "Export final GLB model"
}

## Output Format
{
  "characterType": "humanoid|robot|fantasy|creature|chibi",
  "description": "Brief description of the character",
  "steps": [...]
}

### Korean Color Terms
- 빨간/빨강: [0.8, 0.2, 0.2]
- 파란/파랑: [0.2, 0.4, 0.8]
- 녹색/초록: [0.2, 0.7, 0.3]
- 노란/노랑: [0.9, 0.8, 0.2]
- 검은/검정: [0.1, 0.1, 0.1]
- 흰/하얀: [0.95, 0.95, 0.95]
- 금색: [0.85, 0.65, 0.2]
- 은색: [0.75, 0.75, 0.8]

### Object Names for Targeting
After create_base: Head, Torso, Hips, Arm_L, Arm_R, Leg_L, Leg_R

ALWAYS end with the export step.
Output ONLY valid JSON, no explanations or markdown.`;

// Simple params system prompt (CLI fallback mode only - NOT compatible with Mixamo/MCP mode)
// Note: headScale/armLength/legLength parameters only work with procedural generation, not Mixamo FBX
const SIMPLE_PARAMS_PROMPT = `You are an AI assistant that converts natural language character descriptions into precise Blender parameters for generating 3D humanoid characters.

Given a character description, output ONLY valid JSON with these parameters:

{
  "skinColor": [R, G, B],
  "bodyColor": [R, G, B],
  "headScale": [X, Y, Z],
  "torsoScale": [X, Y, Z],
  "armLength": 1.0,
  "legLength": 1.0,
  "characterType": "human",
  "accessories": [],
  "materialType": "matte",
  "roughness": 0.5,
  "metallic": 0.0
}

Korean color terms:
- 빨간/빨강: [0.8, 0.2, 0.2]
- 파란/파랑: [0.2, 0.4, 0.8]
- 녹색/초록: [0.2, 0.7, 0.3]

For robots: metallic=0.9, roughness=0.2
For chibi: headScale=[1.5,1.5,1.5], armLength=0.6, legLength=0.6

Output ONLY the JSON, no explanations or markdown.`;

// ============================================================
// PROMPT-TO-PARAMETER MAPPING ENGINE
// ============================================================

/**
 * Map a natural language prompt to precise SDK parameters
 * Uses Gemini to convert abstract descriptions to concrete numerical values
 * 
 * @param prompt User's character description (Korean/English)
 * @param style Optional style override
 * @param polyLevel Optional poly level override
 * @returns AkkuSDKParameters with all generation parameters
 */
export async function mapPromptToParameters(
  prompt: string,
  style?: string,
  polyLevel?: string
): Promise<AkkuSDKParameters> {
  try {
    let userRequest = `Convert this character description to SDK parameters:\n\n"${prompt}"`;
    
    if (style) {
      userRequest += `\n\nUse proportionType: "${style}"`;
    }
    if (polyLevel) {
      userRequest += `\nUse polyLevel: "${polyLevel}"`;
    }

    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: [
        { role: "user", parts: [{ text: PARAMETER_MAPPING_PROMPT }] },
        { role: "model", parts: [{ text: "I understand. I will analyze character descriptions and output precise SDK parameter JSON following the strict schema." }] },
        { role: "user", parts: [{ text: userRequest }] },
      ],
    });

    const text = response.text || "";
    let jsonStr = extractJSON(text);
    const params = JSON.parse(jsonStr) as AkkuSDKParameters;
    
    // Validate and clamp parameters
    const validated = validateSDKParameters(params);
    
    console.log(`[Gemini] Mapped prompt to parameters:`, {
      archetype: validated.archetype,
      bodyPreset: validated.bodyType.preset,
      armorStyle: validated.equipment.armorStyle,
      color: validated.shader.baseColor
    });
    
    return validated;
  } catch (error) {
    console.error("Error mapping prompt to parameters:", error);
    return getDefaultSDKParameters(prompt);
  }
}

/**
 * Validate and clamp SDK parameters to valid ranges
 * Uses strict type validation for all enum fields
 */
function validateSDKParameters(params: AkkuSDKParameters): AkkuSDKParameters {
  // Helper to validate equipment items
  function validateEquipment<T>(value: unknown, validValues: (string | null)[], defaultValue: T): T {
    if (value === null || validValues.includes(value as string)) {
      return value as T;
    }
    return defaultValue;
  }
  
  return {
    bodyType: {
      preset: validateEnum<BodyPreset>(params.bodyType?.preset, VALID_BODY_PRESETS, "default"),
      muscular: clamp(params.bodyType?.muscular ?? 0.3, 0, 1),
      fat: clamp(params.bodyType?.fat ?? 0.1, 0, 1),
      height: clamp(params.bodyType?.height ?? 1.0, 0.7, 1.3),
      shoulderWidth: clamp(params.bodyType?.shoulderWidth ?? 1.0, 0.7, 1.5),
      hipWidth: clamp(params.bodyType?.hipWidth ?? 1.0, 0.7, 1.3),
    },
    style: {
      proportionType: validateEnum<ProportionType>(params.style?.proportionType, VALID_PROPORTION_TYPES, "stylized"),
      polyLevel: validateEnum<PolyLevel>(params.style?.polyLevel, VALID_POLY_LEVELS, "medium"),
      gender: validateEnum<Gender>(params.style?.gender, VALID_GENDERS, "neutral"),
    },
    shader: {
      baseColor: validateColor(params.shader?.baseColor, [0.5, 0.5, 0.55]),
      metallic: clamp(params.shader?.metallic ?? 0.3, 0, 1),
      roughness: clamp(params.shader?.roughness ?? 0.5, 0, 1),
      edgeBrightness: clamp(params.shader?.edgeBrightness ?? 1.0, 0, 2),
      cavityDarkness: clamp(params.shader?.cavityDarkness ?? 0.4, 0, 1),
      fresnelStrength: clamp(params.shader?.fresnelStrength ?? 0.3, 0, 1),
      stylePreset: validateEnum<StylePreset>(params.shader?.stylePreset, VALID_STYLE_PRESETS, "stylized"),
    },
    equipment: {
      helmet: validateEquipment<HelmetType>(params.equipment?.helmet, VALID_HELMETS, null),
      shoulders: validateEquipment<ShoulderType>(params.equipment?.shoulders, VALID_SHOULDERS, null),
      chest: validateEquipment<ChestType>(params.equipment?.chest, VALID_CHESTS, null),
      gauntlets: validateEquipment<GauntletType>(params.equipment?.gauntlets, VALID_GAUNTLETS, null),
      boots: validateEquipment<BootType>(params.equipment?.boots, VALID_BOOTS, null),
      weapon: validateEquipment<WeaponType>(params.equipment?.weapon, VALID_WEAPONS, null),
      shield: validateEquipment<ShieldType>(params.equipment?.shield, VALID_SHIELDS, null),
      armorStyle: validateEnum<ArmorStyle>(params.equipment?.armorStyle, VALID_ARMOR_STYLES, "none"),
    },
    archetype: validateEnum<Archetype>(params.archetype, VALID_ARCHETYPES, "humanoid"),
    description: params.description || "Character",
  };
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function validateEnum<T extends string>(value: unknown, validValues: T[], defaultValue: T): T {
  if (typeof value === "string" && validValues.includes(value as T)) {
    return value as T;
  }
  return defaultValue;
}

/**
 * Get default SDK parameters with prompt-based detection
 */
function getDefaultSDKParameters(prompt: string): AkkuSDKParameters {
  const lowerPrompt = prompt.toLowerCase();
  
  // Detect archetype with proper types
  let archetype: Archetype = "humanoid";
  let bodyPreset: BodyPreset = "default";
  let armorStyle: ArmorStyle = "none";
  let muscular = 0.3;
  let proportionType: ProportionType = "stylized";
  let stylePreset: StylePreset = "stylized";
  
  if (lowerPrompt.includes("전사") || lowerPrompt.includes("warrior") || lowerPrompt.includes("fighter")) {
    archetype = "warrior";
    bodyPreset = "muscular";
    armorStyle = "plate";
    muscular = 0.7;
    stylePreset = "heroic";
  } else if (lowerPrompt.includes("기사") || lowerPrompt.includes("knight")) {
    archetype = "knight";
    bodyPreset = "muscular";
    armorStyle = "heavy";
    muscular = 0.6;
    stylePreset = "heroic";
  } else if (lowerPrompt.includes("마법사") || lowerPrompt.includes("mage") || lowerPrompt.includes("wizard")) {
    archetype = "mage";
    bodyPreset = "thin";
    armorStyle = "cloth";
    muscular = 0.2;
    stylePreset = "stylized";
  } else if (lowerPrompt.includes("로봇") || lowerPrompt.includes("robot")) {
    archetype = "robot";
    armorStyle = "scifi";
    stylePreset = "stylized";
  } else if (lowerPrompt.includes("치비") || lowerPrompt.includes("chibi") || lowerPrompt.includes("귀여")) {
    archetype = "chibi";
    bodyPreset = "chibi";
    proportionType = "chibi";
    muscular = 0.0;
    stylePreset = "chibi";
  }
  
  // Detect color
  let baseColor: [number, number, number] = [0.5, 0.5, 0.55];
  if (lowerPrompt.includes("빨간") || lowerPrompt.includes("red")) {
    baseColor = [0.8, 0.2, 0.2];
  } else if (lowerPrompt.includes("파란") || lowerPrompt.includes("blue")) {
    baseColor = [0.2, 0.4, 0.8];
  } else if (lowerPrompt.includes("금") || lowerPrompt.includes("gold")) {
    baseColor = [0.85, 0.65, 0.2];
  } else if (lowerPrompt.includes("녹색") || lowerPrompt.includes("green")) {
    baseColor = [0.2, 0.7, 0.3];
  } else if (lowerPrompt.includes("보라") || lowerPrompt.includes("purple")) {
    baseColor = [0.6, 0.2, 0.8];
  }
  
  return {
    bodyType: {
      preset: bodyPreset,
      muscular: muscular,
      fat: 0.1,
      height: 1.0,
      shoulderWidth: muscular > 0.5 ? 1.2 : 1.0,
      hipWidth: 1.0,
    },
    style: {
      proportionType: proportionType,
      polyLevel: "medium",
      gender: "neutral",
    },
    shader: {
      baseColor: baseColor,
      metallic: armorStyle === "plate" || armorStyle === "scifi" ? 0.8 : 0.2,
      roughness: 0.4,
      edgeBrightness: 1.0,
      cavityDarkness: 0.4,
      fresnelStrength: 0.3,
      stylePreset: stylePreset,
    },
    equipment: {
      helmet: armorStyle === "plate" ? "Knight_Helmet" : armorStyle === "scifi" ? "SciFi_Helmet" : null,
      shoulders: armorStyle === "plate" ? "Knight_Shoulder" : armorStyle === "scifi" ? "SciFi_Shoulder" : null,
      chest: armorStyle === "plate" ? "Knight_Chestplate" : armorStyle === "scifi" ? "SciFi_Chestplate" : null,
      gauntlets: armorStyle === "plate" ? "Knight_Gauntlet" : null,
      boots: armorStyle === "plate" ? "Heavy_Boots" : armorStyle === "scifi" ? "SciFi_Boots" : null,
      weapon: archetype === "mage" ? "Staff" : armorStyle === "plate" ? "Knight_Sword" : null,
      shield: armorStyle === "plate" ? "Knight_Shield" : null,
      armorStyle: armorStyle,
    },
    archetype: archetype,
    description: prompt,
  };
}

/**
 * Generate an Akku SDK generation plan using Gemini
 * @param prompt User's character description
 * @param style Proportion type (sd, stylized, realistic, chibi, mobile, minifig, cartoon)
 * @param polyLevel Polygon density (ultra_low, low, medium, high)
 */
export async function generateAkkuPlan(
  prompt: string,
  style: string = "stylized",
  polyLevel: string = "medium"
): Promise<AkkuGenerationPlan> {
  try {
    const userRequest = `Create an Akku SDK generation plan for this character:

Character description: ${prompt}

Required parameters:
- Use proportion_type: "${style}"
- Use poly_level: "${polyLevel}"

Make sure spawn_humanoid_base includes both proportion_type and poly_level in its params.`;

    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: [
        { role: "user", parts: [{ text: AKKU_SDK_PROMPT }] },
        { role: "model", parts: [{ text: "I understand. I will analyze character descriptions and output Akku SDK generation plans using only the 8 approved tools across the 4 categories." }] },
        { role: "user", parts: [{ text: userRequest }] },
      ],
    });

    const text = response.text || "";
    
    // Extract JSON from response
    let jsonStr = extractJSON(text);
    const plan = JSON.parse(jsonStr) as AkkuGenerationPlan;
    
    // Validate steps exist
    if (!plan.steps || plan.steps.length === 0) {
      throw new Error("No generation steps in plan");
    }
    
    // Ensure the plan ends with export
    const lastStep = plan.steps[plan.steps.length - 1];
    if (lastStep.action !== 'export') {
      plan.steps.push({
        action: 'export',
        params: {},
        description: 'Export final GLB model'
      });
    }
    
    console.log(`Generated Akku plan with ${plan.steps.length} steps for: ${plan.description}`);
    return plan;
  } catch (error) {
    console.error("Error generating Akku plan with Gemini:", error);
    return getDefaultAkkuPlan(prompt);
  }
}

/**
 * Legacy: Generate a multi-step character generation plan using Gemini
 */
export async function generateCharacterPlan(prompt: string): Promise<CharacterGenerationPlan> {
  try {
    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: [
        { role: "user", parts: [{ text: PROCEDURAL_ARTIST_PROMPT }] },
        { role: "model", parts: [{ text: "I understand. I will analyze character descriptions and output detailed JSON generation plans with multiple steps for procedural 3D character creation in Blender." }] },
        { role: "user", parts: [{ text: `Create a detailed generation plan for this character:\n\n${prompt}` }] },
      ],
    });

    const text = response.text || "";
    
    let jsonStr = extractJSON(text);
    const plan = JSON.parse(jsonStr) as CharacterGenerationPlan;
    
    if (!plan.steps || plan.steps.length === 0) {
      throw new Error("No generation steps in plan");
    }
    
    const lastStep = plan.steps[plan.steps.length - 1];
    if (lastStep.action !== 'export') {
      plan.steps.push({
        action: 'export',
        params: {},
        description: 'Export final GLB model'
      });
    }
    
    return plan;
  } catch (error) {
    console.error("Error generating character plan with Gemini:", error);
    return getDefaultPlan(prompt);
  }
}

/**
 * Legacy function: Analyze prompt and return simple parameters
 */
export async function analyzePromptWithGemini(prompt: string): Promise<BlenderParams> {
  try {
    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: [
        { role: "user", parts: [{ text: SIMPLE_PARAMS_PROMPT }] },
        { role: "model", parts: [{ text: "I understand. I will analyze character descriptions and output only valid JSON with Blender parameters." }] },
        { role: "user", parts: [{ text: `Analyze this character description and output the Blender parameters as JSON:\n\n${prompt}` }] },
      ],
    });

    const text = response.text || "";
    let jsonStr = extractJSON(text);
    const params = JSON.parse(jsonStr) as BlenderParams;
    
    return {
      skinColor: validateColor(params.skinColor, [0.9, 0.75, 0.6]),
      bodyColor: validateColor(params.bodyColor, [0.2, 0.4, 0.8]),
      headScale: validateScale(params.headScale, [1.0, 1.0, 1.0]),
      torsoScale: validateScale(params.torsoScale, [1.0, 1.0, 1.0]),
      armLength: validateRange(params.armLength, 0.5, 1.5, 1.0),
      legLength: validateRange(params.legLength, 0.5, 1.5, 1.0),
      characterType: params.characterType || "human",
      accessories: Array.isArray(params.accessories) ? params.accessories : [],
      materialType: validateMaterialType(params.materialType),
      roughness: validateRange(params.roughness, 0, 1, 0.5),
      metallic: validateRange(params.metallic, 0, 1, 0.0),
    };
  } catch (error) {
    console.error("Error analyzing prompt with Gemini:", error);
    return getDefaultParams();
  }
}

function extractJSON(text: string): string {
  let jsonStr = text.trim();
  if (jsonStr.startsWith("```json")) {
    jsonStr = jsonStr.slice(7);
  }
  if (jsonStr.startsWith("```")) {
    jsonStr = jsonStr.slice(3);
  }
  if (jsonStr.endsWith("```")) {
    jsonStr = jsonStr.slice(0, -3);
  }
  return jsonStr.trim();
}

function validateColor(color: unknown, defaultColor: [number, number, number]): [number, number, number] {
  if (!Array.isArray(color) || color.length !== 3) return defaultColor;
  return color.map(v => Math.max(0, Math.min(1, Number(v) || 0))) as [number, number, number];
}

function validateScale(scale: unknown, defaultScale: [number, number, number]): [number, number, number] {
  if (!Array.isArray(scale) || scale.length !== 3) return defaultScale;
  return scale.map(v => Math.max(0.1, Math.min(3, Number(v) || 1))) as [number, number, number];
}

function validateRange(value: unknown, min: number, max: number, defaultValue: number): number {
  const num = Number(value);
  if (isNaN(num)) return defaultValue;
  return Math.max(min, Math.min(max, num));
}

function validateMaterialType(type: unknown): "matte" | "metallic" | "glossy" {
  if (type === "metallic" || type === "glossy") return type;
  return "matte";
}

function getDefaultParams(): BlenderParams {
  return {
    skinColor: [0.9, 0.75, 0.6],
    bodyColor: [0.2, 0.4, 0.8],
    headScale: [1.0, 1.0, 1.0],
    torsoScale: [1.0, 1.0, 1.0],
    armLength: 1.0,
    legLength: 1.0,
    characterType: "human",
    accessories: [],
    materialType: "matte",
    roughness: 0.5,
    metallic: 0.0,
  };
}

function getDefaultAkkuPlan(prompt: string): AkkuGenerationPlan {
  // Detect character type from prompt
  const lowerPrompt = prompt.toLowerCase();
  const isRobot = lowerPrompt.includes('robot') || lowerPrompt.includes('로봇') || lowerPrompt.includes('mech');
  const isWarrior = lowerPrompt.includes('warrior') || lowerPrompt.includes('knight') || lowerPrompt.includes('전사') || lowerPrompt.includes('기사');
  const isChibi = lowerPrompt.includes('chibi') || lowerPrompt.includes('치비') || lowerPrompt.includes('cute') || lowerPrompt.includes('귀여');
  
  let proportionType = 'stylized';
  let characterType = 'humanoid';
  let materialPreset = 'plastic';
  
  if (isRobot) {
    proportionType = 'stylized';
    characterType = 'robot';
    materialPreset = 'metal';
  } else if (isWarrior) {
    proportionType = 'realistic';
    characterType = 'warrior';
    materialPreset = 'brushed_metal';
  } else if (isChibi) {
    proportionType = 'chibi';
    characterType = 'chibi';
    materialPreset = 'plastic';
  }
  
  // Detect color from prompt
  let baseColor: [number, number, number] = [0.5, 0.5, 0.6];
  if (lowerPrompt.includes('파란') || lowerPrompt.includes('blue')) {
    baseColor = [0.2, 0.4, 0.8];
  } else if (lowerPrompt.includes('빨간') || lowerPrompt.includes('red')) {
    baseColor = [0.8, 0.2, 0.2];
  } else if (lowerPrompt.includes('금') || lowerPrompt.includes('gold')) {
    baseColor = [0.85, 0.65, 0.2];
    materialPreset = 'gold';
  }
  
  const steps: AkkuGenerationPlan['steps'] = [
    {
      action: 'spawn_humanoid_base',
      params: { proportion_type: proportionType, gender: 'neutral' },
      description: `Load Mixamo Y Bot with ${proportionType} proportions`
    },
    {
      action: 'apply_akku_pbr',
      params: { object_name: 'AkkuBase_Surface', preset_name: materialPreset, base_color: baseColor },
      description: `Apply ${materialPreset} material to character mesh`
    },
    {
      action: 'export',
      params: {},
      description: 'Export final GLB model'
    }
  ];
  
  // Add armor for robot/warrior
  if (isRobot || isWarrior) {
    steps.splice(2, 0, 
      {
        action: 'attach_armor_plate',
        params: { location: 'left_shoulder', style: 'shoulder_pad', scale: 1.0 },
        description: 'Attach left shoulder armor'
      },
      {
        action: 'attach_armor_plate',
        params: { location: 'right_shoulder', style: 'shoulder_pad', scale: 1.0 },
        description: 'Attach right shoulder armor'
      },
      {
        action: 'attach_armor_plate',
        params: { location: 'chest', style: 'chest_plate', scale: 1.0 },
        description: 'Attach chest armor'
      }
    );
  }
  
  return {
    characterType,
    description: prompt || "Default humanoid character",
    steps
  };
}

function getDefaultPlan(prompt: string): CharacterGenerationPlan {
  return {
    characterType: "humanoid",
    description: prompt || "Default humanoid character",
    steps: [
      {
        action: 'create_base',
        params: {
          headScale: 1.0,
          torsoScale: 1.0,
          armLength: 1.0,
          legLength: 1.0,
          skinColor: [0.9, 0.75, 0.6],
          bodyColor: [0.2, 0.4, 0.8],
          roughness: 0.5,
          metallic: 0.0
        },
        description: 'Create base humanoid character'
      },
      {
        action: 'apply_modifier',
        target: 'Head',
        params: { type: 'SUBSURF', levels: 1, render_levels: 2 },
        description: 'Smooth head mesh'
      },
      {
        action: 'apply_modifier',
        target: 'Torso',
        params: { type: 'SUBSURF', levels: 1, render_levels: 2 },
        description: 'Smooth torso mesh'
      },
      {
        action: 'export',
        params: {},
        description: 'Export final GLB model'
      }
    ]
  };
}

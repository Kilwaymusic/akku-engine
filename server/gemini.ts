import { GoogleGenAI } from "@google/genai";
import type { AkkuGenerationPlan, CharacterGenerationPlan } from "./blender-mcp-client";

// Primary AI client (user's key or Replit integration)
const primaryApiKey = process.env.GEMINI_API_KEY || process.env.AI_INTEGRATIONS_GEMINI_API_KEY;
const primaryBaseUrl = process.env.GEMINI_API_KEY 
  ? undefined  // Use default Google API endpoint when using custom key
  : process.env.AI_INTEGRATIONS_GEMINI_BASE_URL;

const ai = new GoogleGenAI({
  apiKey: primaryApiKey,
  ...(primaryBaseUrl && {
    httpOptions: {
      apiVersion: "",
      baseUrl: primaryBaseUrl,
    },
  }),
});

// Fallback AI client (Replit integration) - used when primary hits rate limit
const fallbackAi = process.env.GEMINI_API_KEY && process.env.AI_INTEGRATIONS_GEMINI_API_KEY
  ? new GoogleGenAI({
      apiKey: process.env.AI_INTEGRATIONS_GEMINI_API_KEY,
      httpOptions: {
        apiVersion: "",
        baseUrl: process.env.AI_INTEGRATIONS_GEMINI_BASE_URL || "",
      },
    })
  : null;

// Helper to detect rate limit errors
function isRateLimitError(error: unknown): boolean {
  if (error && typeof error === "object" && "status" in error) {
    return (error as { status: number }).status === 429;
  }
  return false;
}

// Model name mapping for Replit AI Integrations
function getModelForClient(model: string, isReplit: boolean): string {
  if (!isReplit) return model;
  // Replit AI integrations uses slightly different model names
  if (model === "gemini-2.5-flash") return "gemini-2.5-flash";
  if (model === "gemini-2.5-pro") return "gemini-2.5-pro";
  if (model === "gemini-2.0-flash") return "gemini-2.5-flash"; // Map 2.0 to 2.5 for Replit
  return model;
}

// Helper to call AI with automatic fallback on rate limit
async function generateContentWithFallback(
  model: string,
  contents: Array<{ role: string; parts: Array<{ text?: string; inlineData?: { mimeType: string; data: string } }> }>,
  config?: { responseMimeType?: string; responseSchema?: object }
): Promise<{ text: string | undefined }> {
  try {
    const response = await ai.models.generateContent({
      model,
      contents,
      config,
    });
    return { text: response.text };
  } catch (error) {
    if (isRateLimitError(error) && fallbackAi) {
      console.log("[Gemini] Primary API rate limited, using Replit AI Integration fallback...");
      const fallbackModel = getModelForClient(model, true);
      const response = await fallbackAi.models.generateContent({
        model: fallbackModel,
        contents,
        config,
      });
      return { text: response.text };
    }
    throw error;
  }
}

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
        height: { type: "number", minimum: -0.5, maximum: 0.5 },
        shoulderWidth: { type: "number", minimum: -1.0, maximum: 1.0 },
        hipWidth: { type: "number", minimum: -1.0, maximum: 1.0 }
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
const PARAMETER_MAPPING_PROMPT = `You are a creative 3D character artist AI for the Akku Low-poly Game Character Engine.

## Your Role
Interpret the user's character description and CREATIVELY determine all body proportions, colors, and equipment. 
Use your artistic judgment - there are no fixed mappings. Think like a character designer.

## Output Format (JSON only)
{
  "bodyType": {
    "preset": "default|muscular|thin|fat|athletic|heroic|chibi|slim|broad|stocky",
    "muscular": 0.0-1.0,         // Muscle definition (think: how muscular should this character look?)
    "fat": 0.0-1.0,              // Body fat level
    "height": -0.5 to +0.5,      // Height adjustment (0=average, positive=taller, negative=shorter)
    "shoulderWidth": -1.0 to +1.0, // Shoulder width (-1=very narrow, 0=normal, +1=very broad)
    "hipWidth": -1.0 to +1.0     // Hip width (-1=narrow, 0=normal, +1=wide)
  },
  "style": {
    "proportionType": "stylized|chibi|sd|mobile|minifig|cartoon|realistic",
    "polyLevel": "ultra_low|low|medium|high",
    "gender": "male|female|neutral"
  },
  "shader": {
    "baseColor": [R, G, B],      // Main color (0.0-1.0 each) - BE CREATIVE with colors!
    "metallic": 0.0-1.0,         // How metallic/shiny (armor=high, cloth=low)
    "roughness": 0.0-1.0,        // Surface texture (polished=low, matte=high)
    "edgeBrightness": 0.0-2.0,   // Edge highlighting for low-poly style
    "cavityDarkness": 0.0-1.0,   // Shadow in creases
    "fresnelStrength": 0.0-1.0,  // Rim lighting effect
    "stylePreset": "stylized|chibi|heroic|cartoon|realistic"
  },
  "equipment": {
    "helmet": "Knight_Helmet|SciFi_Helmet|Light_Hood|null",
    "shoulders": "Knight_Shoulder|SciFi_Shoulder|null",
    "chest": "Knight_Chestplate|SciFi_Chestplate|null",
    "gauntlets": "Knight_Gauntlet|null",
    "boots": "Heavy_Boots|SciFi_Boots|null",
    "weapon": "Knight_Sword|SciFi_Blaster|Staff|null",
    "shield": "Knight_Shield|null",
    "armorStyle": "none|plate|leather|cloth|scifi"
  },
  "archetype": "warrior|knight|mage|rogue|robot|monster|chibi|civilian|humanoid",
  "description": "Your artistic interpretation"
}

## Creative Guidelines (NOT rules - use your judgment!)

**Body Proportions - Think about the character's role and personality:**
- Strong fighters typically have broader shoulders and more muscle
- Agile characters are usually leaner with balanced proportions
- Magic users often appear more slender and graceful
- Consider how gender affects body shape naturally
- Exaggerate proportions for stylized/cartoon looks
- Use the FULL range of values (-1.0 to +1.0) for dramatic effect!

**Colors - Be expressive:**
- Choose colors that match the character's personality and role
- Consider cultural associations (fire=red, ice=blue, nature=green)
- Mix creative colors for unique characters
- Material affects appearance (metal is often gray/silver, leather is brown)

**Equipment - Match the character concept:**
- Choose equipment that fits the character's role and era
- Use null for slots that should be empty
- Sci-fi and medieval don't usually mix

## Examples (showing creative interpretation)

Input: "불의 마법사"
Output: {"bodyType":{"preset":"thin","muscular":0.2,"fat":0.0,"height":0.1,"shoulderWidth":-0.6,"hipWidth":-0.2},"style":{"proportionType":"stylized","polyLevel":"medium","gender":"neutral"},"shader":{"baseColor":[0.9,0.3,0.1],"metallic":0.1,"roughness":0.6,"edgeBrightness":1.2,"cavityDarkness":0.4,"fresnelStrength":0.6,"stylePreset":"stylized"},"equipment":{"helmet":"Light_Hood","shoulders":null,"chest":null,"gauntlets":null,"boots":null,"weapon":"Staff","shield":null,"armorStyle":"cloth"},"archetype":"mage","description":"Fire mage with warm orange-red robes, slender build befitting a magic user"}

Input: "거대한 오크 전사"
Output: {"bodyType":{"preset":"heroic","muscular":1.0,"fat":0.3,"height":0.5,"shoulderWidth":1.0,"hipWidth":0.4},"style":{"proportionType":"stylized","polyLevel":"medium","gender":"male"},"shader":{"baseColor":[0.4,0.5,0.3],"metallic":0.3,"roughness":0.7,"edgeBrightness":1.0,"cavityDarkness":0.6,"fresnelStrength":0.3,"stylePreset":"heroic"},"equipment":{"helmet":null,"shoulders":"Knight_Shoulder","chest":"Knight_Chestplate","gauntlets":"Knight_Gauntlet","boots":"Heavy_Boots","weapon":"Knight_Sword","shield":null,"armorStyle":"plate"},"archetype":"monster","description":"Massive orc warrior with greenish skin, extremely broad shoulders, intimidating presence"}

## Output Rules
1. Output ONLY valid JSON, no explanations
2. Be CREATIVE - don't just copy examples
3. Use the FULL range of parameter values for visual impact
4. Interpret the character concept artistically`;

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

    const response = await generateContentWithFallback(
      "gemini-2.5-flash",
      [
        { role: "user", parts: [{ text: PARAMETER_MAPPING_PROMPT }] },
        { role: "model", parts: [{ text: "I understand. I will analyze character descriptions and output precise SDK parameter JSON following the strict schema." }] },
        { role: "user", parts: [{ text: userRequest }] },
      ]
    );

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
      height: clamp(params.bodyType?.height ?? 0.0, -0.5, 0.5),
      shoulderWidth: clamp(params.bodyType?.shoulderWidth ?? 0.0, -1.0, 1.0),
      hipWidth: clamp(params.bodyType?.hipWidth ?? 0.0, -1.0, 1.0),
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
  
  // Determine gender from prompt
  const isFemale = lowerPrompt.includes("여") || lowerPrompt.includes("female") || 
                   lowerPrompt.includes("girl") || lowerPrompt.includes("princess") ||
                   lowerPrompt.includes("마녀") || lowerPrompt.includes("witch");
  const gender: Gender = isFemale ? "female" : "neutral";
  
  // Calculate shoulder width based on archetype and gender (delta format: -1.0 to +1.0)
  let shoulderWidth = 0.0;  // default: neutral
  let hipWidth = 0.0;
  
  if (archetype === "warrior" || archetype === "knight") {
    shoulderWidth = isFemale ? 0.3 : 1.0;  // Female warrior: moderate, Male warrior: maximum
    hipWidth = isFemale ? 0.2 : -0.2;
  } else if (archetype === "mage") {
    shoulderWidth = isFemale ? -1.0 : -0.8;  // Female mage: minimum, Male mage: narrow
    hipWidth = isFemale ? 0.3 : 0.0;
  } else if (archetype === "chibi") {
    shoulderWidth = -0.5;
    hipWidth = 0.0;
  }
  
  return {
    bodyType: {
      preset: bodyPreset,
      muscular: muscular,
      fat: 0.1,
      height: 0.0,  // delta: 0 = normal
      shoulderWidth: shoulderWidth,
      hipWidth: hipWidth,
    },
    style: {
      proportionType: proportionType,
      polyLevel: "medium",
      gender: gender,
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


// ============================================================
// AUTONOMOUS AGENT - SCREENSHOT ANALYSIS & REFINEMENT
// ============================================================

export interface ScreenshotAnalysis {
  satisfactory: boolean;
  issues: string[];
  refinements: Partial<AkkuSDKParameters>;
  confidence: number;
  reasoning: string;
}

export async function analyzeScreenshotForRefinement(
  screenshotBase64: string,
  originalPrompt: string,
  currentParams: Partial<AkkuSDKParameters>,
  iteration: number
): Promise<ScreenshotAnalysis> {
  const systemPrompt = `You are an expert 3D character evaluator for game assets. 
Analyze the screenshot of a generated 3D character and determine if it matches the user's requirements.

Original prompt: "${originalPrompt}"
Current iteration: ${iteration}/3
Current parameters: ${JSON.stringify(currentParams, null, 2)}

EVALUATION CRITERIA:
1. Body proportions match the archetype (warrior=muscular, mage=thin, etc.)
2. Style consistency (chibi should look cute with big head, realistic should look proportional)
3. Equipment presence if requested (armor, weapons, etc.)
4. Overall visual quality and silhouette readability

RESPOND WITH JSON:
{
  "satisfactory": boolean (true if character meets requirements, false if needs refinement),
  "issues": string[] (list of specific problems found),
  "refinements": {
    "bodyType": { ... changes to body params ... },
    "style": { ... changes to style params ... },
    "shader": { ... changes to shader params ... },
    "equipment": { ... changes to equipment params ... }
  },
  "confidence": number (0.0-1.0, how confident you are in the assessment),
  "reasoning": string (brief explanation of your analysis)
}

REFINEMENT GUIDELINES:
- Only include params that need changing (partial updates)
- Use small incremental adjustments (e.g., muscular: 0.6 -> 0.8)
- bodyType.muscular/fat/height are 0.0-1.0 range
- bodyType.shoulderWidth/hipWidth are 0.7-1.5 range
- Valid bodyType.preset values: default, muscular, thin, fat, tall, athletic, heroic, chibi
- Valid style.proportionType values: stylized, chibi, sd, mobile, minifig, cartoon, realistic
- Valid style.polyLevel values: ultra_low, low, medium, high

If the character looks good and matches the prompt, set satisfactory=true and leave refinements empty.`;

  try {
    const response = await generateContentWithFallback(
      "gemini-2.5-flash",
      [
        {
          role: "user",
          parts: [
            { text: systemPrompt },
            {
              inlineData: {
                mimeType: "image/png",
                data: screenshotBase64
              }
            }
          ]
        }
      ]
    );

    const text = response.text || "";
    
    // Extract JSON from response
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]) as ScreenshotAnalysis;
      
      // Validate refinements using existing sanitization logic
      if (parsed.refinements) {
        // Apply basic validation to the refinement params
        const sanitized: Partial<AkkuSDKParameters> = {};
        
        if (parsed.refinements.bodyType) {
          const bt = parsed.refinements.bodyType;
          sanitized.bodyType = {
            preset: VALID_BODY_PRESETS.includes(bt.preset as BodyPreset) ? bt.preset as BodyPreset : "default",
            muscular: Math.min(1.0, Math.max(0.0, bt.muscular ?? 0.3)),
            fat: Math.min(1.0, Math.max(0.0, bt.fat ?? 0.1)),
            height: Math.min(1.3, Math.max(0.7, bt.height ?? 1.0)),
            shoulderWidth: Math.min(1.5, Math.max(0.7, bt.shoulderWidth ?? 1.0)),
            hipWidth: Math.min(1.3, Math.max(0.7, bt.hipWidth ?? 1.0))
          };
        }
        
        if (parsed.refinements.style) {
          const st = parsed.refinements.style;
          sanitized.style = {
            proportionType: VALID_PROPORTION_TYPES.includes(st.proportionType as ProportionType) ? st.proportionType as ProportionType : "stylized",
            polyLevel: VALID_POLY_LEVELS.includes(st.polyLevel as PolyLevel) ? st.polyLevel as PolyLevel : "medium",
            gender: VALID_GENDERS.includes(st.gender as Gender) ? st.gender as Gender : "male"
          };
        }
        
        parsed.refinements = sanitized;
      }
      
      console.log(`[Gemini VLM] Screenshot analysis for iteration ${iteration}:`, {
        satisfactory: parsed.satisfactory,
        issues: parsed.issues,
        confidence: parsed.confidence
      });
      
      return parsed;
    }
    
    // Fallback if no JSON found
    return {
      satisfactory: true,
      issues: [],
      refinements: {},
      confidence: 0.5,
      reasoning: "Could not parse analysis, assuming acceptable"
    };
    
  } catch (error) {
    console.error("[Gemini VLM] Screenshot analysis failed:", error);
    
    // Return safe default on error
    return {
      satisfactory: true,
      issues: ["Analysis failed - using current parameters"],
      refinements: {},
      confidence: 0.0,
      reasoning: `Error: ${error instanceof Error ? error.message : String(error)}`
    };
  }
}

export async function runIterativeGeneration(
  prompt: string,
  maxIterations: number = 3
): Promise<{
  finalParams: AkkuSDKParameters;
  iterationsRun: number;
  analyses: ScreenshotAnalysis[];
}> {
  // Get initial params from prompt
  let currentParams = await mapPromptToParameters(prompt);
  const analyses: ScreenshotAnalysis[] = [];
  
  console.log(`[Iterative Generation] Starting with prompt: "${prompt}"`);
  console.log(`[Iterative Generation] Initial params:`, currentParams);
  
  // Note: Actual screenshot capture happens on GCP Worker
  // This function prepares the refinement loop logic for Replit-side orchestration
  
  return {
    finalParams: currentParams,
    iterationsRun: 0,
    analyses
  };
}

// ============================================================
// BLENDER CODE GENERATION - Headless-Safe Mesh Generation
// ============================================================

const BLENDER_CODE_GENERATION_PROMPT = `You are an expert Blender Python developer. Generate code for HEADLESS CLI environment (no GUI).

## 절대 원칙 (CRITICAL RULES)

### ❌ 절대 하지 말 것 (NEVER DO):
\`\`\`python
# WRONG: bpy.ops는 GUI 컨텍스트 필요, 헤드리스에서 에러 발생
bpy.ops.mesh.primitive_cube_add()  # context.area 에러!
bpy.ops.object.select_all()  # 화면 없으면 실패!
bpy.ops.transform.translate()  # 컨텍스트 에러!
\`\`\`

### ✅ 반드시 해야 할 것 (ALWAYS DO):
\`\`\`python
# CORRECT: bpy.data + bmesh 직접 조작 (헤드리스 안전)
mesh = bpy.data.meshes.new("MyMesh")
obj = bpy.data.objects.new("MyObject", mesh)
bpy.context.collection.objects.link(obj)

bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)  # bmesh.ops는 안전!
bm.to_mesh(mesh)
bm.free()
\`\`\`

## EXTRUDE-FIRST 방법론

The body MUST be ONE CONNECTED MESH. Start with a torso and EXTRUDE all parts:
- Head = extrude TOP face upward
- Arms = extrude SIDE faces outward  
- Legs = extrude BOTTOM face downward

Equipment/accessories CAN be separate objects.

## COMPLETE WORKING REFERENCE CODE

Study this code carefully. It creates a connected humanoid with proper extrusion:

\`\`\`python
import bpy
import bmesh
from mathutils import Vector, Matrix
import math

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_humanoid():
    """Create a connected low-poly humanoid using Extrude-First methodology"""
    
    mesh = bpy.data.meshes.new("Character")
    obj = bpy.data.objects.new("Character", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    bm = bmesh.new()
    
    # ========== TORSO (Starting Point) ==========
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.5, 0.25, 0.6), verts=bm.verts[:])
    bmesh.ops.translate(bm, vec=(0, 0, 1.0), verts=bm.verts[:])
    
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    # ========== HEAD (Extrude from TOP face) ==========
    # Find top face (highest Z normal)
    top_face = max(bm.faces, key=lambda f: f.normal.z)
    
    # Extrude neck
    ret = bmesh.ops.extrude_face_region(bm, geom=[top_face])
    new_verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, 0.15), verts=new_verts)
    bmesh.ops.scale(bm, vec=(0.7, 0.7, 1.0), verts=new_verts, space=Matrix.Translation(top_face.calc_center_median()))
    
    # Find new top face for head
    bm.faces.ensure_lookup_table()
    top_face = max(bm.faces, key=lambda f: f.calc_center_median().z)
    
    # Extrude head
    ret = bmesh.ops.extrude_face_region(bm, geom=[top_face])
    new_verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, 0.35), verts=new_verts)
    bmesh.ops.scale(bm, vec=(1.3, 1.2, 1.0), verts=new_verts, space=Matrix.Translation(top_face.calc_center_median()))
    
    # ========== ARMS (Extrude from SIDE faces) ==========
    bm.faces.ensure_lookup_table()
    
    # Find side faces on torso level (Z around 1.0)
    torso_faces = [f for f in bm.faces if 0.8 < f.calc_center_median().z < 1.4]
    left_face = max([f for f in torso_faces if f.normal.x < -0.5], key=lambda f: abs(f.normal.x), default=None)
    right_face = max([f for f in torso_faces if f.normal.x > 0.5], key=lambda f: abs(f.normal.x), default=None)
    
    # Extrude left arm
    if left_face:
        # Upper arm
        ret = bmesh.ops.extrude_face_region(bm, geom=[left_face])
        arm_verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
        bmesh.ops.scale(bm, vec=(0.6, 0.6, 0.6), verts=arm_verts, space=Matrix.Translation(left_face.calc_center_median()))
        bmesh.ops.translate(bm, vec=(-0.3, 0, 0), verts=arm_verts)
        
        # Forearm
        bm.faces.ensure_lookup_table()
        end_face = max([f for f in bm.faces if f.calc_center_median().x < -0.4], key=lambda f: -f.calc_center_median().x, default=None)
        if end_face:
            ret = bmesh.ops.extrude_face_region(bm, geom=[end_face])
            arm_verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, vec=(-0.35, 0, 0), verts=arm_verts)
            bmesh.ops.scale(bm, vec=(0.8, 0.8, 0.8), verts=arm_verts, space=Matrix.Translation(end_face.calc_center_median()))
    
    # Extrude right arm (mirror)
    bm.faces.ensure_lookup_table()
    torso_faces = [f for f in bm.faces if 0.8 < f.calc_center_median().z < 1.4]
    right_face = max([f for f in torso_faces if f.normal.x > 0.5], key=lambda f: f.normal.x, default=None)
    
    if right_face:
        ret = bmesh.ops.extrude_face_region(bm, geom=[right_face])
        arm_verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
        bmesh.ops.scale(bm, vec=(0.6, 0.6, 0.6), verts=arm_verts, space=Matrix.Translation(right_face.calc_center_median()))
        bmesh.ops.translate(bm, vec=(0.3, 0, 0), verts=arm_verts)
        
        bm.faces.ensure_lookup_table()
        end_face = max([f for f in bm.faces if f.calc_center_median().x > 0.4], key=lambda f: f.calc_center_median().x, default=None)
        if end_face:
            ret = bmesh.ops.extrude_face_region(bm, geom=[end_face])
            arm_verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, vec=(0.35, 0, 0), verts=arm_verts)
            bmesh.ops.scale(bm, vec=(0.8, 0.8, 0.8), verts=arm_verts, space=Matrix.Translation(end_face.calc_center_median()))
    
    # ========== LEGS (Extrude from BOTTOM) ==========
    bm.faces.ensure_lookup_table()
    bottom_face = min(bm.faces, key=lambda f: f.calc_center_median().z)
    
    # Split bottom into two for legs
    center = bottom_face.calc_center_median()
    ret = bmesh.ops.bisect_plane(bm, geom=bm.faces[:] + bm.edges[:] + bm.verts[:], 
                                  plane_co=(0, 0, 0.7), plane_no=(1, 0, 0))
    
    bm.faces.ensure_lookup_table()
    
    # Find left and right bottom faces
    bottom_faces = [f for f in bm.faces if f.calc_center_median().z < 0.75 and f.normal.z < -0.5]
    left_leg_face = min([f for f in bottom_faces if f.calc_center_median().x < 0], 
                        key=lambda f: f.calc_center_median().z, default=None)
    right_leg_face = min([f for f in bottom_faces if f.calc_center_median().x > 0], 
                         key=lambda f: f.calc_center_median().z, default=None)
    
    # Extrude left leg
    if left_leg_face:
        ret = bmesh.ops.extrude_face_region(bm, geom=[left_leg_face])
        leg_verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=(0, 0, -0.5), verts=leg_verts)
        
        bm.faces.ensure_lookup_table()
        end_face = min([f for f in bm.faces if f.calc_center_median().x < -0.05], 
                       key=lambda f: f.calc_center_median().z, default=None)
        if end_face:
            ret = bmesh.ops.extrude_face_region(bm, geom=[end_face])
            leg_verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, vec=(0, 0, -0.5), verts=leg_verts)
    
    # Extrude right leg
    if right_leg_face:
        ret = bmesh.ops.extrude_face_region(bm, geom=[right_leg_face])
        leg_verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=(0, 0, -0.5), verts=leg_verts)
        
        bm.faces.ensure_lookup_table()
        end_face = min([f for f in bm.faces if f.calc_center_median().x > 0.05], 
                       key=lambda f: f.calc_center_median().z, default=None)
        if end_face:
            ret = bmesh.ops.extrude_face_region(bm, geom=[end_face])
            leg_verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, vec=(0, 0, -0.5), verts=leg_verts)
    
    # ========== FINALIZE ==========
    bm.to_mesh(mesh)
    bm.free()
    
    # Flat shading for low-poly look
    for poly in mesh.polygons:
        poly.use_smooth = False
    
    # Material
    mat = bpy.data.materials.new(name="CharacterMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.5, 0.4, 0.35, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.8
    obj.data.materials.append(mat)
    
    return obj

# Execute
clear_scene()
create_humanoid()
\`\`\`

## YOUR TASK

Based on the reference code above, create a character matching the user's prompt. You MUST:

1. **Use Extrude-First**: Body must be ONE connected mesh (head, arms, legs extruded from torso)
2. **Add character-specific features** by modifying the extrusion sizes, adding more extrusions:
   - 늑대/wolf: Extrude pointed ears from head top, elongate snout forward
   - 로봇/robot: Boxy proportions, angular shapes
   - 엘프/elf: Slender proportions, extrude pointed ears from sides of head
   - 마법사/wizard: Add hood by scaling head top, add robe by widening lower torso
   - 전사/warrior: Broader shoulders, thicker arms
3. **Keep it low-poly**: 500-2000 triangles
4. **Set appropriate color**: Match the character concept
5. **Equipment is optional**: Weapons, staffs, etc. CAN be separate objects

## COLOR PALETTE
- Skin: (0.8, 0.6, 0.5, 1.0)
- Brown/leather: (0.4, 0.25, 0.15, 1.0)
- Green/forest: (0.3, 0.5, 0.2, 1.0)  
- Blue/magic: (0.3, 0.4, 0.7, 1.0)
- Metal/gray: (0.5, 0.5, 0.55, 1.0)
- Purple/mystical: (0.5, 0.3, 0.6, 1.0)

## 코드 생성 체크리스트 (MUST SATISFY)

Before outputting code, verify:
1. ✅ bpy.ops.mesh.primitive_* 사용하지 않음 (bmesh.ops 사용)
2. ✅ 모든 오브젝트를 bpy.context.collection.objects.link()로 씬에 추가
3. ✅ BMesh 작업 후 bm.to_mesh() 와 bm.free() 호출
4. ✅ 몸체는 단일 연결 메시 (Extrude-First)
5. ✅ 정점/면 수를 print()로 출력하여 검증 가능하게 함

## SAFE HELPER FUNCTIONS

Use these patterns for semantic face selection:
\`\`\`python
def get_top_face(bm):
    """가장 위쪽을 향하는 면 찾기"""
    bm.faces.ensure_lookup_table()
    return max(bm.faces, key=lambda f: f.calc_center_median().z if f.normal.z > 0.3 else -999)

def get_side_faces(bm, z_min, z_max):
    """측면 면들 찾기 (X 방향)"""
    bm.faces.ensure_lookup_table()
    faces = [f for f in bm.faces if z_min < f.calc_center_median().z < z_max]
    left = [f for f in faces if f.normal.x < -0.5]
    right = [f for f in faces if f.normal.x > 0.5]
    return left, right

def extrude_and_move(bm, face, direction, distance):
    """면을 뽑아서 이동"""
    ret = bmesh.ops.extrude_face_region(bm, geom=[face])
    new_verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
    vec = tuple(d * distance for d in direction)
    bmesh.ops.translate(bm, vec=vec, verts=new_verts)
    return new_verts
\`\`\`

## OUTPUT
Output ONLY valid Python code. No explanations. Include print() statements for vertex/face counts.`;

/**
 * Generate Blender Python code for a character based on prompt
 * This is the core of the Autonomous 3D Agent - Gemini directly controls Blender
 */
export async function generateBlenderCode(prompt: string): Promise<string> {
  console.log(`[Gemini Code Gen] Generating Blender code for: "${prompt}"`);
  
  const response = await generateContentWithFallback(
    "gemini-2.5-flash",
    [
      {
        role: "user",
        parts: [
          {
            text: `${BLENDER_CODE_GENERATION_PROMPT}

## USER REQUEST
Create a character based on this description: "${prompt}"

Generate the complete Blender Python code now. Output ONLY the Python code, nothing else.`
          }
        ]
      }
    ]
  );
  
  const text = response.text || "";
  
  // Extract Python code from response (handle markdown code blocks)
  let code = text;
  
  // Remove markdown code block markers if present
  const codeBlockMatch = text.match(/```python\n?([\s\S]*?)```/);
  if (codeBlockMatch) {
    code = codeBlockMatch[1];
  } else {
    // Try without language specifier
    const genericBlockMatch = text.match(/```\n?([\s\S]*?)```/);
    if (genericBlockMatch) {
      code = genericBlockMatch[1];
    }
  }
  
  // Validate code has minimum required elements
  const validationErrors: string[] = [];
  
  // Required imports
  if (!code.includes("import bpy")) {
    validationErrors.push("Missing 'import bpy'");
  }
  if (!code.includes("bmesh")) {
    validationErrors.push("Missing 'bmesh' operations");
  }
  
  // Required structure
  if (!code.includes("def create_character") && !code.includes("def create_")) {
    validationErrors.push("Missing create_character() or create_* function");
  }
  
  // Check for mesh creation
  if (!code.includes("bpy.data.meshes.new") && !code.includes("bmesh.new()")) {
    validationErrors.push("Missing mesh creation");
  }
  
  // Security: Block dangerous modules
  const dangerousPatterns = [
    /import\s+os(?:\s|$|\.)/,
    /import\s+subprocess/,
    /import\s+sys(?:\s|$|\.)/,
    /from\s+os\s+import/,
    /exec\s*\(/,
    /eval\s*\(/,
    /__import__/,
    /open\s*\([^)]*['"](\/|\\)/,  // Absolute path file access
    /shutil/,
    /socket/,
    /urllib/,
    /requests/
  ];
  
  for (const pattern of dangerousPatterns) {
    if (pattern.test(code)) {
      validationErrors.push(`Security: Blocked pattern detected: ${pattern.source}`);
    }
  }
  
  if (validationErrors.length > 0) {
    console.error("[Gemini Code Gen] Validation failed:", validationErrors);
    throw new Error(`Generated code failed validation: ${validationErrors.join(", ")}`);
  }
  
  console.log(`[Gemini Code Gen] Generated ${code.length} characters of code (validated)`);
  
  return code.trim();
}

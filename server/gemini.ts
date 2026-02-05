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
// BLENDER CODE GENERATION - Simple & Robust Template
// ============================================================

const BLENDER_CODE_GENERATION_PROMPT = `You are an EXPERT 3D artist generating detailed Blender Python code for game-ready characters.

## YOUR GOAL
Create a visually appealing low-poly character with:
- Multiple colored parts (skin, hair, clothing, armor, accessories)
- Proper proportions matching the character type
- Distinctive features that match the prompt
- Multiple materials for different body parts

## OUTPUT RULES
- Output ONLY Python code (NO markdown, NO \`\`\`python blocks)
- Code must be complete and executable in Blender

## ADVANCED TEMPLATE - USE THIS STRUCTURE:

import bpy
import bmesh
from mathutils import Vector

# Scene cleanup
for obj in bpy.data.objects:
    bpy.data.objects.remove(obj, do_unlink=True)
for m in bpy.data.meshes:
    bpy.data.meshes.remove(m)
for mat in bpy.data.materials:
    bpy.data.materials.remove(mat)

def create_material(name, color, metallic=0.0, roughness=0.5):
    """Create a PBR material with given color"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_part(name, material):
    """Create a new mesh object with bmesh for a body part"""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    bm = bmesh.new()
    return obj, bm, mesh

def finish_part(bm, mesh):
    """Finalize bmesh to mesh"""
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.01)
    bm.to_mesh(mesh)
    bm.free()
    for p in mesh.polygons:
        p.use_smooth = False

def add_box(bm, pos, size):
    """Add a box primitive at position with given size"""
    r = bmesh.ops.create_cube(bm, size=1.0)
    for v in r['verts']:
        v.co.x = v.co.x * size[0] + pos[0]
        v.co.y = v.co.y * size[1] + pos[1]
        v.co.z = v.co.z * size[2] + pos[2]
    return r['verts']

def add_sphere(bm, pos, radius, segments=8, rings=6):
    """Add a UV sphere at position"""
    r = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    for v in r['verts']:
        v.co.x += pos[0]
        v.co.y += pos[1]
        v.co.z += pos[2]
    return r['verts']

def add_cone(bm, pos, radius, height, segments=8):
    """Add a cone primitive"""
    r = bmesh.ops.create_cone(bm, segments=segments, radius1=radius, radius2=0, depth=height, cap_ends=True)
    for v in r['verts']:
        v.co.x += pos[0]
        v.co.y += pos[1]
        v.co.z += pos[2] + height/2
    return r['verts']

def add_cylinder(bm, pos, radius, height, segments=8):
    """Add a cylinder primitive"""
    r = bmesh.ops.create_cone(bm, segments=segments, radius1=radius, radius2=radius, depth=height, cap_ends=True)
    for v in r['verts']:
        v.co.x += pos[0]
        v.co.y += pos[1]
        v.co.z += pos[2]
    return r['verts']

# === CREATE MATERIALS FOR EACH PART ===
# Examples - modify colors based on character description:
mat_skin = create_material("Skin", (0.85, 0.65, 0.55))           # Human skin
mat_hair = create_material("Hair", (0.15, 0.1, 0.08))            # Dark hair
mat_clothing = create_material("Clothing", (0.3, 0.35, 0.6))     # Blue fabric
mat_armor = create_material("Armor", (0.7, 0.7, 0.75), metallic=0.9, roughness=0.3)
mat_accent = create_material("Accent", (0.8, 0.2, 0.2))          # Red accent

# === BODY (skin material) ===
obj_body, bm, mesh = create_part("Body", mat_skin)

# Torso - use beveled/tapered shapes for more organic look
add_box(bm, (0, 0, 1.0), (0.42, 0.24, 0.52))     # chest
add_box(bm, (0, 0, 0.68), (0.38, 0.22, 0.16))    # waist
add_box(bm, (0, 0, 1.32), (0.12, 0.1, 0.12))     # neck

# Head - can use sphere for rounder look
add_sphere(bm, (0, 0, 1.58), 0.18, segments=12, rings=8)

# Arms
add_box(bm, (-0.32, 0, 1.1), (0.12, 0.1, 0.35))  # left upper arm
add_box(bm, (-0.32, 0, 0.72), (0.1, 0.08, 0.35)) # left forearm
add_box(bm, (0.32, 0, 1.1), (0.12, 0.1, 0.35))   # right upper arm
add_box(bm, (0.32, 0, 0.72), (0.1, 0.08, 0.35))  # right forearm

# Hands
add_box(bm, (-0.32, 0, 0.52), (0.08, 0.06, 0.1))
add_box(bm, (0.32, 0, 0.52), (0.08, 0.06, 0.1))

# Legs
add_box(bm, (-0.12, 0, 0.42), (0.12, 0.1, 0.32))  # left thigh
add_box(bm, (-0.12, 0, 0.1), (0.1, 0.09, 0.32))   # left shin
add_box(bm, (0.12, 0, 0.42), (0.12, 0.1, 0.32))   # right thigh
add_box(bm, (0.12, 0, 0.1), (0.1, 0.09, 0.32))    # right shin

# Feet
add_box(bm, (-0.12, 0.04, -0.04), (0.1, 0.14, 0.08))
add_box(bm, (0.12, 0.04, -0.04), (0.1, 0.14, 0.08))

finish_part(bm, mesh)

# === HAIR (separate object with hair material) ===
obj_hair, bm, mesh = create_part("Hair", mat_hair)
add_sphere(bm, (0, 0, 1.64), 0.2, segments=10, rings=6)
add_box(bm, (0, -0.08, 1.5), (0.22, 0.1, 0.28))  # back of hair
finish_part(bm, mesh)

# === CLOTHING/ARMOR (separate object) ===
obj_cloth, bm, mesh = create_part("Clothing", mat_clothing)
# Add clothing shapes here - shirt, pants, robe, armor plates, etc.
add_box(bm, (0, 0, 1.0), (0.45, 0.26, 0.54))     # shirt/chest covering
add_box(bm, (0, 0, 0.42), (0.28, 0.2, 0.5))      # pants/skirt
finish_part(bm, mesh)

# === ACCESSORIES (weapons, hats, etc.) ===
# Add based on character type

print("Character created with multiple materials!")

---
## CRITICAL INSTRUCTIONS:
1. CREATE SEPARATE OBJECTS for different colored parts (body, hair, clothing, accessories)
2. EACH OBJECT gets its OWN MATERIAL with appropriate color
3. Use add_sphere() for heads/round parts, add_cone() for hats/horns, add_cylinder() for weapons
4. Match proportions to character type:
   - Chibi: big head (0.25 radius), small body (0.5x height)
   - Realistic: normal proportions (head ~1/7 of height)
   - Stylized: slightly large head, expressive proportions
5. Add DISTINCTIVE FEATURES based on the prompt:
   - Elf: pointed ears using add_cone()
   - Cat: triangular ears, tail using multiple boxes
   - Robot: angular shapes, antenna, visor
   - Knight: armor plates, helmet, sword
   - Mage: flowing robe, staff, hat

## COLOR PALETTE EXAMPLES:
- Elf skin: (0.9, 0.8, 0.7) or pale green (0.75, 0.85, 0.7)
- Purple robe: (0.4, 0.2, 0.5)
- Gold trim: (0.85, 0.7, 0.3), metallic=0.9
- Steel armor: (0.6, 0.6, 0.65), metallic=0.95
- Wood staff: (0.4, 0.25, 0.15)
- Magic glow: (0.5, 0.3, 0.9)

BE CREATIVE but stay within the low-poly game character style (~500-2000 triangles).`;





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
  
  // Check for mesh creation (function not required for simple template approach)
  if (!code.includes("bpy.data.meshes.new") && !code.includes("bmesh.new()")) {
    validationErrors.push("Missing mesh creation");
  }
  
  // Check for object creation
  if (!code.includes("bpy.data.objects.new")) {
    validationErrors.push("Missing object creation");
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


/**
 * Refine Blender code based on screenshot analysis feedback
 * Used in the self-review loop to improve generated characters
 */
export async function refineBlenderCode(
  originalCode: string,
  screenshotBase64: string,
  originalPrompt: string,
  issues: string[],
  iteration: number
): Promise<string> {
  const refinePrompt = `You are refining Blender Python code for a 3D character that was generated but needs improvements.

ORIGINAL PROMPT: "${originalPrompt}"
ITERATION: ${iteration}/3

ISSUES FOUND IN SCREENSHOT:
${issues.map((issue, i) => `${i + 1}. ${issue}`).join('\n')}

ORIGINAL CODE:
\`\`\`python
${originalCode}
\`\`\`

YOUR TASK:
1. Analyze the screenshot to understand what's wrong
2. Modify the code to fix the identified issues
3. Keep the same overall structure but improve:
   - Body proportions (adjust add_box sizes/positions)
   - Character features (add missing elements)
   - Material colors and properties

OUTPUT RULES:
- Output ONLY the complete improved Python code
- No markdown, no explanations, no \`\`\`python markers
- Keep the same template structure
- Make surgical improvements, don't rewrite everything

If the character looks mostly correct, make minimal changes.`;

  try {
    const response = await generateContentWithFallback(
      "gemini-2.5-flash",
      [
        {
          role: "user",
          parts: [
            { text: refinePrompt },
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

    let code = response.text || "";
    
    // Clean up code
    code = code.replace(/```python\n?/g, "").replace(/```\n?/g, "").trim();
    
    // Basic validation
    if (!code.includes("import bpy") && !code.includes("import bmesh")) {
      console.warn("[Gemini Refine] Missing imports, adding them");
      code = "import bpy\nimport bmesh\n\n" + code;
    }
    
    console.log(`[Gemini Refine] Refined code: ${code.length} characters`);
    return code;
    
  } catch (error) {
    console.error("[Gemini Refine] Error:", error);
    // Return original code if refinement fails
    return originalCode;
  }
}


/**
 * Analyze screenshot and generate feedback for code improvement
 * Simplified version for self-review loop
 */
export async function analyzeScreenshotForCodeImprovement(
  screenshotBase64: string,
  originalPrompt: string,
  iteration: number
): Promise<{
  satisfactory: boolean;
  issues: string[];
  suggestions: string[];
  confidence: number;
}> {
  const analysisPrompt = `Analyze this screenshot of a generated 3D character.

ORIGINAL REQUEST: "${originalPrompt}"
ITERATION: ${iteration}/3

Evaluate:
1. Does it match the requested character type? (warrior, mage, cat, robot, etc.)
2. Are body proportions correct? (no floating parts, symmetric limbs)
3. Are distinctive features present? (cat ears for cat, helmet for knight, etc.)
4. Is the overall silhouette readable and appealing?

Respond with JSON only:
{
  "satisfactory": true/false,
  "issues": ["issue1", "issue2"],
  "suggestions": ["specific fix 1", "specific fix 2"],
  "confidence": 0.0-1.0
}

Set satisfactory=true if the character is acceptable (minor issues OK).
Set satisfactory=false if major issues exist that need fixing.`;

  try {
    const response = await generateContentWithFallback(
      "gemini-2.5-flash",
      [
        {
          role: "user",
          parts: [
            { text: analysisPrompt },
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
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]);
      return {
        satisfactory: parsed.satisfactory ?? false,
        issues: parsed.issues ?? [],
        suggestions: parsed.suggestions ?? [],
        confidence: parsed.confidence ?? 0.5
      };
    }
    
    // Fallback
    return {
      satisfactory: true,
      issues: [],
      suggestions: [],
      confidence: 0.5
    };
    
  } catch (error) {
    console.error("[Gemini Screenshot Analysis] Error:", error);
    return {
      satisfactory: true, // Don't block on analysis errors
      issues: [],
      suggestions: [],
      confidence: 0.3
    };
  }
}

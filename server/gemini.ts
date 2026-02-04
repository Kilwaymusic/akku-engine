import { GoogleGenAI } from "@google/genai";

const ai = new GoogleGenAI({
  apiKey: process.env.AI_INTEGRATIONS_GEMINI_API_KEY,
  httpOptions: {
    apiVersion: "",
    baseUrl: process.env.AI_INTEGRATIONS_GEMINI_BASE_URL,
  },
});

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

const SYSTEM_PROMPT = `You are an AI assistant that converts natural language character descriptions into precise Blender parameters for generating 3D humanoid characters.

Given a character description, output ONLY valid JSON with these parameters:

{
  "skinColor": [R, G, B],  // RGB values 0.0-1.0 for skin/base color
  "bodyColor": [R, G, B],  // RGB values 0.0-1.0 for outfit/body color
  "headScale": [X, Y, Z],  // Head proportions, default [1.0, 1.0, 1.0]
  "torsoScale": [X, Y, Z], // Torso proportions, default [1.0, 1.0, 1.0]
  "armLength": 1.0,        // Arm length multiplier 0.5-1.5
  "legLength": 1.0,        // Leg length multiplier 0.5-1.5
  "characterType": "human", // Options: human, robot, fantasy, animal, chibi
  "accessories": [],       // List of accessories: ["helmet", "cape", "wings", etc.]
  "materialType": "matte", // Options: matte, metallic, glossy
  "roughness": 0.5,        // Material roughness 0.0-1.0
  "metallic": 0.0          // Material metallic 0.0-1.0
}

Character type guidelines:
- "human": Normal human proportions
- "robot": Metallic skin, angular features
- "fantasy": Can have unusual skin colors (green for orcs, pale for elves)
- "animal": Adjust colors for fur/feathers
- "chibi": Large head (headScale: [1.5, 1.5, 1.5]), short limbs

Color guidelines for Korean terms:
- 빨간/빨강: Red [0.8, 0.2, 0.2]
- 파란/파랑: Blue [0.2, 0.4, 0.8]
- 녹색/초록: Green [0.2, 0.7, 0.3]
- 노란/노랑: Yellow [0.9, 0.8, 0.2]
- 보라: Purple [0.6, 0.2, 0.8]
- 주황: Orange [0.9, 0.5, 0.1]
- 분홍: Pink [0.9, 0.5, 0.7]
- 검은/검정: Black [0.1, 0.1, 0.1]
- 흰/하얀: White [0.95, 0.95, 0.95]
- 금색: Gold [0.85, 0.65, 0.2]
- 은색: Silver [0.75, 0.75, 0.8]

For cute/kawaii characters or animals:
- Use larger head scale
- Brighter, softer colors
- Lower roughness for smoother look

For robots/mechs:
- Use metallic material type
- High metallic value (0.7-1.0)
- Gray or silver skin colors

Output ONLY the JSON, no explanations or markdown.`;

export async function analyzePromptWithGemini(prompt: string): Promise<BlenderParams> {
  try {
    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: [
        { role: "user", parts: [{ text: SYSTEM_PROMPT }] },
        { role: "model", parts: [{ text: "I understand. I will analyze character descriptions and output only valid JSON with Blender parameters." }] },
        { role: "user", parts: [{ text: `Analyze this character description and output the Blender parameters as JSON:\n\n${prompt}` }] },
      ],
    });

    const text = response.text || "";
    
    // Extract JSON from response (handle potential markdown code blocks)
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
    jsonStr = jsonStr.trim();

    const params = JSON.parse(jsonStr) as BlenderParams;
    
    // Validate and set defaults
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
    // Return default parameters on error
    return getDefaultParams();
  }
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

/**
 * Image Analyzer - Extracts character attributes from reference images
 * Uses Gemini Vision API to analyze uploaded images
 */

import OpenAI from "openai";

interface CharacterAttributes {
  description: string;
  style: string;
  colors: string[];
  bodyType: {
    preset: string;
    muscular?: number;
    fat?: number;
    height?: number;
    shoulderWidth?: number;
    hipWidth?: number;
  };
  gender: string;
  equipment: string[];
  archetype: string;
  suggestedPrompt: string;
}

const STYLE_KEYWORDS: Record<string, string> = {
  "chibi": "chibi",
  "super deformed": "sd",
  "sd": "sd",
  "realistic": "realistic",
  "stylized": "stylized",
  "cartoon": "cartoon",
  "mobile": "mobile",
  "low poly": "stylized",
  "minifig": "minifig",
  "lego": "minifig",
};

const BODY_TYPE_MAPPINGS: Record<string, string> = {
  "muscular": "muscular",
  "athletic": "athletic",
  "thin": "thin",
  "slim": "slim",
  "fat": "fat",
  "chubby": "fat",
  "tall": "tall",
  "short": "short",
  "heroic": "heroic",
  "stocky": "stocky",
};

const ARCHETYPE_KEYWORDS: string[] = [
  "warrior", "knight", "mage", "wizard", "rogue", "assassin",
  "robot", "cyborg", "sci-fi", "elf", "orc", "demon", "angel",
  "archer", "healer", "tank", "ninja", "samurai", "pirate"
];

function getGeminiClient(): OpenAI {
  const baseURL = process.env.AI_INTEGRATIONS_GEMINI_BASE_URL;
  const apiKey = process.env.AI_INTEGRATIONS_GEMINI_API_KEY;
  
  if (!baseURL || !apiKey) {
    throw new Error("Gemini AI Integration not configured. Please set up AI Integrations.");
  }
  
  return new OpenAI({
    apiKey,
    baseURL,
  });
}

export async function analyzeImage(imageBase64: string, mimeType: string = "image/png"): Promise<CharacterAttributes> {
  const client = getGeminiClient();
  
  const systemPrompt = `You are an expert at analyzing character reference images for 3D modeling.
Analyze the provided image and extract the following attributes for a low-poly 3D character generation system.

Respond in valid JSON format with these fields:
{
  "description": "Brief description of the character in the image",
  "style": "One of: realistic, stylized, chibi, sd, mobile, minifig, cartoon",
  "colors": ["Array of dominant colors as descriptive names (e.g., 'red', 'metallic blue', 'golden')"],
  "bodyType": {
    "preset": "One of: default, muscular, thin, fat, tall, short, athletic, stocky, slim, heroic, chibi, giant",
    "muscular": 0.0 to 1.0 (optional, how muscular the character appears),
    "fat": 0.0 to 1.0 (optional, body fat level),
    "height": -1.0 to 1.0 (optional, relative height, 0 is normal),
    "shoulderWidth": -1.0 to 1.0 (optional, shoulder width modifier),
    "hipWidth": -1.0 to 1.0 (optional, hip width modifier)
  },
  "gender": "male or female based on appearance",
  "equipment": ["Array of notable equipment/armor/accessories"],
  "archetype": "Character archetype like warrior, mage, robot, etc.",
  "suggestedPrompt": "A natural language prompt that would generate this character, in Korean or English"
}

Focus on visual characteristics that are relevant for 3D character generation.
For body proportions, estimate based on the character's visible build.`;

  try {
    const response = await client.chat.completions.create({
      model: "gemini-2.5-flash",
      messages: [
        {
          role: "user",
          content: [
            {
              type: "text",
              text: systemPrompt,
            },
            {
              type: "image_url",
              image_url: {
                url: `data:${mimeType};base64,${imageBase64}`,
              },
            },
          ],
        },
      ],
      max_tokens: 1024,
    });

    const content = response.choices[0]?.message?.content;
    if (!content) {
      throw new Error("No response from Gemini Vision API");
    }

    // Extract JSON from response (handle markdown code blocks)
    let jsonStr = content;
    const jsonMatch = content.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (jsonMatch) {
      jsonStr = jsonMatch[1].trim();
    } else {
      // Try to find raw JSON
      const bracketMatch = content.match(/\{[\s\S]*\}/);
      if (bracketMatch) {
        jsonStr = bracketMatch[0];
      }
    }

    const attributes = JSON.parse(jsonStr) as CharacterAttributes;
    
    // Validate and normalize style
    if (!["realistic", "stylized", "chibi", "sd", "mobile", "minifig", "cartoon"].includes(attributes.style)) {
      attributes.style = "stylized";
    }
    
    // Validate gender
    if (!["male", "female"].includes(attributes.gender)) {
      attributes.gender = "male";
    }
    
    // Ensure arrays exist
    attributes.colors = attributes.colors || [];
    attributes.equipment = attributes.equipment || [];
    
    // Ensure bodyType has preset
    if (!attributes.bodyType || !attributes.bodyType.preset) {
      attributes.bodyType = { preset: "default" };
    }

    console.log("[ImageAnalyzer] Successfully analyzed image:", {
      style: attributes.style,
      archetype: attributes.archetype,
      bodyType: attributes.bodyType.preset,
    });

    return attributes;
  } catch (error) {
    console.error("[ImageAnalyzer] Error analyzing image:", error);
    throw error;
  }
}

export function attributesToGenerationOptions(attributes: CharacterAttributes): {
  prompt: string;
  style: string;
  bodyType: string;
  gender: string;
  bodyTypeParams: Record<string, unknown>;
} {
  // Build prompt from attributes
  const promptParts: string[] = [];
  
  if (attributes.archetype) {
    promptParts.push(attributes.archetype);
  }
  
  if (attributes.colors.length > 0) {
    promptParts.push(attributes.colors.slice(0, 3).join(", "));
  }
  
  if (attributes.equipment.length > 0) {
    promptParts.push(attributes.equipment.slice(0, 3).join(", "));
  }
  
  const prompt = attributes.suggestedPrompt || promptParts.join(", ") || attributes.description;

  return {
    prompt,
    style: attributes.style,
    bodyType: attributes.bodyType.preset,
    gender: attributes.gender,
    bodyTypeParams: {
      preset: attributes.bodyType.preset,
      muscular: attributes.bodyType.muscular,
      fat: attributes.bodyType.fat,
      height: attributes.bodyType.height,
      shoulderWidth: attributes.bodyType.shoulderWidth,
      hipWidth: attributes.bodyType.hipWidth,
    },
  };
}

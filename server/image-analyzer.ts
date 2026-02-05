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
  
  const systemPrompt = `You are an expert at analyzing character reference images for 3D low-poly game character modeling.
Analyze the provided image VERY CAREFULLY and extract DETAILED attributes for accurate 3D character recreation.

IMPORTANT: Be EXTREMELY SPECIFIC about visual details. The output will be used to generate a 3D model that should closely match this reference.

Respond in valid JSON format with these fields:
{
  "description": "DETAILED description including: pose, clothing items, accessories, facial features, hair style, any unique visual characteristics",
  "style": "One of: realistic, stylized, chibi, sd, mobile, minifig, cartoon",
  "colors": ["SPECIFIC colors with context, e.g., 'brown short hair', 'blue casual t-shirt', 'dark gray pants', 'tan/beige skin tone'"],
  "bodyType": {
    "preset": "One of: default, muscular, thin, fat, tall, short, athletic, stocky, slim, heroic, chibi, giant",
    "muscular": 0.0 to 1.0 (how muscular the character appears),
    "fat": 0.0 to 1.0 (body fat level),
    "height": -1.0 to 1.0 (relative height, 0 is normal),
    "shoulderWidth": -1.0 to 1.0 (shoulder width modifier),
    "hipWidth": -1.0 to 1.0 (hip width modifier)
  },
  "gender": "male or female based on appearance",
  "equipment": ["SPECIFIC clothing/accessories: e.g., 'blue short-sleeve t-shirt', 'gray knee-length shorts', 'brown casual shoes'"],
  "archetype": "Character type: casual, warrior, mage, robot, etc.",
  "suggestedPrompt": "A VERY DETAILED prompt in Korean that would recreate this exact character. Include: gender, body type, specific clothing with colors, hair color/style, skin tone, pose if notable. Example format: '남성, 평균 체형, 갈색 짧은 머리, 베이지색 피부, 파란 반팔 티셔츠, 회색 반바지, 갈색 신발'"
}

Focus on ACCURACY - the generated 3D model should look like this reference image.
Pay special attention to: clothing style, colors, body proportions, and any distinctive features.`;

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

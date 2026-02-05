import type { Express } from "express";
import { createServer, type Server } from "http";
import express from "express";
import { storage } from "./storage";
import { insertJobSchema } from "@shared/schema";
import { existsSync, mkdirSync, writeFileSync, readFileSync } from "fs";
import path from "path";
import { analyzeImage, attributesToGenerationOptions } from "./image-analyzer";
import { mapPromptToParameters, analyzeScreenshotForRefinement, generateBlenderCode, refineBlenderCode, analyzeScreenshotForCodeImprovement, type AkkuSDKParameters, type ScreenshotAnalysis } from "./gemini";

const PUBLIC_DIR = path.join(process.cwd(), "public");

const MODELS_DIR = path.join(process.cwd(), "public", "models");

// GCP Worker server for Blender operations
const GCP_WORKER_URL = process.env.GCP_WORKER_URL || "http://localhost:5000";

interface BodyTypeParams {
  preset?: string;
  muscular?: number;
  fat?: number;
  height?: number;
  shoulderWidth?: number;
  hipWidth?: number;
}

interface GenerationOptions {
  prompt: string;
  style?: string;
  polyLevel?: string;
  bodyType?: BodyTypeParams;
  gender?: string;
  geminiParams?: AkkuSDKParameters;
}

// Timeout for GCP Worker requests (2 minutes)
const GCP_WORKER_TIMEOUT = 120000;

/**
 * Remote GCP Worker-based generation
 * Sends prompt to external Blender server and receives GLB file
 */
async function generateModelRemote(jobId: string, options: GenerationOptions): Promise<string> {
  const { prompt, style = "stylized", polyLevel = "medium", bodyType, gender = "male", geminiParams } = options;
  
  console.log(`[GCP Worker] Sending generation request for job ${jobId}...`);
  console.log(`Prompt: ${prompt}`);
  console.log(`Style: ${style}, Poly Level: ${polyLevel}`);
  console.log(`Body Type:`, bodyType);
  console.log(`Gender: ${gender}`);
  if (geminiParams) {
    console.log(`[Gemini] Parameters:`, {
      archetype: geminiParams.archetype,
      bodyPreset: geminiParams.bodyType.preset,
      armorStyle: geminiParams.equipment.armorStyle,
      color: geminiParams.shader.baseColor
    });
  }

  if (!existsSync(MODELS_DIR)) {
    mkdirSync(MODELS_DIR, { recursive: true });
  }

  const outputPath = path.join(MODELS_DIR, `${jobId}.glb`);

  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), GCP_WORKER_TIMEOUT);

  // Normalize armorStyle to SDK-compatible equipment value
  function mapArmorStyleToEquipment(armorStyle: string | undefined): string {
    if (!armorStyle) return "default";
    switch (armorStyle) {
      case "plate":
      case "heavy":
      case "scifi":
        return "armor";
      case "cloth":
      case "magic":
      case "leather":
        return "robe";
      case "none":
      case "light":
      default:
        return "default";
    }
  }

  // Use Gemini params if available, otherwise fallback to basic params
  const requestBody = geminiParams ? {
    prompt,
    style: geminiParams.style?.proportionType || style,
    polyLevel: geminiParams.style?.polyLevel || polyLevel,
    jobId,
    gender: geminiParams.style?.gender || gender,
    bodyType: JSON.stringify(geminiParams.bodyType || {}),
    equipment: mapArmorStyleToEquipment(geminiParams.equipment?.armorStyle),
    geminiParams: JSON.stringify(geminiParams),
  } : {
    prompt,
    style,
    polyLevel,
    jobId,
    gender,
    bodyType: bodyType ? JSON.stringify(bodyType) : undefined,
  };

  try {
    const response = await fetch(`${GCP_WORKER_URL}/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`GCP Worker returned ${response.status}: ${errorText}`);
    }

    // Validate content type
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      // Worker returned JSON error
      const errorData = await response.json() as { error?: string };
      throw new Error(`GCP Worker error: ${errorData.error || "Unknown error"}`);
    }

    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    
    // Validate buffer size (GLB files should be at least a few KB)
    if (buffer.length < 100) {
      throw new Error(`Invalid GLB file: too small (${buffer.length} bytes)`);
    }

    // Validate GLB magic number (glTF binary starts with "glTF")
    const magic = buffer.slice(0, 4).toString("ascii");
    if (magic !== "glTF") {
      throw new Error(`Invalid GLB file: bad magic number "${magic}"`);
    }

    // Save with timestamped filename from header if available, else useJobID
    const contentDisposition = response.headers.get("content-disposition");
    let filename = `${jobId}.glb`;
    if (contentDisposition && contentDisposition.includes("filename=")) {
      const match = contentDisposition.match(/filename="(.+)"/);
      if (match) filename = match[1];
    }
    
    const finalOutputPath = path.join(MODELS_DIR, filename);
    writeFileSync(finalOutputPath, buffer);
    
    // Also save to outputs directory for persistent record
    const OUTPUTS_DIR = path.join(process.cwd(), "public", "outputs");
    if (!existsSync(OUTPUTS_DIR)) {
      mkdirSync(OUTPUTS_DIR, { recursive: true });
    }
    writeFileSync(path.join(OUTPUTS_DIR, filename), buffer);
    
    console.log(`[GCP Worker] GLB file saved: ${finalOutputPath} (${buffer.length} bytes)`);
    
    if (existsSync(finalOutputPath)) {
      console.log(`[GCP Worker] Generation completed successfully for job ${jobId}`);
      return `/models/${filename}`;
    } else {
      throw new Error("GLB file was not saved correctly");
    }
  } catch (error) {
    clearTimeout(timeoutId);
    
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error(`GCP Worker timeout after ${GCP_WORKER_TIMEOUT / 1000} seconds`);
    }
    
    console.error(`[GCP Worker] Generation failed:`, error);
    throw error;
  }
}

/**
 * Main generation function - uses remote GCP Worker
 */
async function generateModel(jobId: string, options: GenerationOptions): Promise<string> {
  return await generateModelRemote(jobId, options);
}

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  // Serve static files from public directory (for SDK downloads, etc.)
  app.use("/models", express.static(path.join(PUBLIC_DIR, "models")));
  app.use("/outputs", express.static(path.join(PUBLIC_DIR, "outputs")));
  
  // SDK download endpoint - returns base64 encoded file
  app.get("/api/sdk-base64", (req, res) => {
    const filePath = path.join(PUBLIC_DIR, "akku_sdk_v3.6.tar.gz");
    if (existsSync(filePath)) {
      const fileData = readFileSync(filePath);
      const base64Data = fileData.toString("base64");
      res.json({ 
        filename: "akku_sdk_v3.6.tar.gz",
        size: fileData.length,
        data: base64Data 
      });
    } else {
      res.status(404).json({ error: "SDK file not found" });
    }
  });

  // SDK individual file download - returns raw Python file
  app.get("/api/sdk-file/:filename", (req, res) => {
    const sdkDir = path.join(process.cwd(), "server", "akku_sdk");
    const filename = req.params.filename;
    const allowedFiles = ["core.py", "tools.py", "mesh.py", "shader.py", "body.py", 
                          "kitbash.py", "rigging.py", "finalize.py", "handlers.py", 
                          "main.py", "run.py", "__init__.py"];
    if (!allowedFiles.includes(filename)) {
      return res.status(400).send("Invalid filename");
    }
    const filePath = path.join(sdkDir, filename);
    if (existsSync(filePath)) {
      res.setHeader("Content-Type", "text/plain");
      res.send(readFileSync(filePath, "utf-8"));
    } else {
      res.status(404).send("File not found");
    }
  });

  // List all SDK files
  app.get("/api/sdk-files", (req, res) => {
    res.json({
      files: ["core.py", "tools.py", "mesh.py", "shader.py", "body.py", 
              "kitbash.py", "rigging.py", "finalize.py", "handlers.py", 
              "main.py", "run.py", "__init__.py"],
      version: "3.6"
    });
  });

  // Download full SDK as tar.gz for GCP pull
  app.get("/api/sdk-bundle", async (req, res) => {
    try {
      const { execSync } = await import("child_process");
      const sdkDir = path.join(process.cwd(), "server", "akku_sdk");
      const gcpAppPath = path.join(process.cwd(), "server", "gcp-app.py");
      const tempTar = "/tmp/akku_sdk_bundle.tar.gz";
      
      // Create tar with SDK folder and gcp-app.py
      execSync(`tar -czf ${tempTar} -C ${path.join(process.cwd(), "server")} akku_sdk gcp-app.py`);
      
      res.setHeader("Content-Type", "application/gzip");
      res.setHeader("Content-Disposition", "attachment; filename=akku_sdk_bundle.tar.gz");
      res.send(readFileSync(tempTar));
    } catch (error) {
      console.error("SDK bundle error:", error);
      res.status(500).json({ error: "Failed to create SDK bundle" });
    }
  });

  // GCP pull script - run this on GCP to download latest SDK
  app.get("/api/gcp-pull-script", (req, res) => {
    const replitUrl = `https://${req.get('host')}`;
    
    const script = `#!/bin/bash
# Akku SDK Pull Script - Run this on GCP Worker
# Downloads latest SDK from Replit and restarts Flask server
set -e

REPLIT_URL="${replitUrl}"
BASE_DIR="/home/composerkil/akku-engine"

echo "=== Akku SDK Pull from Replit ==="
echo "Downloading SDK bundle from \${REPLIT_URL}..."

cd \${BASE_DIR}

# Backup old SDK
if [ -d "server/akku_sdk" ]; then
  mv server/akku_sdk server/akku_sdk.bak.\$(date +%Y%m%d_%H%M%S)
fi

# Download and extract new SDK
curl -sL "\${REPLIT_URL}/api/sdk-bundle" -o /tmp/akku_sdk_bundle.tar.gz
tar -xzf /tmp/akku_sdk_bundle.tar.gz -C server/

# Restart Flask server
pkill -f "python.*gcp-app.py" || true
sleep 1
cd \${BASE_DIR}/server
nohup python gcp-app.py > /tmp/gcp-worker.log 2>&1 &
sleep 2

if pgrep -f "python.*gcp-app.py" > /dev/null; then
  echo "GCP Worker restarted successfully"
  curl -s http://localhost:5000/health
else
  echo "WARNING: GCP Worker may not have started"
  tail -20 /tmp/gcp-worker.log
fi

rm -f /tmp/akku_sdk_bundle.tar.gz
echo ""
echo "=== Pull Complete ==="
`;
    res.setHeader("Content-Type", "text/plain");
    res.send(script);
  });
  
  // Get all jobs
  app.get("/api/jobs", async (req, res) => {
    try {
      const jobs = await storage.getAllJobs();
      res.json(jobs);
    } catch (error) {
      console.error("Error fetching jobs:", error);
      res.status(500).json({ error: "Failed to fetch jobs" });
    }
  });

  // Get single job
  app.get("/api/jobs/:id", async (req, res) => {
    try {
      const job = await storage.getJob(req.params.id);
      if (!job) {
        return res.status(404).json({ error: "Job not found" });
      }
      res.json(job);
    } catch (error) {
      console.error("Error fetching job:", error);
      res.status(500).json({ error: "Failed to fetch job" });
    }
  });

  // Create new job
  app.post("/api/jobs", async (req, res) => {
    try {
      const result = insertJobSchema.safeParse(req.body);
      if (!result.success) {
        return res.status(400).json({ 
          error: "Invalid request", 
          details: result.error.errors 
        });
      }

      const job = await storage.createJob(result.data);
      res.status(201).json(job);

      // Start generation in background
      (async () => {
        try {
          await storage.updateJob(job.id, { status: "processing" });
          
          // Use Gemini to analyze prompt and map to SDK parameters
          console.log(`[Job ${job.id}] Analyzing prompt with Gemini...`);
          let geminiParams: AkkuSDKParameters | undefined;
          try {
            geminiParams = await mapPromptToParameters(
              job.prompt,
              result.data.style,
              result.data.polyLevel
            );
            console.log(`[Job ${job.id}] Gemini analysis complete:`, {
              archetype: geminiParams.archetype,
              bodyPreset: geminiParams.bodyType?.preset,
              armorStyle: geminiParams.equipment?.armorStyle
            });
          } catch (geminiError) {
            console.warn(`[Job ${job.id}] Gemini analysis failed, using fallback:`, geminiError);
            geminiParams = undefined;
          }
          
          // Convert string bodyType to BodyTypeParams as fallback
          let bodyTypeParams: BodyTypeParams | undefined;
          const rawBodyType = (req.body as { bodyType?: string }).bodyType;
          if (rawBodyType && typeof rawBodyType === 'string') {
            bodyTypeParams = { preset: rawBodyType };
          }
          
          const modelUrl = await generateModel(job.id, {
            prompt: job.prompt,
            style: result.data.style,
            polyLevel: result.data.polyLevel,
            bodyType: bodyTypeParams,
            gender: (req.body as { gender?: string }).gender || 'male',
            geminiParams,
          });
          
          await storage.updateJob(job.id, {
            status: "completed",
            modelUrl,
          });
          
          console.log(`Job ${job.id} completed successfully`);
        } catch (error) {
          console.error(`Job ${job.id} failed:`, error);
          await storage.updateJob(job.id, {
            status: "failed",
            error: error instanceof Error ? error.message : "Unknown error",
          });
        }
      })();
    } catch (error) {
      console.error("Error creating job:", error);
      res.status(500).json({ error: "Failed to create job" });
    }
  });

  // Analyze reference image using Gemini Vision
  app.post("/api/analyze-image", async (req, res) => {
    try {
      const { image, mimeType } = req.body as { image?: string; mimeType?: string };
      
      if (!image) {
        return res.status(400).json({ error: "No image provided" });
      }
      
      // Validate image size (max 5MB base64 = ~6.6MB string)
      const MAX_IMAGE_SIZE = 7 * 1024 * 1024;
      if (image.length > MAX_IMAGE_SIZE) {
        return res.status(400).json({ error: "Image too large. Maximum size is 5MB." });
      }
      
      // Validate mime type
      const allowedMimeTypes = ["image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"];
      
      // Remove data URL prefix if present
      let imageBase64 = image;
      const dataUrlMatch = image.match(/^data:([^;]+);base64,(.+)$/);
      let detectedMimeType = mimeType || "image/png";
      
      if (dataUrlMatch) {
        detectedMimeType = dataUrlMatch[1];
        imageBase64 = dataUrlMatch[2];
      }
      
      if (!allowedMimeTypes.includes(detectedMimeType)) {
        return res.status(400).json({ error: "Invalid image type. Allowed: PNG, JPEG, WebP, GIF" });
      }
      
      console.log(`[API] Analyzing image (${detectedMimeType}, ${imageBase64.length} chars base64)`);
      
      const attributes = await analyzeImage(imageBase64, detectedMimeType);
      const generationOptions = attributesToGenerationOptions(attributes);
      
      res.json({
        success: true,
        attributes,
        generationOptions,
      });
    } catch (error) {
      console.error("[API] Image analysis failed:", error);
      res.status(500).json({ 
        error: "Image analysis failed",
        details: error instanceof Error ? error.message : "Unknown error"
      });
    }
  });

  // Get system status
  app.get("/api/status", async (req, res) => {
    res.json({
      mode: "GCP Worker",
      workerUrl: GCP_WORKER_URL,
      sdkVersion: "Akku SDK v3.7 (Procedural)",
      modelsDir: existsSync(MODELS_DIR),
    });
  });

  // Serve SDK file for GCP download
  app.get("/api/sdk", async (req, res) => {
    try {
      const { readFileSync } = await import("fs");
      const sdkPath = path.join(process.cwd(), "server", "akku-sdk-v3.py");
      const sdkContent = readFileSync(sdkPath, "utf-8");
      res.setHeader("Content-Type", "text/plain");
      res.send(sdkContent);
    } catch (error) {
      res.status(500).send("Error reading SDK file");
    }
  });

  // Serve Flask app for GCP download
  app.get("/api/flask-app", async (req, res) => {
    try {
      const { readFileSync } = await import("fs");
      const appPath = path.join(process.cwd(), "server", "gcp-app.py");
      const appContent = readFileSync(appPath, "utf-8");
      res.setHeader("Content-Type", "text/plain");
      res.send(appContent);
    } catch (error) {
      res.status(500).send("Error reading app file");
    }
  });

  // Deployment script for GCP
  app.get("/api/deploy-script", async (req, res) => {
    const replitUrl = req.get('host') || 'localhost:5000';
    const protocol = req.protocol || 'https';
    const baseUrl = `${protocol}://${replitUrl}`;
    
    const script = `#!/bin/bash
# Akku SDK v3.0 Deployment Script
set -e
cd ~/akku-engine

echo "Downloading Akku SDK v3.0..."
curl -sL "${baseUrl}/api/sdk" > akku-sdk.py
echo "SDK downloaded."

echo "Downloading Flask server..."
curl -sL "${baseUrl}/api/flask-app" > app.py
echo "Flask app downloaded."

echo "Restarting server..."
pkill -f "python3 app.py" 2>/dev/null || true
nohup python3 app.py > server.log 2>&1 &
sleep 3
curl http://localhost:5000/health
echo ""
echo "Deployment complete!"
`;
    res.setHeader("Content-Type", "text/plain");
    res.send(script);
  });

  // Deploy SDK to GCP
  app.post("/api/deploy", async (req, res) => {
    try {
      const { deployAndRestart } = await import("./gcp-deploy");
      const { readFileSync } = await import("fs");
      
      // Read SDK and app files
      const sdkContent = readFileSync(path.join(process.cwd(), "server", "akku-sdk.py"), "utf-8");
      const appContent = readFileSync(path.join(process.cwd(), "server", "gcp-app.py"), "utf-8");
      
      const result = await deployAndRestart([
        { name: "akku-sdk.py", content: sdkContent },
        { name: "app.py", content: appContent }
      ]);
      
      if (result.success) {
        res.json({ success: true, message: result.message });
      } else {
        res.status(500).json({ success: false, error: result.message });
      }
    } catch (error) {
      console.error("Deploy error:", error);
      res.status(500).json({ 
        success: false, 
        error: error instanceof Error ? error.message : "Deployment failed" 
      });
    }
  });

  // Test GCP connection
  app.get("/api/gcp-test", async (req, res) => {
    try {
      const { testConnection } = await import("./gcp-deploy");
      const result = await testConnection();
      res.json(result);
    } catch (error) {
      res.status(500).json({ 
        success: false, 
        error: error instanceof Error ? error.message : "Connection test failed" 
      });
    }
  });

  // ============================================================
  // ITERATIVE GENERATION - Autonomous 3D Agent with Self-Verification
  // Replit orchestrates: Generate → Screenshot → Gemini VLM → Refine → Repeat
  // ============================================================
  
  app.post("/api/jobs/iterative", async (req, res) => {
    try {
      const { prompt, maxIterations = 3 } = req.body as { 
        prompt: string; 
        maxIterations?: number;
      };
      
      if (!prompt) {
        return res.status(400).json({ error: "Prompt is required" });
      }
      
      const iterations = Math.min(maxIterations, 5);
      const iterationResults: Array<{
        iteration: number;
        glb_size_bytes: number;
        screenshot_size_bytes: number;
        analysis?: ScreenshotAnalysis;
        satisfactory: boolean;
      }> = [];
      
      console.log(`[Iterative Generation] Starting with prompt: "${prompt}", max ${iterations} iterations`);
      
      // Step 1: Get initial params from Gemini
      let currentParams: AkkuSDKParameters | undefined;
      try {
        currentParams = await mapPromptToParameters(prompt);
        console.log(`[Iterative Generation] Initial Gemini params:`, {
          archetype: currentParams.archetype,
          bodyPreset: currentParams.bodyType?.preset,
          armorStyle: currentParams.equipment?.armorStyle
        });
      } catch (geminiError) {
        console.warn(`[Iterative Generation] Gemini analysis failed, using defaults`);
      }
      
      const sessionId = `iter_${Date.now()}`;
      let finalGlbPath: string | null = null;
      
      // Step 2: Iterative loop with Gemini VLM self-verification
      for (let i = 1; i <= iterations; i++) {
        console.log(`[Iteration ${i}/${iterations}] Starting...`);
        
        // Call GCP Worker for single iteration with screenshot capture
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);
        
        try {
          const response = await fetch(`${GCP_WORKER_URL}/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              prompt,
              style: currentParams?.style?.proportionType || "stylized",
              polyLevel: currentParams?.style?.polyLevel || "medium",
              gender: currentParams?.style?.gender || "male",
              bodyType: currentParams?.bodyType?.preset || "default",
              geminiParams: currentParams,
              captureScreenshot: true,
              sessionId,
              iteration: i
            }),
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
          
          if (!response.ok) {
            const errorText = await response.text();
            console.error(`[Iteration ${i}] Generation failed: ${errorText}`);
            iterationResults.push({
              iteration: i,
              glb_size_bytes: 0,
              screenshot_size_bytes: 0,
              satisfactory: false
            });
            continue;
          }
          
          // Validate content-type to ensure we got GLB not JSON error
          const contentType = response.headers.get("content-type") || "";
          if (contentType.includes("application/json")) {
            const errorJson = await response.json() as { error?: string };
            console.error(`[Iteration ${i}] Generation returned JSON error:`, errorJson);
            iterationResults.push({
              iteration: i,
              glb_size_bytes: 0,
              screenshot_size_bytes: 0,
              satisfactory: false
            });
            continue;
          }
          
          // Save GLB file
          const buffer = Buffer.from(await response.arrayBuffer());
          
          // Validate GLB magic number
          const magic = buffer.slice(0, 4).toString("ascii");
          if (magic !== "glTF") {
            console.error(`[Iteration ${i}] Invalid GLB: bad magic "${magic}"`);
            iterationResults.push({
              iteration: i,
              glb_size_bytes: 0,
              screenshot_size_bytes: 0,
              satisfactory: false
            });
            continue;
          }
          
          const glbFilename = `${sessionId}_iter${i}.glb`;
          const outputPath = path.join(MODELS_DIR, glbFilename);
          writeFileSync(outputPath, buffer);
          
          console.log(`[Iteration ${i}] GLB saved: ${buffer.length} bytes`);
          finalGlbPath = outputPath;
          
          // Try to fetch screenshot from GCP Worker for VLM analysis
          let screenshotBase64: string | null = null;
          try {
            const screenshotResponse = await fetch(
              `${GCP_WORKER_URL}/screenshot/${sessionId}/iter${i}.png`
            );
            if (screenshotResponse.ok) {
              const screenshotBuffer = Buffer.from(await screenshotResponse.arrayBuffer());
              screenshotBase64 = screenshotBuffer.toString("base64");
              console.log(`[Iteration ${i}] Screenshot fetched: ${screenshotBuffer.length} bytes`);
            }
          } catch (screenshotError) {
            console.warn(`[Iteration ${i}] Screenshot fetch failed:`, screenshotError);
          }
          
          // Step 3: Analyze screenshot with Gemini VLM
          let analysis: ScreenshotAnalysis | undefined;
          let shouldBreak = false;
          
          if (screenshotBase64 && currentParams) {
            try {
              analysis = await analyzeScreenshotForRefinement(
                screenshotBase64,
                prompt,
                currentParams,
                i
              );
              
              console.log(`[Iteration ${i}] VLM Analysis:`, {
                satisfactory: analysis.satisfactory,
                issues: analysis.issues,
                confidence: analysis.confidence
              });
              
              // Check if satisfactory - set flag to break after pushing result
              if (analysis.satisfactory) {
                console.log(`[Iteration ${i}] Character satisfactory! Stopping iterations.`);
                shouldBreak = true;
              }
              
              // Step 4: Apply refinements for next iteration (if not satisfactory)
              if (!analysis.satisfactory && analysis.refinements && Object.keys(analysis.refinements).length > 0) {
                console.log(`[Iteration ${i}] Applying refinements for next iteration`);
                
                // Merge refinements into current params (including equipment)
                if (analysis.refinements.bodyType && currentParams) {
                  currentParams.bodyType = { ...currentParams.bodyType, ...analysis.refinements.bodyType };
                }
                if (analysis.refinements.style && currentParams) {
                  currentParams.style = { ...currentParams.style, ...analysis.refinements.style };
                }
                if (analysis.refinements.equipment && currentParams) {
                  currentParams.equipment = { ...currentParams.equipment, ...analysis.refinements.equipment };
                }
                if (analysis.refinements.shader && currentParams) {
                  currentParams.shader = { ...currentParams.shader, ...analysis.refinements.shader };
                }
              }
              
            } catch (analysisError) {
              console.warn(`[Iteration ${i}] VLM analysis failed:`, analysisError);
            }
          }
          
          iterationResults.push({
            iteration: i,
            glb_size_bytes: buffer.length,
            screenshot_size_bytes: screenshotBase64 ? Buffer.from(screenshotBase64, "base64").length : 0,
            analysis,
            satisfactory: analysis?.satisfactory || false
          });
          
          // Break out of loop if satisfactory
          if (shouldBreak) {
            break;
          }
          
        } catch (error) {
          clearTimeout(timeoutId);
          console.error(`[Iteration ${i}] Error:`, error);
          iterationResults.push({
            iteration: i,
            glb_size_bytes: 0,
            screenshot_size_bytes: 0,
            satisfactory: false
          });
        }
      }
      
      // Step 5: Return final result
      const lastSuccessfulIteration = iterationResults.filter(r => r.glb_size_bytes > 0).pop();
      const finalModelUrl = lastSuccessfulIteration 
        ? `/models/${sessionId}_iter${lastSuccessfulIteration.iteration}.glb`
        : null;
      
      console.log(`[Iterative Generation] Completed ${iterationResults.length} iterations`);
      
      res.json({
        status: finalModelUrl ? "success" : "failed",
        modelUrl: finalModelUrl,
        session_id: sessionId,
        iterations: iterationResults.map(r => ({
          iteration: r.iteration,
          glb_size_bytes: r.glb_size_bytes,
          satisfactory: r.satisfactory,
          issues: r.analysis?.issues || [],
          reasoning: r.analysis?.reasoning
        })),
        total_iterations: iterationResults.length,
        final_satisfactory: iterationResults[iterationResults.length - 1]?.satisfactory || false
      });
      
    } catch (error) {
      console.error("[Iterative Generation] Failed:", error);
      res.status(500).json({ 
        error: error instanceof Error ? error.message : "Iterative generation failed" 
      });
    }
  });

  // Get screenshot from iterative session
  app.get("/api/iterative/:sessionId/screenshot/:iteration", async (req, res) => {
    try {
      const { sessionId, iteration } = req.params;
      const response = await fetch(
        `${GCP_WORKER_URL}/screenshot/${sessionId}/iter${iteration}.png`
      );
      
      if (!response.ok) {
        return res.status(404).json({ error: "Screenshot not found" });
      }
      
      const buffer = Buffer.from(await response.arrayBuffer());
      res.setHeader("Content-Type", "image/png");
      res.send(buffer);
      
    } catch (error) {
      res.status(500).json({ 
        error: error instanceof Error ? error.message : "Failed to fetch screenshot" 
      });
    }
  });

  // ============================================================
  // AUTONOMOUS 3D AGENT - Gemini Code Generation Endpoint
  // ============================================================
  
  /**
   * Generate character using Gemini-generated Blender Python code
   * This is the creative agent mode - Gemini directly controls mesh creation
   */
  app.post("/api/jobs/agent", async (req, res) => {
    try {
      const { prompt } = req.body;
      
      if (!prompt) {
        return res.status(400).json({ error: "Prompt is required" });
      }
      
      console.log(`\n${"=".repeat(60)}`);
      console.log(`[Autonomous 3D Agent] Starting generation`);
      console.log(`${"=".repeat(60)}`);
      console.log(`Prompt: ${prompt}`);
      
      // Step 1: Create job
      const job = await storage.createJob({ 
        prompt, 
        style: "stylized", 
        polyLevel: "medium" 
      });
      await storage.updateJob(job.id, { status: "processing" });
      
      console.log(`[Agent] Job created: ${job.id}`);
      
      // Step 2: Verify GCP Worker supports code execution
      console.log(`[Agent] Checking GCP Worker capabilities...`);
      try {
        const healthResponse = await fetch(`${GCP_WORKER_URL}/health`, {
          signal: AbortSignal.timeout(5000)
        });
        if (!healthResponse.ok) {
          throw new Error("GCP Worker health check failed");
        }
        const healthData = await healthResponse.json() as { version?: string };
        console.log(`[Agent] GCP Worker version: ${healthData.version}`);
        
        // Require version 5.0.0+ for code execution
        if (!healthData.version || !healthData.version.startsWith("5.")) {
          await storage.updateJob(job.id, { status: "failed" });
          return res.status(503).json({
            error: "GCP Worker outdated",
            details: "Code execution requires GCP Worker v5.0.0+. Please update the worker."
          });
        }
      } catch (healthError) {
        console.error(`[Agent] GCP Worker health check failed:`, healthError);
        await storage.updateJob(job.id, { status: "failed" });
        return res.status(503).json({
          error: "GCP Worker unavailable",
          details: "Cannot connect to GCP Worker for code execution"
        });
      }
      
      // Step 3: Generate Blender code with Gemini
      console.log(`[Agent] Generating Blender code with Gemini...`);
      let blenderCode: string;
      
      try {
        blenderCode = await generateBlenderCode(prompt);
        console.log(`[Agent] Code generated: ${blenderCode.length} characters`);
      } catch (codeError) {
        console.error(`[Agent] Code generation failed:`, codeError);
        await storage.updateJob(job.id, { 
          status: "failed" 
        });
        return res.status(500).json({ 
          error: "Failed to generate Blender code",
          details: codeError instanceof Error ? codeError.message : String(codeError)
        });
      }
      
      // Step 4: Send code to GCP Worker for execution
      console.log(`[Agent] Sending code to GCP Worker...`);
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), GCP_WORKER_TIMEOUT);
      
      try {
        const gcpResponse = await fetch(`${GCP_WORKER_URL}/execute-code`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            code: blenderCode,
            jobId: job.id,
            prompt
          }),
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        // Check if response is JSON
        const contentType = gcpResponse.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
          const text = await gcpResponse.text();
          console.error(`[Agent] GCP Worker returned non-JSON response:`, text.substring(0, 200));
          await storage.updateJob(job.id, { status: "failed" });
          return res.status(500).json({
            error: "GCP Worker returned invalid response",
            details: gcpResponse.status === 404 
              ? "Endpoint /execute-code not found - please update GCP Worker" 
              : `Status ${gcpResponse.status}`
          });
        }
        
        const result = await gcpResponse.json() as { 
          success: boolean; 
          glb_path?: string; 
          glb_filename?: string;
          file_size?: number;
          error?: string;
          execution_time?: number;
        };
        
        if (!result.success) {
          console.error(`[Agent] Execution failed:`, result.error);
          await storage.updateJob(job.id, { status: "failed" });
          return res.status(500).json({ 
            error: "Blender execution failed",
            details: result.error
          });
        }
        
        console.log(`[Agent] GLB created: ${result.glb_filename} (${result.file_size} bytes)`);
        
        // Step 5: Fetch GLB from GCP Worker
        const glbResponse = await fetch(`${GCP_WORKER_URL}/download/${result.glb_filename}`);
        
        if (!glbResponse.ok) {
          throw new Error(`Failed to download GLB: ${glbResponse.status}`);
        }
        
        const glbBuffer = await glbResponse.arrayBuffer();
        
        // Save locally
        if (!existsSync(MODELS_DIR)) {
          mkdirSync(MODELS_DIR, { recursive: true });
        }
        
        const localPath = path.join(MODELS_DIR, `${job.id}.glb`);
        writeFileSync(localPath, Buffer.from(glbBuffer));
        
        const modelUrl = `/models/${job.id}.glb`;
        await storage.updateJob(job.id, { 
          status: "completed", 
          modelUrl 
        });
        
        console.log(`[Agent] Completed! Model: ${modelUrl}`);
        console.log(`${"=".repeat(60)}\n`);
        
        res.json({
          success: true,
          jobId: job.id,
          modelUrl,
          codeLength: blenderCode.length,
          executionTime: result.execution_time
        });
        
      } catch (fetchError) {
        clearTimeout(timeoutId);
        
        if (fetchError instanceof Error && fetchError.name === 'AbortError') {
          console.error(`[Agent] Request timed out`);
          await storage.updateJob(job.id, { status: "failed" });
          return res.status(504).json({ error: "Request timed out" });
        }
        
        throw fetchError;
      }
      
    } catch (error) {
      console.error(`[Autonomous 3D Agent] Error:`, error);
      res.status(500).json({ 
        error: error instanceof Error ? error.message : "Agent generation failed" 
      });
    }
  });

  // ==========================================================================
  // Iterative Self-Review Agent (3-iteration loop with screenshot analysis)
  // ==========================================================================
  app.post("/api/jobs/agent-iterative", async (req, res) => {
    try {
      const { prompt, maxIterations = 3 } = req.body;
      
      if (!prompt || typeof prompt !== "string") {
        return res.status(400).json({ error: "Prompt is required" });
      }
      
      console.log(`\n${"=".repeat(60)}`);
      console.log(`[Iterative Agent] Starting self-review loop`);
      console.log(`[Iterative Agent] Prompt: "${prompt}"`);
      console.log(`[Iterative Agent] Max iterations: ${maxIterations}`);
      console.log(`${"=".repeat(60)}\n`);
      
      // Create job record
      const job = await storage.createJob({
        prompt,
        status: "processing"
      });
      
      // Verify GCP Worker is available
      try {
        const healthResponse = await fetch(`${GCP_WORKER_URL}/health`);
        const healthData = await healthResponse.json() as { version?: string };
        console.log(`[Iterative Agent] GCP Worker v${healthData.version} is healthy`);
      } catch (error) {
        await storage.updateJob(job.id, { status: "failed" });
        return res.status(503).json({ error: "GCP Worker unavailable" });
      }
      
      // Step 1: Generate initial code
      console.log(`[Iterative Agent] Generating initial code...`);
      let currentCode = await generateBlenderCode(prompt);
      console.log(`[Iterative Agent] Initial code: ${currentCode.length} chars`);
      
      let finalGlbFilename = "";
      let finalScreenshotFilename = "";
      const iterationResults: Array<{
        iteration: number;
        success: boolean;
        issues?: string[];
        satisfactory?: boolean;
      }> = [];
      
      // Iterative loop
      for (let iteration = 1; iteration <= maxIterations; iteration++) {
        console.log(`\n[Iterative Agent] === Iteration ${iteration}/${maxIterations} ===`);
        
        // Execute code with screenshot capture
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), GCP_WORKER_TIMEOUT);
        
        try {
          const execResponse = await fetch(`${GCP_WORKER_URL}/execute-code`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              code: currentCode,
              jobId: `${job.id}_iter${iteration}`,
              prompt,
              captureScreenshot: true,
              iteration
            }),
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
          
          const result = await execResponse.json() as {
            success: boolean;
            glb_filename?: string;
            screenshot_filename?: string;
            error?: string;
          };
          
          if (!result.success) {
            console.error(`[Iterative Agent] Execution failed:`, result.error);
            iterationResults.push({ iteration, success: false, issues: [result.error || "Unknown error"] });
            
            // If execution fails, try to regenerate code for next iteration
            if (iteration < maxIterations) {
              console.log(`[Iterative Agent] Regenerating code after failure...`);
              try {
                currentCode = await generateBlenderCode(prompt + " (retry, simpler approach)");
              } catch (regenError) {
                console.error(`[Iterative Agent] Code regeneration failed:`, regenError);
              }
            }
            continue;
          }
          
          console.log(`[Iterative Agent] GLB: ${result.glb_filename}`);
          console.log(`[Iterative Agent] Screenshot: ${result.screenshot_filename}`);
          
          finalGlbFilename = result.glb_filename || "";
          finalScreenshotFilename = result.screenshot_filename || "";
          
          // If this is the last iteration, skip analysis
          if (iteration === maxIterations) {
            console.log(`[Iterative Agent] Final iteration reached, using result`);
            iterationResults.push({ iteration, success: true, satisfactory: true });
            break;
          }
          
          // Fetch screenshot for analysis
          let screenshotBase64 = "";
          if (result.screenshot_filename) {
            console.log(`[Iterative Agent] Fetching screenshot for analysis...`);
            
            try {
              const screenshotResponse = await fetch(
                `${GCP_WORKER_URL}/download/${result.screenshot_filename}`
              );
              
              if (screenshotResponse.ok) {
                const screenshotBuffer = await screenshotResponse.arrayBuffer();
                screenshotBase64 = Buffer.from(screenshotBuffer).toString("base64");
              } else {
                console.warn(`[Iterative Agent] Screenshot fetch failed: ${screenshotResponse.status}`);
              }
            } catch (screenshotError) {
              console.warn(`[Iterative Agent] Screenshot fetch error:`, screenshotError);
            }
          }
          
          // Analyze screenshot with Gemini Vision (or provide default feedback if no screenshot)
          console.log(`[Iterative Agent] Analyzing with Gemini Vision...`);
          let analysis: { satisfactory: boolean; issues: string[]; suggestions: string[]; confidence: number };
          
          if (screenshotBase64) {
            analysis = await analyzeScreenshotForCodeImprovement(
              screenshotBase64,
              prompt,
              iteration
            );
          } else {
            // Default analysis when screenshot unavailable - assume needs improvement
            analysis = {
              satisfactory: false,
              issues: ["Screenshot unavailable - assuming improvements needed"],
              suggestions: ["Ensure mesh is created correctly", "Check material assignment"],
              confidence: 0.3
            };
          }
          
          console.log(`[Iterative Agent] Analysis: satisfactory=${analysis.satisfactory}, issues=${analysis.issues.length}, confidence=${analysis.confidence}`);
          
          iterationResults.push({
            iteration,
            success: true,
            issues: analysis.issues,
            satisfactory: analysis.satisfactory
          });
          
          // If satisfactory with high confidence, stop early
          if (analysis.satisfactory && analysis.confidence >= 0.7) {
            console.log(`[Iterative Agent] Result is satisfactory (confidence: ${analysis.confidence}), stopping early`);
            break;
          }
          
          // Refine code based on feedback
          console.log(`[Iterative Agent] Refining code based on ${analysis.issues.length} issues...`);
          try {
            currentCode = await refineBlenderCode(
              currentCode,
              screenshotBase64,
              prompt,
              [...analysis.issues, ...analysis.suggestions],
              iteration + 1
            );
            console.log(`[Iterative Agent] Refined code: ${currentCode.length} chars`);
          } catch (refineError) {
            console.error(`[Iterative Agent] Refinement failed:`, refineError);
            // Continue with current code
          }
          
        } catch (fetchError) {
          clearTimeout(timeoutId);
          console.error(`[Iterative Agent] Fetch error:`, fetchError);
          iterationResults.push({ iteration, success: false, issues: ["Network error"] });
        }
      }
      
      // Final result
      if (!finalGlbFilename) {
        await storage.updateJob(job.id, { status: "failed" });
        return res.status(500).json({
          error: "All iterations failed",
          iterations: iterationResults
        });
      }
      
      // Download final GLB
      console.log(`[Iterative Agent] Downloading final GLB: ${finalGlbFilename}`);
      const glbResponse = await fetch(`${GCP_WORKER_URL}/download/${finalGlbFilename}`);
      
      if (!glbResponse.ok) {
        await storage.updateJob(job.id, { status: "failed" });
        return res.status(500).json({ error: "Failed to download final GLB" });
      }
      
      const glbBuffer = await glbResponse.arrayBuffer();
      
      // Save locally
      if (!existsSync(MODELS_DIR)) {
        mkdirSync(MODELS_DIR, { recursive: true });
      }
      
      const localFilename = `${job.id}_final.glb`;
      const localPath = path.join(MODELS_DIR, localFilename);
      writeFileSync(localPath, Buffer.from(glbBuffer));
      
      // Update job
      const modelUrl = `/models/${localFilename}`;
      await storage.updateJob(job.id, {
        status: "completed",
        modelUrl
      });
      
      console.log(`\n[Iterative Agent] === COMPLETE ===`);
      console.log(`[Iterative Agent] Job: ${job.id}`);
      console.log(`[Iterative Agent] Iterations: ${iterationResults.length}`);
      console.log(`[Iterative Agent] Model: ${modelUrl}`);
      
      res.json({
        jobId: job.id,
        status: "completed",
        modelUrl,
        iterations: iterationResults,
        totalIterations: iterationResults.length
      });
      
    } catch (error) {
      console.error(`[Iterative Agent] Error:`, error);
      res.status(500).json({
        error: error instanceof Error ? error.message : "Iterative generation failed"
      });
    }
  });

  return httpServer;
}

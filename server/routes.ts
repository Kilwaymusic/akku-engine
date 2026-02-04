import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { insertJobSchema } from "@shared/schema";
import { spawn } from "child_process";
import { existsSync, mkdirSync } from "fs";
import path from "path";
import { analyzePromptWithGemini, generateAkkuPlan, type BlenderParams } from "./gemini";
import { mcpManager } from "./mcp-manager";

const MODELS_DIR = path.join(process.cwd(), "public", "models");

// Configuration: Use MCP if available, fallback to CLI
let useMCPMode = true;

/**
 * Legacy CLI-based generation
 */
async function generateModelCLI(jobId: string, prompt: string): Promise<string> {
  console.log(`[CLI Mode] Analyzing prompt with Gemini AI for job ${jobId}...`);
  const blenderParams = await analyzePromptWithGemini(prompt);
  console.log(`Gemini AI generated parameters:`, JSON.stringify(blenderParams, null, 2));

  return new Promise((resolve, reject) => {
    if (!existsSync(MODELS_DIR)) {
      mkdirSync(MODELS_DIR, { recursive: true });
    }

    const outputPath = path.join(MODELS_DIR, `${jobId}.glb`);
    const scriptPath = path.join(process.cwd(), "scripts", "generate_humanoid.py");
    const paramsJson = JSON.stringify(blenderParams);

    console.log(`Starting Blender CLI generation for job ${jobId}`);

    const blenderProcess = spawn("blender", [
      "--background",
      "--python",
      scriptPath,
      "--",
      outputPath,
      paramsJson,
    ]);

    let stdout = "";
    let stderr = "";

    blenderProcess.stdout.on("data", (data) => {
      stdout += data.toString();
      console.log(`Blender stdout: ${data}`);
    });

    blenderProcess.stderr.on("data", (data) => {
      stderr += data.toString();
      console.error(`Blender stderr: ${data}`);
    });

    blenderProcess.on("close", (code) => {
      if (code === 0 && existsSync(outputPath)) {
        console.log(`Blender CLI completed successfully for job ${jobId}`);
        resolve(`/models/${jobId}.glb`);
      } else {
        console.error(`Blender failed with code ${code}`);
        reject(new Error(`Blender process failed with code ${code}: ${stderr}`));
      }
    });

    blenderProcess.on("error", (err) => {
      console.error(`Blender process error: ${err.message}`);
      reject(err);
    });
  });
}

/**
 * Akku SDK MCP-based generation with multi-step procedural workflow
 */
interface GenerationOptions {
  prompt: string;
  style?: string;
  polyLevel?: string;
}

async function generateModelMCP(jobId: string, options: GenerationOptions): Promise<string> {
  const { prompt, style = "stylized", polyLevel = "medium" } = options;
  console.log(`[Akku SDK Mode] Generating plan with Gemini AI for job ${jobId}...`);
  console.log(`Style: ${style}, Poly Level: ${polyLevel}`);
  
  const plan = await generateAkkuPlan(prompt, style, polyLevel);
  console.log(`Akku SDK Plan:`, JSON.stringify(plan, null, 2));
  console.log(`Total steps: ${plan.steps.length}`);

  if (!existsSync(MODELS_DIR)) {
    mkdirSync(MODELS_DIR, { recursive: true });
  }

  const outputPath = path.join(MODELS_DIR, `${jobId}.glb`);
  
  const result = await mcpManager.generateWithAkkuSDK(plan, outputPath);
  
  console.log(`Akku SDK Generation log:`);
  result.log.forEach(line => console.log(`  ${line}`));
  
  if (result.success && existsSync(outputPath)) {
    console.log(`Akku SDK generation completed successfully for job ${jobId}`);
    return `/models/${jobId}.glb`;
  } else {
    throw new Error(result.error || 'Akku SDK generation failed');
  }
}

/**
 * Main generation function - tries MCP first, falls back to CLI
 */
async function generateModel(jobId: string, options: GenerationOptions): Promise<string> {
  if (useMCPMode) {
    try {
      return await generateModelMCP(jobId, options);
    } catch (error) {
      console.warn(`MCP generation failed, falling back to CLI:`, error);
      return await generateModelCLI(jobId, options.prompt);
    }
  } else {
    return await generateModelCLI(jobId, options.prompt);
  }
}

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
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
          
          const modelUrl = await generateModel(job.id, {
            prompt: job.prompt,
            style: result.data.style,
            polyLevel: result.data.polyLevel,
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

  // Get system status
  app.get("/api/status", async (req, res) => {
    res.json({
      mcpMode: useMCPMode,
      sdkVersion: "Akku Low-poly SDK v1.0",
      blenderReady: mcpManager.isBlenderReady(),
      modelsDir: existsSync(MODELS_DIR),
      availableTools: {
        baseGeneration: ["spawn_humanoid_base", "deform_body"],
        kitbashing: ["attach_armor_plate", "add_scifi_detail"],
        pbrShading: ["apply_akku_pbr", "set_material_property"],
        rigging: ["finalize_and_bind", "test_animation"]
      }
    });
  });

  // Toggle generation mode
  app.post("/api/mode", async (req, res) => {
    const { useMCP } = req.body;
    if (typeof useMCP === 'boolean') {
      useMCPMode = useMCP;
      res.json({ mcpMode: useMCPMode });
    } else {
      res.status(400).json({ error: "Invalid mode setting" });
    }
  });

  return httpServer;
}

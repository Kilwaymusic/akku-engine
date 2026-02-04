import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { insertJobSchema } from "@shared/schema";
import { existsSync, mkdirSync, writeFileSync } from "fs";
import path from "path";

const MODELS_DIR = path.join(process.cwd(), "public", "models");

// GCP Worker server for Blender operations
const GCP_WORKER_URL = "http://34.134.82.224:5000/generate";

interface GenerationOptions {
  prompt: string;
  style?: string;
  polyLevel?: string;
}

// Timeout for GCP Worker requests (2 minutes)
const GCP_WORKER_TIMEOUT = 120000;

/**
 * Remote GCP Worker-based generation
 * Sends prompt to external Blender server and receives GLB file
 */
async function generateModelRemote(jobId: string, options: GenerationOptions): Promise<string> {
  const { prompt, style = "stylized", polyLevel = "medium" } = options;
  
  console.log(`[GCP Worker] Sending generation request for job ${jobId}...`);
  console.log(`Prompt: ${prompt}`);
  console.log(`Style: ${style}, Poly Level: ${polyLevel}`);

  if (!existsSync(MODELS_DIR)) {
    mkdirSync(MODELS_DIR, { recursive: true });
  }

  const outputPath = path.join(MODELS_DIR, `${jobId}.glb`);

  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), GCP_WORKER_TIMEOUT);

  try {
    const response = await fetch(GCP_WORKER_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        prompt,
        style,
        polyLevel,
        jobId,
      }),
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
    
    writeFileSync(outputPath, buffer);
    
    console.log(`[GCP Worker] GLB file saved: ${outputPath} (${buffer.length} bytes)`);
    
    if (existsSync(outputPath)) {
      console.log(`[GCP Worker] Generation completed successfully for job ${jobId}`);
      return `/models/${jobId}.glb`;
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
      mode: "GCP Worker",
      workerUrl: GCP_WORKER_URL,
      sdkVersion: "Akku SDK v2.0 (Remote)",
      modelsDir: existsSync(MODELS_DIR),
    });
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

  return httpServer;
}

import type { Express } from "express";
import { createServer, type Server } from "http";
import express from "express";
import { storage } from "./storage";
import { insertJobSchema } from "@shared/schema";
import { existsSync, mkdirSync, writeFileSync, readFileSync } from "fs";
import path from "path";

const PUBLIC_DIR = path.join(process.cwd(), "public");

const MODELS_DIR = path.join(process.cwd(), "public", "models");

// GCP Worker server for Blender operations
const GCP_WORKER_URL = "http://34.134.82.224:5000/generate";

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
}

// Timeout for GCP Worker requests (2 minutes)
const GCP_WORKER_TIMEOUT = 120000;

/**
 * Remote GCP Worker-based generation
 * Sends prompt to external Blender server and receives GLB file
 */
async function generateModelRemote(jobId: string, options: GenerationOptions): Promise<string> {
  const { prompt, style = "stylized", polyLevel = "medium", bodyType, gender = "male" } = options;
  
  console.log(`[GCP Worker] Sending generation request for job ${jobId}...`);
  console.log(`Prompt: ${prompt}`);
  console.log(`Style: ${style}, Poly Level: ${polyLevel}`);
  console.log(`Body Type:`, bodyType);
  console.log(`Gender: ${gender}`);

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
        gender,
        bodyType: bodyType ? JSON.stringify(bodyType) : undefined,
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
          
          // Convert string bodyType to BodyTypeParams
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

  return httpServer;
}

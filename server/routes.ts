import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { insertJobSchema } from "@shared/schema";
import { spawn } from "child_process";
import { existsSync, mkdirSync } from "fs";
import path from "path";

const MODELS_DIR = path.join(process.cwd(), "public", "models");

async function generateModel(jobId: string, prompt: string): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!existsSync(MODELS_DIR)) {
      mkdirSync(MODELS_DIR, { recursive: true });
    }

    const outputPath = path.join(MODELS_DIR, `${jobId}.glb`);
    const scriptPath = path.join(process.cwd(), "scripts", "generate_humanoid.py");

    console.log(`Starting Blender generation for job ${jobId}`);
    console.log(`Script path: ${scriptPath}`);
    console.log(`Output path: ${outputPath}`);

    const blenderProcess = spawn("blender", [
      "--background",
      "--python",
      scriptPath,
      "--",
      outputPath,
      prompt,
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
        console.log(`Blender completed successfully for job ${jobId}`);
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
          
          const modelUrl = await generateModel(job.id, job.prompt);
          
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

  return httpServer;
}

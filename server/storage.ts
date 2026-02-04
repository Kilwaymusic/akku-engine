import { type Job, type InsertJob } from "@shared/schema";
import { randomUUID } from "crypto";

export interface IStorage {
  createJob(job: InsertJob): Promise<Job>;
  getJob(id: string): Promise<Job | undefined>;
  getAllJobs(): Promise<Job[]>;
  updateJob(id: string, updates: Partial<Job>): Promise<Job | undefined>;
}

export class MemStorage implements IStorage {
  private jobs: Map<string, Job>;

  constructor() {
    this.jobs = new Map();
  }

  async createJob(insertJob: InsertJob): Promise<Job> {
    const id = randomUUID();
    const job: Job = {
      id,
      prompt: insertJob.prompt,
      status: "pending",
      modelUrl: null,
      error: null,
      createdAt: new Date(),
    };
    this.jobs.set(id, job);
    return job;
  }

  async getJob(id: string): Promise<Job | undefined> {
    return this.jobs.get(id);
  }

  async getAllJobs(): Promise<Job[]> {
    return Array.from(this.jobs.values()).sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
  }

  async updateJob(id: string, updates: Partial<Job>): Promise<Job | undefined> {
    const job = this.jobs.get(id);
    if (!job) return undefined;
    
    const updatedJob = { ...job, ...updates };
    this.jobs.set(id, updatedJob);
    return updatedJob;
  }
}

export const storage = new MemStorage();

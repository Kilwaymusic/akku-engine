import { sql } from "drizzle-orm";
import { pgTable, text, varchar, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const jobs = pgTable("jobs", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  prompt: text("prompt").notNull(),
  style: varchar("style", { length: 20 }).default("stylized"),
  polyLevel: varchar("poly_level", { length: 20 }).default("medium"),
  status: varchar("status", { length: 20 }).notNull().default("pending"),
  modelUrl: text("model_url"),
  error: text("error"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const insertJobSchema = createInsertSchema(jobs).pick({
  prompt: true,
}).extend({
  style: z.enum(["sd", "stylized", "realistic", "chibi", "mobile", "minifig", "cartoon"]).optional().default("stylized"),
  polyLevel: z.enum(["ultra_low", "low", "medium", "high"]).optional().default("medium"),
});

export type InsertJob = z.infer<typeof insertJobSchema>;
export type Job = typeof jobs.$inferSelect;

export type JobStatus = "pending" | "processing" | "completed" | "failed";

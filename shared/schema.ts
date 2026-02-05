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
  progressStage: varchar("progress_stage", { length: 50 }),
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
export type ProgressStage = 
  | "analyzing_prompt"     // 프롬프트 분석 중
  | "generating_code"      // 코드 생성 중
  | "sending_to_blender"   // Blender로 전송 중
  | "rendering"            // 렌더링 중
  | "analyzing_screenshot" // 스크린샷 분석 중
  | "refining_code"        // 코드 개선 중
  | "finalizing";          // 최종화 중

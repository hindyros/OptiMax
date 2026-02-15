/**
 * In-Memory Data Stores
 *
 * Simple in-memory storage for conversations and jobs.
 * Good enough for hackathon demo. Can upgrade to Redis/database later.
 *
 * IMPORTANT: Data will be lost on server restart, which is fine for demo.
 */

import { ConversationState, JobInfo, JobStatus, OptimizationStage } from '../types';

// ===== Conversation Store =====

/**
 * Store active refinement conversations
 * Key: conversation_id, Value: ConversationState
 */
const conversations = new Map<string, ConversationState>();

export function saveConversation(conversation: ConversationState): void {
  conversations.set(conversation.id, conversation);
  console.log(`[Store] Saved conversation ${conversation.id}`);
}

export function getConversation(id: string): ConversationState | undefined {
  return conversations.get(id);
}

export function deleteConversation(id: string): void {
  conversations.delete(id);
  console.log(`[Store] Deleted conversation ${id}`);
}

// ===== Job Store =====

/**
 * Store active optimization jobs
 * Key: job_id, Value: JobInfo
 */
const jobs = new Map<string, JobInfo>();

export function saveJob(job: JobInfo): void {
  jobs.set(job.id, job);
  console.log(`[Store] Saved job ${job.id} (status: ${job.status})`);
}

export function getJob(id: string): JobInfo | undefined {
  return jobs.get(id);
}

export function updateJobStatus(
  id: string,
  updates: Partial<JobInfo>
): void {
  const job = jobs.get(id);
  if (!job) {
    console.warn(`[Store] Job ${id} not found for update`);
    return;
  }

  Object.assign(job, updates);
  jobs.set(id, job);

  console.log(`[Store] Updated job ${id}:`, updates);
}

export function deleteJob(id: string): void {
  jobs.delete(id);
  console.log(`[Store] Deleted job ${id}`);
}

// ===== Utility Functions =====

/**
 * Get all active jobs (for debugging)
 */
export function getAllJobs(): JobInfo[] {
  return Array.from(jobs.values());
}

/**
 * Get all active conversations (for debugging)
 */
export function getAllConversations(): ConversationState[] {
  return Array.from(conversations.values());
}

/**
 * Clean up old completed jobs (optional cleanup)
 */
export function cleanupOldJobs(maxAgeMs: number = 3600000): void {
  // Default: delete jobs older than 1 hour
  const now = Date.now();

  for (const [id, job] of jobs.entries()) {
    if (job.completed_at) {
      const age = now - job.completed_at.getTime();
      if (age > maxAgeMs) {
        jobs.delete(id);
        console.log(`[Store] Cleaned up old job ${id}`);
      }
    }
  }
}

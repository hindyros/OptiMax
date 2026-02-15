/**
 * API Route: POST /api/optimize
 *
 * Main optimization endpoint. This is where the magic happens!
 *
 * Flow:
 * 1. Clear previous optimization (python optimus.py --clear)
 * 2. Write desc.txt and params.json to backend/current_query/
 * 3. Run OptiMUS pipeline (python optimus.py)
 * 4. Monitor progress by polling state files
 * 5. Run judge (python judge.py)
 * 6. Read verdict.json and return results
 *
 * This is a LONG-RUNNING process (30-120 seconds), so we:
 * - Return job_id immediately
 * - Run optimization in background
 * - Frontend polls /api/optimize/[jobId]/status for progress
 */

import { NextRequest, NextResponse } from 'next/server';
import { nanoid } from 'nanoid';
import {
  clearPreviousOptimization,
  runOptiMUS,
  runJudge,
} from '@/lib/utils/python-runner';
import {
  writeDescriptionFile,
  writeParamsFile,
  readVerdictFile,
  getCurrentOptimizationStage,
  isOptimizationComplete,
} from '@/lib/utils/file-ops';
import { extractParameters } from '@/lib/utils/llm';
import { saveJob, updateJobStatus } from '@/lib/utils/store';
import { JobInfo } from '@/lib/types';

/**
 * Main optimization handler
 */
export async function POST(request: NextRequest) {
  console.log('\n[API] POST /api/optimize');

  try {
    // Parse request body
    const body = await request.json();
    const { conversation_id, refined_description, params } = body;

    if (!conversation_id || !refined_description) {
      return NextResponse.json(
        { error: 'conversation_id and refined_description are required' },
        { status: 400 }
      );
    }

    console.log('[API] Starting optimization for conversation:', conversation_id);

    // Create job
    const jobId = nanoid();
    const job: JobInfo = {
      id: jobId,
      status: 'queued',
      current_stage: 'state_1_params',
      progress_percent: 0,
      conversation_id,
      created_at: new Date(),
    };

    saveJob(job);

    console.log('[API] ✓ Job created:', jobId);

    // Start optimization in background (don't await - return immediately)
    runOptimizationPipeline(jobId, refined_description, params).catch((error) => {
      console.error('[API] Optimization pipeline failed:', error.message);
      updateJobStatus(jobId, {
        status: 'failed',
        error: error.message,
      });
    });

    // Return job ID immediately
    return NextResponse.json({
      job_id: jobId,
      status: 'queued',
    });
  } catch (error: any) {
    console.error('[API] Error in /api/optimize:', error.message);

    return NextResponse.json(
      { error: 'Failed to start optimization', details: error.message },
      { status: 500 }
    );
  }
}

/**
 * Background optimization pipeline
 *
 * This runs independently and updates job status as it progresses
 */
async function runOptimizationPipeline(
  jobId: string,
  refinedDescription: string,
  params: any | null
): Promise<void> {
  console.log(`\n[Pipeline] Starting for job ${jobId}`);

  try {
    // Step 1: Clear previous optimization
    console.log('[Pipeline] Step 1: Clearing previous files...');
    updateJobStatus(jobId, {
      status: 'processing',
      current_stage: 'state_1_params',
      progress_percent: 5,
    });

    await clearPreviousOptimization();

    // Step 2: Write files
    console.log('[Pipeline] Step 2: Writing desc.txt and params.json...');

    await writeDescriptionFile(refinedDescription);

    if (params) {
      // User provided params
      await writeParamsFile(params);
    } else {
      // Extract params from description using LLM
      console.log('[Pipeline] Extracting parameters from description...');
      const extractedParams = await extractParameters(refinedDescription);
      await writeParamsFile(extractedParams);
    }

    updateJobStatus(jobId, { progress_percent: 10 });

    // Step 3: Run OptiMUS
    console.log('[Pipeline] Step 3: Running OptiMUS pipeline...');

    // Start progress monitoring in parallel
    monitorProgress(jobId);

    await runOptiMUS();

    console.log('[Pipeline] ✓ OptiMUS completed');

    // Step 4: Run judge
    console.log('[Pipeline] Step 4: Running judge...');
    updateJobStatus(jobId, {
      current_stage: 'complete',
      progress_percent: 95,
    });

    await runJudge();

    console.log('[Pipeline] ✓ Judge completed');

    // Step 5: Read results
    console.log('[Pipeline] Step 5: Reading verdict.json...');
    const verdict = await readVerdictFile();

    // Extract key metrics for frontend visualization
    const keyMetrics = extractKeyMetrics(verdict);

    // Update job with final results
    updateJobStatus(jobId, {
      status: 'completed',
      progress_percent: 100,
      completed_at: new Date(),
      result: {
        explanation: verdict.explanation,
        technical_details: verdict.technical_details,
        objective_value: verdict.objective_value,
        key_metrics: keyMetrics,
        direction: verdict.direction,
      },
    });

    console.log(`[Pipeline] ✓ Job ${jobId} completed successfully!`);
  } catch (error: any) {
    console.error(`[Pipeline] Job ${jobId} failed:`, error.message);

    updateJobStatus(jobId, {
      status: 'failed',
      error: error.message,
      completed_at: new Date(),
    });
  }
}

/**
 * Monitor optimization progress by polling state files
 */
async function monitorProgress(jobId: string): Promise<void> {
  console.log(`[Monitor] Starting progress monitoring for job ${jobId}`);

  const pollInterval = 1000;  // Check every second
  const maxDuration = 600000;  // 10 minutes max (OptiMUS can take 5-7 minutes)
  const startTime = Date.now();

  while (Date.now() - startTime < maxDuration) {
    try {
      // Check if optimization is complete
      const isComplete = await isOptimizationComplete();
      if (isComplete) {
        console.log('[Monitor] Optimization complete!');
        return;
      }

      // Get current stage from state files
      const { stage, progress } = await getCurrentOptimizationStage();

      // Update job status
      updateJobStatus(jobId, {
        current_stage: stage,
        progress_percent: progress,
      });

      // Wait before next poll
      await new Promise((resolve) => setTimeout(resolve, pollInterval));
    } catch (error: any) {
      console.warn('[Monitor] Poll error:', error.message);
      // Continue monitoring even if a poll fails
    }
  }

  console.warn('[Monitor] Monitoring timeout after 10 minutes');
}

/**
 * Extract key metrics from verdict for visualization
 *
 * This parses the technical_details to find decision variables
 */
function extractKeyMetrics(verdict: any): Record<string, number> {
  // Simple extraction: look for common patterns in technical_details
  // For demo, we'll extract from explanation text

  const keyMetrics: Record<string, number> = {
    'Objective Value': verdict.objective_value,
  };

  // Try to parse technical details for variable values
  // This is a simple regex-based extraction
  const technicalDetails = verdict.technical_details || '';

  // Look for patterns like "Product A: 20 units" or "x_A = 20"
  const variablePattern = /(\w+(?:\s+\w+)?)[:\s=]+(\d+(?:\.\d+)?)\s*(?:units?)?/gi;
  let match;

  while ((match = variablePattern.exec(technicalDetails)) !== null) {
    const [, name, value] = match;
    if (!name.toLowerCase().includes('optimal') && !name.toLowerCase().includes('objective')) {
      keyMetrics[name.trim()] = parseFloat(value);
    }
  }

  return keyMetrics;
}

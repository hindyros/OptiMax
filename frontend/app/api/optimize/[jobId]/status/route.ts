/**
 * API Route: GET /api/optimize/[jobId]/status
 *
 * Check optimization progress.
 *
 * Frontend polls this endpoint every second to get live progress updates.
 * Returns current stage, progress percentage, and status.
 */

import { NextRequest, NextResponse } from 'next/server';
import { getJob } from '@/lib/utils/store';

/**
 * Stage descriptions for user-friendly messages
 */
const STAGE_MESSAGES: Record<string, string> = {
  state_1_params: 'Extracting parameters...',
  state_2_objective: 'Identifying objective function...',
  state_3_constraints: 'Analyzing constraints...',
  state_4_constraints_modeled: 'Formulating constraint equations...',
  state_5_objective_modeled: 'Formulating objective function...',
  state_6_code: 'Generating solver code...',
  executing: 'Running optimization solver...',
  complete: 'Optimization complete!',
};

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params;

  console.log(`[API] GET /api/optimize/${jobId}/status`);

  try {
    // Get job from store
    const job = getJob(jobId);

    if (!job) {
      return NextResponse.json(
        { error: 'Job not found' },
        { status: 404 }
      );
    }

    // Prepare response
    const response = {
      job_id: jobId,
      status: job.status,
      current_stage: job.current_stage,
      progress_percent: job.progress_percent,
      message: STAGE_MESSAGES[job.current_stage] || 'Processing...',
      error: job.error,
    };

    return NextResponse.json(response);
  } catch (error: any) {
    console.error(`[API] Error in /api/optimize/${jobId}/status:`, error.message);

    return NextResponse.json(
      { error: 'Failed to get job status', details: error.message },
      { status: 500 }
    );
  }
}

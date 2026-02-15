/**
 * API Route: GET /api/optimize/[jobId]/result
 *
 * Get final optimization results.
 *
 * Called by frontend once optimization is complete.
 * Returns explanation, technical details, and key metrics for visualization.
 */

import { NextRequest, NextResponse } from 'next/server';
import { getJob } from '@/lib/utils/store';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params;

  console.log(`[API] GET /api/optimize/${jobId}/result`);

  try {
    // Get job from store
    const job = getJob(jobId);

    if (!job) {
      return NextResponse.json(
        { error: 'Job not found' },
        { status: 404 }
      );
    }

    // Check if job is completed
    if (job.status !== 'completed') {
      return NextResponse.json(
        {
          error: 'Job not completed yet',
          current_status: job.status,
          progress: job.progress_percent,
        },
        { status: 400 }
      );
    }

    // Check if results exist
    if (!job.result) {
      return NextResponse.json(
        { error: 'Results not available' },
        { status: 500 }
      );
    }

    // Return results
    return NextResponse.json(job.result);
  } catch (error: any) {
    console.error(`[API] Error in /api/optimize/${jobId}/result:`, error.message);

    return NextResponse.json(
      { error: 'Failed to get results', details: error.message },
      { status: 500 }
    );
  }
}

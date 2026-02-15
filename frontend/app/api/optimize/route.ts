/**
 * API Route: POST /api/optimize
 *
 * SIMPLIFIED WORKFLOW (Updated):
 * 1. Receive problem description only
 * 2. Write desc.txt to data_upload/
 * 3. Run main.py
 * 4. Monitor progress and return results
 *
 * NOTE: CSV and baseline features commented out for potential future use
 */

import { NextRequest, NextResponse } from 'next/server';
import { nanoid } from 'nanoid';
import { runMainPipeline } from '@/lib/utils/python-runner';
import {
  clearDataUpload,
  clearCurrentQuery,
  writeDescriptionToDataUpload,
  readVerdictFile,
  readReportFile,
  getCurrentOptimizationStage,
  isOptimizationComplete,
} from '@/lib/utils/file-ops';
import { saveJob, updateJobStatus } from '@/lib/utils/store';
import { JobInfo } from '@/lib/types';

export async function POST(request: NextRequest) {
  console.log('\n[API] POST /api/optimize');

  try {
    const formData = await request.formData();
    const conversation_id = formData.get('conversation_id') as string;
    const problem_description = formData.get('problem_description') as string;

    if (!conversation_id || !problem_description) {
      return NextResponse.json(
        { error: 'conversation_id and problem_description are required' },
        { status: 400 }
      );
    }

    console.log('[API] Starting optimization for conversation:', conversation_id);

    const jobId = nanoid();
    const job: JobInfo = {
      id: jobId,
      status: 'queued',
      current_stage: 'initializing' as any,
      progress_percent: 0,
      conversation_id,
      created_at: new Date(),
    };

    saveJob(job);
    console.log('[API] ✓ Job created:', jobId);

    runOptimizationPipeline(jobId, problem_description).catch((error) => {
      console.error('[API] Optimization pipeline failed:', error.message);
      updateJobStatus(jobId, {
        status: 'failed',
        error: error.message,
      });
    });

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

async function runOptimizationPipeline(jobId: string, problemDescription: string): Promise<void> {
  console.log(`\n[Pipeline] Starting for job ${jobId}`);

  try {
    console.log('[Pipeline] Step 1: Clearing data_upload/ and current_query/...');
    updateJobStatus(jobId, {
      status: 'processing',
      current_stage: 'initializing' as any,
      progress_percent: 5,
    });

    // Clear both directories to prevent stale progress detection
    await Promise.all([
      clearDataUpload(),
      clearCurrentQuery(),
    ]);

    console.log('[Pipeline] Step 2: Writing desc.txt to data_upload/...');
    await writeDescriptionToDataUpload(problemDescription);

    updateJobStatus(jobId, { progress_percent: 15 });

    console.log('[Pipeline] Step 3: Running main.py...');

    monitorProgress(jobId);
    await runMainPipeline();

    console.log('[Pipeline] ✓ main.py completed');

    console.log('[Pipeline] Step 4: Reading verdict.json and report.md...');
    const verdict = await readVerdictFile();
    const report = await readReportFile();

    // Extract key metrics from report (parse decision variables from Optimal Solution section)
    const extractedMetrics = extractMetricsFromReport(report, verdict);

    updateJobStatus(jobId, {
      status: 'completed',
      progress_percent: 100,
      completed_at: new Date(),
      result: {
        explanation: verdict.explanation || '',
        technical_details: verdict.technical_details || '',
        objective_value: verdict.objective_value,
        key_metrics: extractedMetrics,
        direction: verdict.direction,
        report_content: report,
        executive_summary: verdict.executive_summary,
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

async function monitorProgress(jobId: string): Promise<void> {
  console.log(`[Monitor] Starting progress monitoring for job ${jobId}`);

  const pollInterval = 2000;  // Increased to 2 seconds for better stage detection
  const maxDuration = 600000;
  const startTime = Date.now();

  while (Date.now() - startTime < maxDuration) {
    try {
      const isComplete = await isOptimizationComplete();
      if (isComplete) {
        console.log('[Monitor] Optimization complete!');
        return;
      }

      const { stage, progress, message } = await getCurrentOptimizationStage();

      updateJobStatus(jobId, {
        current_stage: stage as any,
        progress_percent: progress,
      });

      console.log(`[Monitor] ${stage} - ${progress}% - ${message}`);

      await new Promise((resolve) => setTimeout(resolve, pollInterval));
    } catch (error: any) {
      console.warn('[Monitor] Poll error:', error.message);
    }
  }

  console.warn('[Monitor] Monitoring timeout after 10 minutes');
}

/**
 * Extract key metrics from report.md for charts
 * Parses the "Optimal Solution" table to get decision variables
 */
function extractMetricsFromReport(report: string, verdict: any): Record<string, number> {
  const metrics: Record<string, number> = {
    'Objective Value': verdict.objective_value || 0,
  };

  try {
    // Look for the "Optimal Solution" section with a table
    const optimalSolutionMatch = report.match(/### Optimal Solution\s+([\s\S]*?)(?=\n###|$)/i);

    if (optimalSolutionMatch) {
      const solutionSection = optimalSolutionMatch[1];

      // Extract table rows (format: | Variable | Value | Description |)
      const tableRowRegex = /\|\s*\$?(\w+(?:_\d+)?)\$?\s*\|\s*([\d.]+)\s*\|/g;
      let match;

      while ((match = tableRowRegex.exec(solutionSection)) !== null) {
        const [, varName, value] = match;
        if (varName && value && !isNaN(parseFloat(value))) {
          // Clean up variable name for display
          const cleanName = varName.replace(/_/g, ' ').replace(/x\s*/i, '');
          if (parseFloat(value) > 0) {  // Only show non-zero values
            metrics[cleanName] = parseFloat(value);
          }
        }
      }
    }

    // If no variables found in table, try to extract from other sections
    if (Object.keys(metrics).length === 1) {
      // Try executive summary bullet points
      const summaryMatch = report.match(/## Executive Summary\s+([\s\S]*?)(?=\n##|$)/i);
      if (summaryMatch) {
        const summary = summaryMatch[1];
        const allocationRegex = /\*\*(\d+)\s+([^*]+)\s+(?:stores?|beds?|units?)\*\*/gi;
        let allocMatch;

        while ((allocMatch = allocationRegex.exec(summary)) !== null) {
          const [, value, name] = allocMatch;
          metrics[name.trim()] = parseFloat(value);
        }
      }
    }
  } catch (error) {
    console.warn('[Metrics] Failed to extract metrics from report:', error);
  }

  console.log('[Metrics] Extracted metrics:', metrics);
  return metrics;
}

/**
 * Optimization Processing Page (/optimize/[jobId])
 *
 * Real-time progress visualization while OptiMUS runs.
 *
 * Polls /api/optimize/[jobId]/status every second to get progress updates.
 * Shows current stage, progress bar, and user-friendly messages.
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { motion } from 'framer-motion';

interface JobStatus {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  current_stage: string;
  progress_percent: number;
  message: string;
  error?: string;
}

/**
 * Sanitize error messages for user display
 * Converts technical stack traces into user-friendly messages
 */
function sanitizeError(error: string): string {
  // Check for common error patterns and return user-friendly messages

  // Generic pipeline/command failures (hide technical details)
  if (error.includes('OptiMUS pipeline failed') || error.includes('Command failed: python')) {
    return 'The optimization process encountered an issue. Our team is working to resolve it. Please try again or contact support if the problem persists.';
  }

  // Timeout errors
  if (error.includes('timeout') || error.includes('ETIMEDOUT')) {
    return 'The optimization is taking longer than expected. This problem may be too complex. Please try simplifying it or contact support.';
  }

  // Missing Python packages
  if (error.includes('ModuleNotFoundError')) {
    return 'System configuration issue detected. Please contact support or try again later.';
  }

  // Gurobi license issues
  if (error.includes('GurobiError') || error.includes('license')) {
    return 'Solver license configuration issue. Please contact support.';
  }

  // File not found errors
  if (error.includes('FileNotFoundError') || error.includes('No such file')) {
    return 'Required system files are missing. Please contact support.';
  }

  // OpenAI API errors
  if (error.includes('OpenAI') || error.includes('API key')) {
    return 'AI service configuration issue. Please contact support.';
  }

  // Python not found
  if (error.includes('python: not found') || error.includes('command not found')) {
    return 'System configuration issue detected. Please contact support.';
  }

  // Generic fallback - try to extract the last line which often has the actual error
  const lines = error.split('\n').filter(line => line.trim());
  const lastLine = lines[lines.length - 1];

  // If it's a short, readable error without technical jargon, use it
  if (lastLine &&
      lastLine.length < 150 &&
      !lastLine.includes('File "') &&
      !lastLine.includes('python') &&
      !lastLine.includes('Traceback') &&
      !lastLine.includes('.py')) {
    return lastLine;
  }

  // Otherwise, generic message
  return 'We encountered an unexpected issue while processing your request. Please try again or contact support if the problem continues.';
}

export default function OptimizePage() {
  const router = useRouter();
  const params = useParams();
  const jobId = params?.jobId as string;

  // State
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  /**
   * Poll job status
   */
  useEffect(() => {
    if (!jobId) return;

    let pollInterval: NodeJS.Timeout;

    const pollStatus = async () => {
      try {
        const response = await fetch(`/api/optimize/${jobId}/status`);
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || 'Failed to fetch status');
        }

        setStatus(data);

        // If completed, redirect to results
        if (data.status === 'completed') {
          clearInterval(pollInterval);
          setTimeout(() => {
            router.push(`/results/${jobId}`);
          }, 1000); // Brief delay to show 100% completion
        }

        // If failed, show error
        if (data.status === 'failed') {
          clearInterval(pollInterval);
          setError(sanitizeError(data.error || 'Optimization failed'));
        }
      } catch (err: any) {
        console.error('Poll error:', err);
        setError(sanitizeError(err.message));
      }
    };

    // Initial poll
    pollStatus();

    // Poll every second
    pollInterval = setInterval(pollStatus, 1000);

    return () => {
      clearInterval(pollInterval);
    };
  }, [jobId, router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <div className="max-w-lg w-full bg-surface border border-error rounded-lg p-8 text-center">
          <div className="text-5xl mb-4">❌</div>
          <h2 className="text-2xl font-bold text-error mb-4">Optimization Failed</h2>
          <p className="text-foreground-dim mb-6 whitespace-pre-wrap wrap-break-word max-w-full">
            {error}
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={() => router.push('/refine')}
              className="px-6 py-2 bg-primary text-background font-semibold rounded-lg hover:bg-opacity-90 transition-all"
            >
              Try Again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2 bg-surface border border-border text-foreground font-semibold rounded-lg hover:bg-code-bg transition-all"
            >
              Reload Page
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4">⏳</div>
          <p className="text-foreground-dim">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-2xl w-full">
         {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <div className="text-6xl mb-4 animate-spin-slow">⚙️</div>
          <h1 className="text-3xl font-bold text-foreground mb-2">Optimizing...</h1>
          <p className="text-foreground-dim">
            We're solving your optimization problem. This may take up to 10 minutes.
          </p>
        </motion.div>

        {/* Progress Bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-surface border border-border rounded-lg p-8 space-y-6"
        >
          {/* Current Stage Message */}
          <div className="text-center">
            <motion.p
              key={status.message}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-lg font-semibold text-primary"
            >
              {status.message}
            </motion.p>
          </div>

          {/* Progress Bar */}
          <div className="w-full h-3 bg-code-bg rounded-full overflow-hidden">
            <motion.div
              className="h-full progress-shimmer rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${status.progress_percent}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          </div>

          {/* Progress Percentage */}
          <div className="text-center">
            <motion.p
              key={status.progress_percent}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-4xl font-bold text-foreground"
            >
              {status.progress_percent}%
            </motion.p>
          </div>

          {/* Stage Indicators */}
          <div className="grid grid-cols-4 gap-2 mt-8">
            {[
              { label: 'Extracting', progress: 25 },
              { label: 'Modeling', progress: 50 },
              { label: 'Coding', progress: 75 },
              { label: 'Solving', progress: 100 },
            ].map((stage, index) => (
              <div key={index} className="text-center">
                <div
                  className={`w-full h-2 rounded-full ${
                    status.progress_percent >= stage.progress
                      ? 'bg-success'
                      : 'bg-code-bg'
                  }`}
                />
                <p className="text-xs text-foreground-dim mt-2">{stage.label}</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Info Text */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="text-center text-sm text-foreground-dim mt-8"
        >
          Running OptiMUS pipeline: parameter extraction → mathematical formulation
          → code generation → solver execution → results evaluation
        </motion.p>
      </div>
    </div>
  );
}

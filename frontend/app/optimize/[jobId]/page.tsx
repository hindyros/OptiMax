/**
 * Optimization Processing Page (/optimize/[jobId])
 *
 * Real-time progress visualization while OptiMATE runs.
 *
 * NEW WORKFLOW:
 * - Polls /api/optimize/[jobId]/status every second
 * - Shows unified "OptiMATE" branding (not OptiMUS/OptiMind separately)
 * - Displays: Preprocessing → Analyzing → Solving → Finalizing → Complete
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
 */
function sanitizeError(error: string): string {
  if (error.includes('Main pipeline failed') || error.includes('Command failed: python')) {
    return 'The optimization process encountered an issue. Please try again or contact support if the problem persists.';
  }

  if (error.includes('timeout') || error.includes('ETIMEDOUT')) {
    return 'The optimization is taking longer than expected. This problem may be too complex. Please try simplifying it or contact support.';
  }

  if (error.includes('ModuleNotFoundError')) {
    return 'System configuration issue detected. Please contact support or try again later.';
  }

  if (error.includes('GurobiError') || error.includes('license')) {
    return 'Solver license configuration issue. Please contact support.';
  }

  if (error.includes('FileNotFoundError') || error.includes('No such file')) {
    return 'Required system files are missing. Please contact support.';
  }

  if (error.includes('OpenAI') || error.includes('API key')) {
    return 'AI service configuration issue. Please contact support.';
  }

  if (error.includes('python: not found') || error.includes('command not found')) {
    return 'System configuration issue detected. Please contact support.';
  }

  const lines = error.split('\n').filter(line => line.trim());
  const lastLine = lines[lines.length - 1];

  if (lastLine &&
      lastLine.length < 150 &&
      !lastLine.includes('File "') &&
      !lastLine.includes('python') &&
      !lastLine.includes('Traceback') &&
      !lastLine.includes('.py')) {
    return lastLine;
  }

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
      <div className="min-h-screen flex items-center justify-center p-4 sm:p-6 md:p-8 bg-gradient-to-br from-background via-background to-surface/30 particle-bg relative overflow-hidden">
        {/* Floating orbs */}
        <div className="absolute top-20 left-10 w-64 h-64 bg-error/10 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-error/5 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />

        <div className="max-w-md md:max-w-lg w-full glass-card gradient-border rounded-2xl p-6 sm:p-8 text-center relative z-10">
          <div className="text-5xl mb-4">❌</div>
          <h2 className="text-2xl font-bold text-error mb-4">Optimization Failed</h2>
          <p className="text-foreground-dim mb-6 whitespace-pre-wrap wrap-break-word max-w-full">
            {error}
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={() => router.push('/refine')}
              className="btn-gradient px-6 py-2 text-background font-semibold rounded-lg shadow-lg"
            >
              Try Again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2 glass-card border border-border text-foreground font-semibold rounded-lg card-hover"
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
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-surface/30 particle-bg">
        <div className="text-center">
          <div className="text-4xl mb-4 animate-pulse">⏳</div>
          <p className="text-foreground-dim">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6 md:p-8 bg-gradient-to-br from-background via-background to-surface/30 particle-bg relative overflow-hidden">
      {/* Animated floating orbs */}
      <div className="absolute top-20 left-10 w-64 h-64 bg-primary/10 rounded-full blur-3xl animate-float" />
      <div className="absolute bottom-20 right-10 w-96 h-96 bg-accent/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />
      <div className="absolute top-1/2 left-1/2 w-80 h-80 bg-success/5 rounded-full blur-3xl animate-float" style={{ animationDelay: '4s' }} />

      <div className="max-w-xl md:max-w-2xl lg:max-w-3xl xl:max-w-4xl w-full relative z-10">
         {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8 sm:mb-10 md:mb-12"
        >
          <motion.div
            className="text-4xl sm:text-5xl md:text-6xl mb-3 sm:mb-4 inline-block"
            animate={{ rotate: [0, 360] }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
          >
            ⚙️
          </motion.div>
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-2">
            <span className="text-foreground">Opti</span>
            <span className="text-primary italic">MATE</span>
            <span className="text-foreground"> is Working...</span>
          </h1>
          {/* <p className="text-foreground-dim">
            We're solving your optimization problem. This may take up to 10 minutes depending on complexity.
          </p> */}
          <p className="text-xs sm:text-sm text-foreground-dim mt-2">
            Expected processing time: ≤10 mins
          </p>
        </motion.div>

        {/* Progress Container with Glassmorphism */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-card gradient-border rounded-2xl p-4 sm:p-6 md:p-8 space-y-4 sm:space-y-5 md:space-y-6"
        >
          {/* Current Stage Message */}
          <div className="text-center">
            <motion.p
              key={status.message}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-base sm:text-lg md:text-xl font-semibold gradient-text"
            >
              {status.message}
            </motion.p>
          </div>

          {/* Progress Bar with Gradient */}
          <div className="w-full h-3 sm:h-4 bg-code-bg rounded-full overflow-hidden shadow-inner">
            <motion.div
              className="h-full progress-shimmer rounded-full relative"
              initial={{ width: 0 }}
              animate={{ width: `${status.progress_percent}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-primary via-accent to-primary animate-gradient bg-size-200" />
            </motion.div>
          </div>

          {/* Progress Percentage with Glow */}
          <div className="text-center">
            <motion.p
              key={status.progress_percent}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-4xl sm:text-5xl md:text-6xl font-bold gradient-text neon-glow"
            >
              {status.progress_percent}%
            </motion.p>
          </div>

          {/* Enhanced Stage Indicators */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3 mt-6 sm:mt-8">
            {[
              { label: 'Preprocessing', progress: 15, icon: '🔍' },
              { label: 'Analyzing', progress: 35, icon: '🧠' },
              { label: 'Solving', progress: 60, icon: '⚡' },
              { label: 'Finalizing', progress: 85, icon: '✨' },
            ].map((stage, index) => (
              <motion.div
                key={index}
                className="text-center"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + index * 0.1 }}
              >
                <div className="mb-1 sm:mb-2 text-xl sm:text-2xl opacity-50">
                  {status.progress_percent >= stage.progress ? stage.icon : '⭕'}
                </div>
                <div
                  className={`w-full h-1.5 sm:h-2 rounded-full transition-all duration-500 ${
                    status.progress_percent >= stage.progress
                      ? 'bg-gradient-to-r from-success via-primary to-success bg-size-200 animate-gradient shadow-glow'
                      : 'bg-code-bg'
                  }`}
                />
                <p className={`text-xs sm:text-sm mt-1 sm:mt-2 transition-all duration-300 ${
                  status.progress_percent >= stage.progress
                    ? 'text-foreground font-semibold'
                    : 'text-foreground-dim'
                }`}>
                  {stage.label}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Info Text with Glass Effect */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="text-center text-xs sm:text-sm text-foreground-dim mt-6 sm:mt-8 glass-card rounded-lg p-3 sm:p-4"
        >
          <span className="text-foreground">Opti</span>
          <span className="text-primary italic">MATE</span>
          <span className="text-foreground"> is analyzing your problem, generating mathematical formulations,
          and finding the optimal solution with baseline comparison.</span>
        </motion.div>
      </div>
    </div>
  );
}

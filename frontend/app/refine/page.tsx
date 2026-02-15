/**
 * Refinement Page (/refine)
 *
 * SIMPLIFIED WORKFLOW (Updated):
 * 1. User enters problem description in one textarea
 * 2. Submit directly to optimization (no CSV, no baseline questions)
 * 3. Description saved as desc.txt in data_upload/
 * 4. Backend runs main.py to process
 *
 * NOTE: CSV upload and baseline assessment features commented out for potential future use
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';

export default function RefinePage() {
  const router = useRouter();

  // State
  const [problemDescription, setProblemDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Handle optimization submission
   */
  const handleSubmit = async () => {
    if (!problemDescription.trim()) {
      setError('Please enter a problem description');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      // Submit directly to optimization
      const formData = new FormData();
      formData.append('conversation_id', Date.now().toString()); // Simple ID
      formData.append('problem_description', problemDescription);
      formData.append('refined_description', problemDescription); // No refinement, same text

      const response = await fetch('/api/optimize', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to start optimization');
      }

      // Redirect to processing page
      router.push(`/optimize/${data.job_id}`);
    } catch (err: any) {
      console.error('Submission error:', err);
      setError(err.message || 'Failed to submit. Please try again.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6 md:p-8 bg-gradient-to-br from-background via-background to-surface/30">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-xl md:max-w-2xl lg:max-w-4xl xl:max-w-5xl"
      >
        {/* Header */}
        <div className="text-center mb-8 sm:mb-12 px-4">
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="text-4xl sm:text-5xl md:text-6xl mb-4 sm:mb-6"
          >
            ✨
          </motion.div>
          <motion.h1
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-foreground mb-3 sm:mb-4 bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent"
          >
            Describe Your Optimization Problem
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-base sm:text-lg md:text-xl text-foreground-dim max-w-2xl mx-auto"
          >
            Enter your optimization challenge below and let <span className="text-foreground">Opti</span><span className="text-primary italic font-bold">MATE</span> find the optimal solution
          </motion.p>
        </div>

        {/* Input Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-card gradient-border rounded-2xl p-4 sm:p-6 md:p-8 shadow-2xl"
        >
          <div className="space-y-4 sm:space-y-6">
            {/* Textarea */}
            <div>
              <label className="block text-sm font-semibold text-foreground mb-3">
                Problem Description
              </label>
              <textarea
                value={problemDescription}
                onChange={(e) => setProblemDescription(e.target.value)}
                placeholder="Example: I need to optimize hospital bed allocation across 7 departments to maximize patient care while minimizing costs. Each department has different capacities, staffing levels, and patient demands..."
                className="w-full h-48 sm:h-56 md:h-64 lg:h-80 px-3 sm:px-4 py-3 bg-code-bg border-2 border-border rounded-xl text-foreground text-sm sm:text-base placeholder-foreground-dim focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all resize-none"
                disabled={isSubmitting}
              />
              <p className="text-xs sm:text-sm text-foreground-dim mt-2">
                Be as detailed as possible about your constraints, objectives, and data
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="p-4 bg-error/10 border border-error rounded-lg"
              >
                <p className="text-error text-sm">{error}</p>
              </motion.div>
            )}

            {/* Submit Button */}
            <button
              onClick={handleSubmit}
              disabled={isSubmitting || !problemDescription.trim()}
              className="w-full py-3 sm:py-4 btn-gradient text-background font-bold text-base sm:text-lg rounded-xl hover:shadow-2xl hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 transition-all duration-300"
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2 sm:gap-3">
                  <span className="inline-block animate-spin">⚙️</span>
                  <span className="hidden sm:inline">Processing...</span>
                  <span className="sm:hidden">...</span>
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2 sm:gap-3">
                  🚀 Optimize Now
                </span>
              )}
            </button>

            {/* Example Problems Link */}
            <div className="text-center pt-2 sm:pt-4">
              <button
                onClick={() => {
                  setProblemDescription(
                    "I need to optimize hospital bed allocation across 7 departments to maximize patient care while minimizing daily operational costs. We have different capacities, staffing levels, and patient demands for each department. Priority departments include Emergency, ICU, and Surgery."
                  );
                }}
                className="text-xs sm:text-sm text-primary hover:text-accent underline transition-colors"
              >
                Load Example Problem
              </button>
            </div>
          </div>
        </motion.div>

        {/* Additional Info */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-6 sm:mt-8 text-center text-xs sm:text-sm text-foreground-dim"
        >
          <p>Expected processing time: ≤10 minutes</p>
        </motion.div>
      </motion.div>
    </div>
  );
}

/*
 * COMMENTED OUT FEATURES FOR POTENTIAL FUTURE USE:
 *
 * - CSV Upload Functionality
 * - Baseline Assessment Questions (LLM back-and-forth)
 * - Multi-step form with animations
 *
 * To re-enable, see git history or previous version
 */

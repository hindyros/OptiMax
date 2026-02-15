/**
 * Results Page (/results/[jobId])
 *
 * Final results display with:
 * 1. Metric cards (key values)
 * 2. Simple bar chart (decision variables)
 * 3. Explanation (markdown-rendered executive summary)
 * 4. Technical details (collapsible: LaTeX math + syntax-highlighted code)
 */

'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import remarkGfm from 'remark-gfm';
import rehypeKatex from 'rehype-katex';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { vs } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useTheme } from 'next-themes';
import { generateHeyGenVideo } from '@/lib/heygen-api';
import 'katex/dist/katex.min.css';

interface OptimizationResult {
  explanation: string;
  technical_details: string;
  objective_value: number;
  key_metrics: Record<string, number>;
  direction: 'maximize' | 'minimize';
  report_content?: string;  // NEW: Full report.md content
  baseline_comparison?: string;  // NEW: Baseline comparison section
  has_baseline_comparison?: boolean;  // NEW: Flag
  executive_summary?: string;  // NEW: Executive summary
}

export default function ResultsPage() {
  const router = useRouter();
  const params = useParams();
  const jobId = params?.jobId as string;

  // State
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAIPresentation, setShowAIPresentation] = useState(false);
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [videoGenerationProgress, setVideoGenerationProgress] = useState<string>('');
  const [videoUrl, setVideoUrl] = useState<string | null>(null);

  // Summary state
  const [summary, setSummary] = useState<string>('');
  const [isLoadingSummary, setIsLoadingSummary] = useState(false);
  const [showFullReport, setShowFullReport] = useState(false);

  /**
   * Fetch results on mount
   */
  useEffect(() => {
    if (!jobId) return;

    const fetchResults = async () => {
      try {
        const response = await fetch(`/api/optimize/${jobId}/result`);
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || 'Failed to fetch results');
        }

        setResult(data);
        setIsLoading(false);

        // Generate summary after loading results
        generateSummary(data.report_content || data.explanation);
      } catch (err) {
        console.error('Fetch results error:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch results');
        setIsLoading(false);
      }
    };

    fetchResults();
  }, [jobId]);

  /**
   * Generate AI summary of the report
   */
  const generateSummary = async (reportContent: string) => {
    if (!reportContent) return;

    setIsLoadingSummary(true);

    try {
      const response = await fetch('/api/summarize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ report: reportContent }),
      });

      const data = await response.json();

      if (data.summary) {
        setSummary(data.summary);
      }
    } catch (err) {
      console.error('Summary generation error:', err);
      setSummary('Summary unavailable. Please review the detailed report below.');
    } finally {
      setIsLoadingSummary(false);
    }
  };

  /**
   * Download report as PDF
   */
  const handleDownloadPDF = async () => {
    if (!result?.report_content) return;

    try {
      const response = await fetch('/api/generate-pdf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          markdown: result.report_content,
          jobId: jobId,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to generate PDF');
      }

      // Download the PDF
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `optima-report-${jobId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('PDF generation error:', err);
      alert('Failed to generate PDF. Please try again.');
    }
  };

  /**
   * Generate HeyGen AI presentation using the library
   */
  const handleGenerateAIPresentation = async () => {
    if (!result || !summary) {
      alert('Please wait for the summary to be generated first.');
      return;
    }

    setIsGeneratingVideo(true);
    setVideoGenerationProgress('Preparing...');

    try {
      // Use the LLM-generated summary for the video script
      // Remove markdown formatting for cleaner speech
      const cleanSummary = summary
        .replace(/\*\*/g, '')        // Remove bold
        .replace(/\*/g, '')           // Remove italics
        .replace(/`/g, '')            // Remove inline code
        .replace(/#+\s/g, '')         // Remove headers
        .replace(/\n\n/g, '. ')       // Replace double newlines with periods
        .replace(/\n/g, ' ')          // Replace single newlines with spaces
        .replace(/\s+/g, ' ')         // Normalize whitespace
        .trim();

      // Create engaging intro and use the summary
      const script = `Hello! Let me walk you through your optimization results. ${cleanSummary}. Thank you for using OptiMATE!`;

      console.log('[HeyGen] Generating video with script:', script);

      // Use the library's clean API with progress callback
      const videoUrl = await generateHeyGenVideo(script, (progress) => {
        console.log('[HeyGen] Progress:', progress);
        setVideoGenerationProgress(progress);
      });

      console.log('[HeyGen] ✓ Video ready:', videoUrl);
      setVideoUrl(videoUrl);
      setShowAIPresentation(true);
      setVideoGenerationProgress('');

    } catch (err) {
      console.error('[HeyGen] Generation error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      alert(`Failed to generate AI presentation: ${errorMessage}\n\nPlease check:\n1. HeyGen API key is valid (NEXT_PUBLIC_HEYGEN_API_KEY in .env.local)\n2. You have credits in your HeyGen account\n3. Check browser console for more details`);
      setVideoGenerationProgress('');
    } finally {
      setIsGeneratingVideo(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden bg-app-gradient">
        <div className="text-center">
          <div className="text-4xl sm:text-5xl mb-4 animate-pulse">📊</div>
          <p className="text-foreground-dim text-sm sm:text-base">Loading results...</p>
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 sm:p-6 md:p-8 relative overflow-hidden bg-app-gradient">
        <div className="max-w-md w-full glass-card gradient-border rounded-2xl p-6 sm:p-8 text-center relative z-10">
          <div className="text-5xl mb-4">❌</div>
          <h2 className="text-2xl font-bold text-error mb-4">Failed to Load Results</h2>
          <p className="text-foreground-dim mb-6">{error || 'Unknown error'}</p>
          <button
            onClick={() => router.push('/refine')}
            className="btn-gradient px-6 py-2 text-background font-semibold rounded-lg shadow-lg"
          >
            Start New Optimization
          </button>
        </div>
      </div>
    );
  }

  // Prepare chart data
  const chartData = Object.entries(result.key_metrics)
    .filter(([key]) => key !== 'Objective Value')
    .map(([name, value]) => ({ name, value }));

  return (
    <div className="min-h-screen p-4 sm:p-6 md:p-8 relative overflow-hidden bg-app-gradient">
      <div className="max-w-xl md:max-w-3xl lg:max-w-4xl xl:max-w-5xl mx-auto space-y-6 sm:space-y-8 relative z-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center px-4"
        >
          <motion.div
            className="text-4xl sm:text-5xl md:text-6xl mb-3 sm:mb-4 inline-block"
          >
            ✨
          </motion.div>
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-2 sm:mb-3" style={{ color: '#e76a28'}}>Optimization Complete</h1>
          <p className="text-foreground-dim text-sm sm:text-base md:text-lg">
            Your optimal solution has been found and verified.
          </p>
        </motion.div>

        {/* Metric Cards */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6"
        >
          {Object.entries(result.key_metrics).map(([key, value], index) => (
            <MetricCard key={key} label={key} value={value} delay={index * 0.05} />
          ))}
        </motion.div>

        {/* Chart */}
        {chartData.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass-card gradient-border rounded-2xl p-4 sm:p-6"
          >
            <div className="mb-3 sm:mb-4">
              <h2 className="text-lg sm:text-xl font-semibold gradient-text mb-1 sm:mb-2">Decision Variables</h2>
              <p className="text-xs sm:text-sm text-foreground-dim">
                Optimal values for each decision variable in your problem
              </p>
            </div>
            <ResponsiveContainer width="100%" height={250} className="sm:h-[300px]">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#45475a" />
                <XAxis dataKey="name" stroke="#cdd6f4" />
                <YAxis stroke="#cdd6f4" label={{ value: 'Quantity', angle: -90, position: 'insideLeft', fill: '#cdd6f4' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#2d2d44',
                    border: '1px solid #45475a',
                    borderRadius: '8px',
                    color: '#cdd6f4',
                  }}
                />
                <Bar dataKey="value" fill="#89b4fa" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </motion.div>
        )}

        {/* Executive Summary Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="glass-card gradient-border rounded-2xl p-4 sm:p-6 md:p-8"
        >
          <h2 className="text-xl sm:text-2xl font-semibold mb-4 sm:mb-6" style={{ color: '#e76a28' }}>
            Executive Summary
          </h2>

          {isLoadingSummary ? (
            <div className="flex items-center gap-3 text-foreground-dim">
              <span className="inline-block animate-spin text-xl">⚙️</span>
              <span className="text-sm sm:text-base">Generating summary...</span>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="prose prose-invert max-w-none text-foreground-dim text-sm sm:text-base leading-relaxed">
                <ReactMarkdown>
                  {summary}
                </ReactMarkdown>
              </div>

              <button
                onClick={() => setShowFullReport(!showFullReport)}
                className="flex items-center gap-2 text-primary hover:text-accent transition-colors text-sm sm:text-base font-semibold mt-4"
              >
                <span className="text-lg">{showFullReport ? '▼' : '▶'}</span>
                <span>{showFullReport ? 'Hide' : 'View'} Detailed Report</span>
              </button>
            </div>
          )}
        </motion.div>

        {/* Full Report - Collapsible */}
        {showFullReport && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="glass-card gradient-border rounded-2xl p-4 sm:p-6 md:p-8"
          >
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4 sm:mb-6">
              <h2 className="text-xl sm:text-2xl font-semibold gradient-text">Detailed Optimization Report</h2>
              <button
                onClick={handleDownloadPDF}
                className="btn-gradient px-3 sm:px-4 py-2 text-background text-sm sm:text-base font-semibold rounded-lg shadow-lg flex items-center gap-2 card-hover w-full sm:w-auto justify-center"
                title="Download report as PDF"
              >
                <span>📄</span>
                <span className="hidden sm:inline">Download PDF</span>
                <span className="sm:hidden">PDF</span>
              </button>
            </div>
            <div className="prose prose-invert max-w-none">
              <MarkdownRenderer content={result.report_content || result.explanation} />
            </div>
          </motion.div>
        )}

        {/* AI Presentation Section */}
        {showAIPresentation && videoUrl && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="glass-card gradient-border rounded-2xl p-4 sm:p-6 md:p-8"
          >
            <h2 className="text-xl sm:text-2xl font-semibold gradient-text mb-4 sm:mb-6 text-center">
              🎬 AI Presentation
            </h2>
            <div className="aspect-video rounded-lg overflow-hidden bg-code-bg">
              <video
                src={videoUrl}
                controls
                autoPlay
                className="w-full h-full"
              >
                Your browser does not support the video tag.
              </video>
            </div>
            <p className="text-sm text-foreground-dim text-center mt-4">
              AI-generated presentation of your optimization results
            </p>
          </motion.div>
        )}

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="flex flex-col sm:flex-row justify-center gap-3 sm:gap-4"
        >
          <button
            onClick={() => router.push('/refine')}
            className="btn-gradient px-6 sm:px-8 py-2.5 sm:py-3 text-background text-sm sm:text-base font-semibold rounded-xl shadow-lg card-hover"
          >
            Solve Another Problem
          </button>

          {!showAIPresentation && (
            <button
              onClick={handleGenerateAIPresentation}
              disabled={isGeneratingVideo}
              className="px-6 sm:px-8 py-2.5 sm:py-3 glass-card gradient-border text-foreground text-sm sm:text-base font-semibold rounded-xl card-hover disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isGeneratingVideo ? (
                <>
                  <span className="inline-block animate-spin mr-2">⚙️</span>
                  {videoGenerationProgress || 'Generating AI Presenter...'}
                </>
              ) : (
                <>🎬 Get AI Presentation</>
              )}
            </button>
          )}
        </motion.div>
      </div>
    </div>
  );
}

/**
 * Markdown Renderer Component
 * Properly renders report.md with LaTeX, code highlighting, and tables
 */
function MarkdownRenderer({ content }: { content: string }) {
  const { theme } = useTheme();
  const codeTheme = theme === 'light' ? vs : vscDarkPlus;

  return (
    <ReactMarkdown
      remarkPlugins={[remarkMath, remarkGfm]}
      rehypePlugins={[rehypeKatex]}
      components={{
        // Headings
        h1: ({ node, ...props }) => (
          <h1 className="text-3xl font-bold text-foreground mt-8 mb-4 border-b border-border pb-2" {...props} />
        ),
        h2: ({ node, ...props }) => (
          <h2 className="text-2xl font-semibold text-foreground mt-6 mb-3" {...props} />
        ),
        h3: ({ node, ...props }) => (
          <h3 className="text-xl font-semibold text-foreground mt-4 mb-2" {...props} />
        ),
        h4: ({ node, ...props }) => (
          <h4 className="text-lg font-semibold text-foreground mt-3 mb-2" {...props} />
        ),

        // Paragraphs and text
        p: ({ node, ...props }) => (
          <p className="text-foreground-dim mb-4 leading-relaxed" {...props} />
        ),
        strong: ({ node, ...props }) => (
          <strong className="text-foreground font-semibold" {...props} />
        ),
        em: ({ node, ...props }) => (
          <em className="text-foreground-dim italic" {...props} />
        ),

        // Lists
        ul: ({ node, ...props }) => (
          <ul className="list-disc list-inside text-foreground-dim space-y-2 mb-4" {...props} />
        ),
        ol: ({ node, ...props }) => (
          <ol className="list-decimal list-inside text-foreground-dim space-y-2 mb-4" {...props} />
        ),
        li: ({ node, ...props }) => (
          <li className="text-foreground-dim" {...props} />
        ),

        // Blockquote
        blockquote: ({ node, ...props }) => (
          <blockquote className="border-l-4 border-primary pl-4 italic text-foreground-dim my-4 bg-surface/50 py-2" {...props} />
        ),

        // Tables
        table: ({ node, ...props }) => (
          <div className="overflow-x-auto mb-6">
            <table className="min-w-full border border-border rounded-lg" {...props} />
          </div>
        ),
        thead: ({ node, ...props }) => (
          <thead className="bg-surface" {...props} />
        ),
        tbody: ({ node, ...props }) => (
          <tbody className="divide-y divide-border" {...props} />
        ),
        tr: ({ node, ...props }) => (
          <tr className="hover:bg-surface/50 transition-colors" {...props} />
        ),
        th: ({ node, ...props }) => (
          <th className="px-4 py-3 text-left text-sm font-semibold text-foreground border-r border-border last:border-r-0" {...props} />
        ),
        td: ({ node, ...props }) => (
          <td className="px-4 py-3 text-sm text-foreground-dim border-r border-border last:border-r-0" {...props} />
        ),

        // Code blocks and inline code
        code: ({ node, inline, className, children, ...props }: {
          node?: any;
          inline?: boolean;
          className?: string;
          children?: React.ReactNode;
        }) => {
          const match = /language-(\w+)/.exec(className || '');
          const language = match ? match[1] : 'Python';
          const content = String(children).replace(/\n$/, '');

          if (!inline && match) {
            // Code block with syntax highlighting
            return (
              <div className="my-4 rounded-lg overflow-hidden">
                <SyntaxHighlighter
                  language={language}
                  style={codeTheme}
                  customStyle={{
                    margin: 0,
                    borderRadius: '8px',
                    fontSize: '14px',
                    maxWidth: '100%',
                    padding: '1.5rem',
                  }}
                  wrapLongLines={false}
                  showLineNumbers={false}
                  {...props}
                >
                  {content}
                </SyntaxHighlighter>
              </div>
            );
          } else {
            // Inline code (math is handled by rehype-katex)
            return (
              <code
                className="bg-code-bg px-2 py-1 rounded text-sm text-accent font-mono"
                {...props}
              >
                {children}
              </code>
            );
          }
        },

        // Horizontal rule
        hr: ({ node, ...props }) => (
          <hr className="my-6 border-border" {...props} />
        ),

        // Links
        a: ({ node, ...props }) => (
          <a
            className="text-primary hover:text-accent underline transition-colors"
            target="_blank"
            rel="noopener noreferrer"
            {...props}
          />
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

/**
 * Metric Card Component with tooltip
 */
function MetricCard({ label, value, delay }: { label: string; value: number; delay: number }) {
  // Get tooltip text based on label
  const getTooltip = (label: string): string => {
    if (label.includes('Objective') || label.includes('objective')) {
      return 'The final value of the function being maximized or minimized';
    }
    if (label.toLowerCase().includes('profit')) {
      return 'Total profit achieved at optimal solution';
    }
    if (label.toLowerCase().includes('cost')) {
      return 'Total cost at optimal solution';
    }
    return 'Optimal value for this variable';
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay }}
      className="glass-card gradient-border rounded-2xl p-4 sm:p-6 group relative overflow-hidden hover:border-primary/30 transition-all"
      title={getTooltip(label)}
    >
      <div className="relative z-10">
        <div className="flex items-center gap-1.5 sm:gap-2 mb-1.5 sm:mb-2">
          <p className="text-xs sm:text-sm text-foreground-dim">{label}</p>
        </div>
        <p className="text-2xl sm:text-3xl md:text-4xl font-bold" style={{ color: '#e76a28' }}>{value.toLocaleString()}</p>
      </div>
    </motion.div>
  );
}

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
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { InlineMath, BlockMath } from 'react-katex';
import 'katex/dist/katex.min.css';

interface OptimizationResult {
  explanation: string;
  technical_details: string;
  objective_value: number;
  key_metrics: Record<string, number>;
  direction: 'maximize' | 'minimize';
}

export default function ResultsPage() {
  const router = useRouter();
  const params = useParams();
  const jobId = params?.jobId as string;

  // State
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [showAIPresentation, setShowAIPresentation] = useState(false);
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);

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
      } catch (err: any) {
        console.error('Fetch results error:', err);
        setError(err.message);
        setIsLoading(false);
      }
    };

    fetchResults();
  }, [jobId]);

  /**
   * Generate HeyGen AI presentation
   */
  const handleGenerateAIPresentation = async () => {
    if (!result) return;

    setIsGeneratingVideo(true);

    try {
      // Create a concise script from the explanation (strip markdown formatting)
      const plainText = result.explanation
        .replace(/\*\*/g, '')  // Remove bold
        .replace(/\n/g, ' ')    // Replace newlines with spaces
        .slice(0, 500);         // Limit to 500 chars

      const script = `Here are your optimization results. ${plainText}`;

      // Call our API route (server-side) to generate video
      const response = await fetch('/api/heygen/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ script }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to generate video');
      }

      // Extract video ID from response (HeyGen API v2 structure)
      const videoId = data.data?.video_id || data.video_id;

      if (videoId) {
        console.log('HeyGen video generation started:', videoId);

        // Poll for video completion (HeyGen videos take time to generate)
        const pollForVideo = async (videoId: string) => {
          const maxAttempts = 60; // Poll for up to 5 minutes (5s intervals)
          let attempts = 0;

          const checkStatus = async (): Promise<boolean> => {
            try {
              const statusResponse = await fetch(`/api/heygen/status?video_id=${videoId}`);
              const statusData = await statusResponse.json();

              if (!statusResponse.ok) {
                throw new Error(statusData.error || 'Failed to check video status');
              }

              // Check for completed video (handle both v1 and v2 response structures)
              const status = statusData.data?.status || statusData.status;
              const videoUrl = statusData.data?.video_url || statusData.video_url;

              if (status === 'completed' && videoUrl) {
                setVideoUrl(videoUrl);
                setShowAIPresentation(true);
                return true;
              } else if (status === 'failed') {
                throw new Error('Video generation failed');
              }

              // Still processing
              attempts++;
              if (attempts < maxAttempts) {
                await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
                return checkStatus();
              } else {
                throw new Error('Video generation timed out');
              }
            } catch (err) {
              throw err;
            }
          };

          return checkStatus();
        };

        await pollForVideo(videoId);
      } else {
        throw new Error('No video ID returned from HeyGen API');
      }
    } catch (err: any) {
      console.error('HeyGen generation error:', err);
      alert(`Failed to generate AI presentation: ${err.message}\n\nPlease check:\n1. HeyGen API key is valid\n2. You have credits in your HeyGen account\n3. Check console for more details`);
    } finally {
      setIsGeneratingVideo(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4">📊</div>
          <p className="text-foreground-dim">Loading results...</p>
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <div className="max-w-md w-full bg-surface border border-error rounded-lg p-8 text-center">
          <div className="text-5xl mb-4">❌</div>
          <h2 className="text-2xl font-bold text-error mb-4">Failed to Load Results</h2>
          <p className="text-foreground-dim mb-6">{error || 'Unknown error'}</p>
          <button
            onClick={() => router.push('/refine')}
            className="px-6 py-2 bg-primary text-background font-semibold rounded-lg hover:bg-opacity-90 transition-all"
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
    <div className="min-h-screen p-8">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center"
        >
          <div className="text-6xl mb-4">✨</div>
          <h1 className="text-4xl font-bold text-foreground mb-2">Optimization Complete</h1>
          <p className="text-foreground-dim">
            Your optimal solution has been found and verified.
          </p>
        </motion.div>

        {/* Metric Cards */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
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
            className="bg-surface border border-border rounded-lg p-6"
          >
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-foreground mb-2">Decision Variables</h2>
              <p className="text-sm text-foreground-dim">
                Optimal values for each decision variable in your problem
              </p>
            </div>
            <ResponsiveContainer width="100%" height={300}>
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

        {/* Explanation */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-surface border border-border rounded-lg p-8"
        >
          <h2 className="text-2xl font-semibold text-foreground mb-6">Executive Summary</h2>
          <div className="prose prose-invert max-w-none">
            <ReactMarkdown
              components={{
                p: ({ node, ...props }) => <p className="text-foreground-dim mb-4" {...props} />,
                strong: ({ node, ...props }) => <strong className="text-foreground font-semibold" {...props} />,
                ul: ({ node, ...props }) => <ul className="list-disc list-inside text-foreground-dim space-y-2" {...props} />,
                ol: ({ node, ...props }) => <ol className="list-decimal list-inside text-foreground-dim space-y-2" {...props} />,
              }}
            >
              {result.explanation}
            </ReactMarkdown>
          </div>
        </motion.div>

        {/* Technical Details (Collapsible) */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-surface border border-border rounded-lg"
        >
          <button
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            className="w-full p-6 flex items-center justify-between hover:bg-code-bg transition-all"
          >
            <h2 className="text-xl font-semibold text-foreground">Technical Details</h2>
            <span className="text-2xl text-primary">
              {showTechnicalDetails ? '▼' : '▶'}
            </span>
          </button>

          {showTechnicalDetails && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="border-t border-border p-6 space-y-6"
            >
              <TechnicalDetailsContent content={result.technical_details} />
            </motion.div>
          )}
        </motion.div>

        {/* AI Presentation Section */}
        {showAIPresentation && videoUrl && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="bg-surface border border-border rounded-lg p-8"
          >
            <h2 className="text-2xl font-semibold text-foreground mb-6 text-center">
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
          className="flex justify-center space-x-4 flex-wrap gap-4"
        >
          <button
            onClick={() => router.push('/refine')}
            className="px-6 py-3 bg-primary text-background font-semibold rounded-lg hover:bg-opacity-90 transition-all"
          >
            Solve Another Problem
          </button>

          {!showAIPresentation && (
            <button
              onClick={handleGenerateAIPresentation}
              disabled={isGeneratingVideo}
              className="px-6 py-3 bg-accent text-background font-semibold rounded-lg hover:bg-opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isGeneratingVideo ? (
                <>
                  <span className="inline-block animate-spin mr-2">⚙️</span>
                  Generating AI Presenter...
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
      className="bg-surface border border-border rounded-lg p-6 hover:border-primary transition-all group relative"
      title={getTooltip(label)}
    >
      <div className="flex items-center gap-2 mb-2">
        <p className="text-sm text-foreground-dim">{label}</p>
        <span className="text-xs text-foreground-dim opacity-0 group-hover:opacity-100 transition-opacity">
          ℹ️
        </span>
      </div>
      <p className="text-3xl font-bold text-primary">{value.toLocaleString()}</p>
    </motion.div>
  );
}

/**
 * Technical Details Content Parser
 * Extracts LaTeX math and code from technical_details
 */
function TechnicalDetailsContent({ content }: { content: string }) {
  // Split content into sections
  const sections = content.split('\n\n');

  return (
    <div className="space-y-6">
      {sections.map((section, index) => {
        // Check if section contains LaTeX math (multiple formats)
        // Format 1: \[ ... \] (proper LaTeX)
        const blockMathMatch = section.match(/\\\[([\s\S]*?)\\\]/);
        // Format 2: $$ ... $$ (display math)
        const displayMathMatch = section.match(/\$\$([\s\S]*?)\$\$/);
        // Format 3: [ ... ] (backend format - single brackets)
        const singleBracketMatch = section.match(/\[\s*\\?([a-z]+[^[]*?)\s*\]/i);

        if (blockMathMatch || displayMathMatch || singleBracketMatch) {
          const math = (blockMathMatch || displayMathMatch || singleBracketMatch)?.[1] || '';
          return (
            <div key={index} className="bg-code-bg p-4 rounded-lg overflow-x-auto border border-border">
              <BlockMath math={math.trim()} />
            </div>
          );
        }

        // Check if section contains code (wrapped in ```)
        const codeMatch = section.match(/```(\w+)?\n([\s\S]*?)```/);
        if (codeMatch) {
          const [, language = 'python', code] = codeMatch;
          return (
            <div key={index} className="rounded-lg overflow-hidden">
              <SyntaxHighlighter
                language={language}
                style={vscDarkPlus}
                customStyle={{
                  margin: 0,
                  borderRadius: '8px',
                  fontSize: '14px',
                  maxWidth: '100%',
                  overflowX: 'auto',
                }}
                wrapLongLines={false}
              >
                {code.trim()}
              </SyntaxHighlighter>
            </div>
          );
        }

        // Regular text with possible inline math
        const hasInlineMath = section.includes('$') || section.includes('\\(');

        if (hasInlineMath) {
          // Parse inline math
          const parts = section.split(/(\$[^$]+\$|\\\([^)]+\\\))/g);
          return (
            <p key={index} className="text-foreground-dim">
              {parts.map((part, i) => {
                const inlineMathMatch = part.match(/\$([^$]+)\$|\\\(([^)]+)\\\)/);
                if (inlineMathMatch) {
                  const math = inlineMathMatch[1] || inlineMathMatch[2];
                  return <InlineMath key={i} math={math} />;
                }
                return <span key={i}>{part}</span>;
              })}
            </p>
          );
        }

        // Regular text or markdown headers
        if (section.startsWith('**')) {
          const text = section.replace(/\*\*/g, '');
          return (
            <h3 key={index} className="text-lg font-semibold text-foreground mt-4">
              {text}
            </h3>
          );
        }

        // Plain text sections (like Solver Output) - wrap in styled container
        if (section.trim().length > 0) {
          // Check if this looks like output/data (contains numbers, equals signs, etc.)
          const looksLikeOutput = /[:=\d]/.test(section);

          if (looksLikeOutput) {
            return (
              <div key={index} className="bg-code-bg/70 p-4 rounded-lg border border-border">
                <pre className="text-foreground-dim whitespace-pre-wrap font-mono text-sm">
                  {section}
                </pre>
              </div>
            );
          }

          // Regular text paragraph
          return (
            <p key={index} className="text-foreground-dim">
              {section}
            </p>
          );
        }

        return null;
      })}
    </div>
  );
}

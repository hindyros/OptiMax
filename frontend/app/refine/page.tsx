/**
 * Refinement Page (/refine)
 *
 * Conversational LLM refinement interface.
 *
 * Flow:
 * 1. User enters initial problem description
 * 2. LLM asks clarifying questions (up to 5 iterations)
 * 3. When ready (confidence >= 90% internally), automatically proceeds to optimization
 *
 * CRITICAL: User NEVER sees confidence scores!
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function RefinePage() {
  const router = useRouter();

  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [hasStarted, setHasStarted] = useState(false);
  const [needsData, setNeedsData] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  // Scroll to top on mount
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  /**
   * Start conversation with initial description
   */
  const handleStart = async () => {
    if (!inputValue.trim()) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setIsLoading(true);
    setHasStarted(true);

    // Add user message to UI
    setMessages([{ role: 'user', content: userMessage }]);

    try {
      const response = await fetch('/api/refine/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initial_description: userMessage }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to start refinement');
      }

      setConversationId(data.conversation_id);

      // Track if data is needed
      setNeedsData(data.needs_data || false);

      // Check if ready immediately (high confidence on first try)
      if (data.ready_for_optimization) {
        handleReadyForOptimization(data.conversation_id, data.refined_description || userMessage);
        return;
      }

      // Add LLM's question to messages
      if (data.question) {
        setMessages((prev) => [...prev, { role: 'assistant', content: data.question }]);
      }

      setIsLoading(false);
    } catch (error: any) {
      console.error('Start refinement error:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Sorry, something went wrong: ${error.message}. Please try again.`,
        },
      ]);
      setIsLoading(false);
    }
  };

  /**
   * Continue conversation with user's response
   */
  const handleContinue = async () => {
    if (!inputValue.trim() || !conversationId) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setIsLoading(true);

    // Add user message to UI
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);

    try {
      const response = await fetch('/api/refine/continue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: conversationId,
          user_response: userMessage,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to continue refinement');
      }

      // Track if data is needed
      setNeedsData(data.needs_data || false);

      // Check if ready for optimization
      if (data.ready_for_optimization) {
        // Show final transition message
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: "Perfect! I have all the information I need. Let's solve this problem for you.",
          },
        ]);

        // Wait a moment for user to read, then proceed
        setTimeout(() => {
          handleReadyForOptimization(conversationId, data.refined_description || '');
        }, 1500);

        return;
      }

      // Add LLM's next question
      if (data.question) {
        setMessages((prev) => [...prev, { role: 'assistant', content: data.question }]);
      }

      setIsLoading(false);
    } catch (error: any) {
      console.error('Continue refinement error:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Sorry, something went wrong: ${error.message}. Please try again.`,
        },
      ]);
      setIsLoading(false);
    }
  };

  /**
   * Handle ready for optimization - start the optimization process
   */
  const handleReadyForOptimization = async (convId: string, refinedDescription: string) => {
    setIsLoading(true);

    try {
      const response = await fetch('/api/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: convId,
          refined_description: refinedDescription,
          params: null, // Let LLM extract params
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to start optimization');
      }

      // Redirect to processing page
      router.push(`/optimize/${data.job_id}`);
    } catch (error: any) {
      console.error('Start optimization error:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Sorry, failed to start optimization: ${error.message}`,
        },
      ]);
      setIsLoading(false);
    }
  };

  /**
   * Handle key press (Enter to submit)
   */
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (hasStarted) {
        handleContinue();
      } else {
        handleStart();
      }
    }
  };

  /**
   * Handle file selection
   */
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setUploadedFile(e.target.files[0]);
    }
  };

  /**
   * Handle file upload and parsing
   */
  const handleFileUpload = async () => {
    if (!uploadedFile || !conversationId) return;

    setIsLoading(true);

    try {
      // Read file contents
      const fileText = await uploadedFile.text();

      // Parse based on file type
      let parsedData: Record<string, any> = {};

      if (uploadedFile.name.endsWith('.json')) {
        // Parse JSON directly
        parsedData = JSON.parse(fileText);
      } else if (uploadedFile.name.endsWith('.csv')) {
        // Parse CSV to JSON format
        const lines = fileText.trim().split('\n');

        for (const line of lines) {
          const [key, value] = line.split(',').map(s => s.trim());
          if (key && value && key !== 'parameter') {
            const numValue = parseFloat(value);
            parsedData[key] = {
              shape: [],
              definition: `Parameter: ${key}`,
              type: Number.isInteger(numValue) ? 'int' : 'float',
              value: isNaN(numValue) ? value : numValue,
            };
          }
        }
      }

      // Send to backend
      const response = await fetch('/api/refine/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: conversationId,
          params: parsedData,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to upload file');
      }

      // Add success message and proceed
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Perfect! I\'ve received your data. Let\'s solve this problem for you.',
        },
      ]);

      // Wait a moment, then proceed to optimization
      setTimeout(() => {
        handleReadyForOptimization(conversationId, data.refined_description || '');
      }, 1500);
    } catch (error: any) {
      console.error('File upload error:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Sorry, I couldn't process that file: ${error.message}. Please check the format and try again.`,
        },
      ]);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col p-8">
      {/* Header */}
      <div className="max-w-3xl mx-auto w-full mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">Describe Your Problem</h1>
        <p className="text-foreground-dim">
          Tell me about your optimization problem in plain English. I'll ask clarifying questions to ensure accuracy.
        </p>
      </div>

      {/* Chat Container */}
      <div className="flex-1 max-w-3xl mx-auto w-full flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-4 mb-6">
          <AnimatePresence initial={false}>
            {messages.map((message, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] p-4 rounded-lg ${
                    message.role === 'user'
                      ? 'bg-primary text-background'
                      : 'bg-surface text-foreground border border-border'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Loading indicator */}
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="bg-surface text-foreground border border-border p-4 rounded-lg">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </motion.div>
          )}
        </div>

        {/* Input Area */}
        <div className="bg-surface border border-border rounded-lg p-4">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder={
              hasStarted
                ? 'Type your response...'
                : 'e.g., "A factory produces two products A and B. Product A yields $5 profit per unit..."'
            }
            className="w-full bg-transparent text-foreground placeholder-foreground-dim outline-none resize-none"
            rows={3}
            disabled={isLoading}
          />

          {/* File Upload Section (only when data is needed) */}
          {needsData && hasStarted && (
            <div className="mt-4 pt-4 border-t border-border">
              <p className="text-sm text-foreground-dim mb-3">
                Or upload a data file (CSV or JSON):
              </p>
              <div className="flex items-center gap-3">
                <label
                  htmlFor="file-upload"
                  className="px-4 py-2 bg-surface border border-border text-foreground rounded-lg cursor-pointer hover:border-primary transition-all duration-200"
                >
                  {uploadedFile ? uploadedFile.name : 'Choose File'}
                </label>
                <input
                  id="file-upload"
                  type="file"
                  accept=".csv,.json"
                  onChange={handleFileChange}
                  className="hidden"
                  disabled={isLoading}
                />
                {uploadedFile && (
                  <button
                    onClick={handleFileUpload}
                    disabled={isLoading}
                    className="px-4 py-2 bg-accent text-background font-semibold rounded-lg hover:bg-opacity-90 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Upload Data
                  </button>
                )}
              </div>
            </div>
          )}

          <div className="flex justify-between items-center mt-4">
            <p className="text-sm text-foreground-dim">
              Press Enter to send • Shift+Enter for new line
            </p>
            <button
              onClick={hasStarted ? handleContinue : handleStart}
              disabled={!inputValue.trim() || isLoading}
              className="px-6 py-2 bg-primary text-background font-semibold rounded-lg hover:bg-opacity-90 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {hasStarted ? 'Send' : 'Start'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Landing Page (/)
 *
 * Hero section with introduction and "Start Optimizing" button
 *
 * What judges will see first - make it clean and professional!
 */

'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';

export default function LandingPage() {
  // Scroll to top on mount
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      {/* Hero Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="max-w-4xl mx-auto text-center space-y-8"
      >
        {/* Logo/Title */}
        <div className="space-y-4">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-6xl font-bold text-foreground"
          >
            Optima
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-xl text-foreground-dim"
          >
            AI-Powered Mathematical Optimization
          </motion.p>
        </div>

        {/* Description */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="text-lg text-foreground-dim max-w-2xl mx-auto leading-relaxed"
        >
          Describe your optimization problem in plain English. Our AI refines your
          description, formulates the mathematical model, generates solver code, and
          returns optimal solutions with detailed explanations.
        </motion.p>

        {/* Features */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12"
        >
          <FeatureCard
            title="Natural Language"
            description="No math required. Just describe your problem conversationally."
            icon="💬"
          />
          <FeatureCard
            title="AI-Guided Refinement"
            description="Our LLM asks clarifying questions to ensure accuracy."
            icon="🤖"
          />
          <FeatureCard
            title="Professional Results"
            description="Get LaTeX formulations, solver code, and clear explanations."
            icon="📊"
          />
        </motion.div>

        {/* CTA Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="mt-12"
        >
          <Link href="/refine">
            <button className="px-8 py-4 bg-primary text-background font-semibold text-lg rounded-lg hover:bg-opacity-90 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105">
              Start Optimizing →
            </button>
          </Link>
        </motion.div>

        {/* Example Use Cases */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.6 }}
          className="mt-16 pt-8 border-t border-border"
        >
          <p className="text-sm text-foreground-dim mb-4">Example Use Cases:</p>
          <div className="flex flex-wrap justify-center gap-3">
            {[
              'Factory Production Planning',
              'Hospital Resource Allocation',
              'Supply Chain Optimization',
              'Portfolio Management',
              'Workforce Scheduling',
            ].map((useCase, index) => (
              <span
                key={index}
                className="px-4 py-2 bg-surface text-foreground-dim text-sm rounded-full border border-border"
              >
                {useCase}
              </span>
            ))}
          </div>
        </motion.div>
      </motion.div>

      {/* Footer */}
      <motion.footer
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.7 }}
        className="mt-16 text-center text-sm text-foreground-dim"
      >
        <p>Powered by OptiMUS • Built with GPT-4 & Gurobi</p>
      </motion.footer>
    </div>
  );
}

/**
 * Feature Card Component
 */
function FeatureCard({ title, description, icon }: { title: string; description: string; icon: string }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-6 hover:border-primary transition-all duration-200">
      <div className="text-4xl mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-foreground mb-2">{title}</h3>
      <p className="text-sm text-foreground-dim">{description}</p>
    </div>
  );
}

/**
 * Landing Page (/)
 *
 * Sophisticated hero section with advanced animations and effects
 */

'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';

export default function LandingPage() {
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8 relative overflow-hidden bg-app-gradient">

      {/* Hero Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="max-w-5xl mx-auto text-center space-y-12 relative z-10"
      >
        {/* Logo/Title with glow effect */}
        <div className="space-y-6">
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="inline-block"
          >
            <h1 className="text-8xl font-bold">
              <span className="text-foreground">Opti</span>
              <span className="text-primary italic">MATE</span>
            </h1>
          </motion.div>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="text-2xl text-foreground-dim font-light tracking-wide"
          >
            AI-Powered Mathematical Optimization
          </motion.p>

          <motion.div
            initial={{ width: 0 }}
            animate={{ width: '200px' }}
            transition={{ duration: 1, delay: 0.5 }}
            className="h-1 mx-auto bg-gradient-to-r from-transparent via-primary to-transparent"
          />
        </div>

        {/* Description with glassmorphism */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6 }}
          className="glass-card p-12 rounded-2xl max-w-5xl mx-auto"
        >
          <p className="text-lg text-foreground leading-relaxed">
            Transform natural language into optimal solutions. Describe your problem, and watch as our AI
            agents formulate mathematical models, generate solver code, and deliver
            <span className="text-primary font-semibold"> proven optimal results</span>.
          </p>
        </motion.div>

        {/* Features Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.7 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16"
        >
          <FeatureCard
            title="Natural Language"
            description="No math expertise required. Describe your optimization problem in plain English."
            icon="💬"
            delay={0.8}
          />
          <FeatureCard
            title="Dual-Solver Intelligence"
            description="Two AI agents compete to find the best solution, validated by an autonomous judge."
            icon="🤖"
            delay={0.9}
          />
          <FeatureCard
            title="Production-Ready Code"
            description="Get complete formulations, solver code, and detailed reports ready to deploy."
            icon="📊"
            delay={1.0}
          />
        </motion.div>

        {/* CTA Button with gradient */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, delay: 1.1 }}
          className="mt-16"
        >
          <Link href="/refine">
            <button className="btn-gradient px-12 py-5 text-background font-bold text-xl rounded-2xl shadow-2xl relative overflow-hidden group">
              <span className="relative z-10 flex items-center justify-center gap-3">
                <span>Start Optimizing</span>
                <span className="group-hover:translate-x-1 transition-transform">→</span>
              </span>
            </button>
          </Link>
        </motion.div>

        {/* Use Cases */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 1.2 }}
          className="mt-20 pt-12"
        >
          <p className="text-sm text-foreground-dim mb-6 uppercase tracking-wider">Trusted For</p>
          <div className="flex flex-wrap justify-center gap-4">
            {[
              { icon: '🏭', text: 'Production Planning' },
              { icon: '🏥', text: 'Resource Allocation' },
              { icon: '🚚', text: 'Supply Chain' },
              { icon: '💼', text: 'Portfolio Management' },
              { icon: '📅', text: 'Scheduling' },
            ].map((useCase, index) => (
              <motion.span
                key={index}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, delay: 1.3 + index * 0.1 }}
                className="px-5 py-3 glass-card rounded-xl text-foreground text-sm font-medium flex items-center gap-2 cursor-default"
              >
                <span className="text-xl">{useCase.icon}</span>
                {useCase.text}
              </motion.span>
            ))}
          </div>
        </motion.div>
      </motion.div>

      {/* Footer */}
      <motion.footer
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8, delay: 1.5 }}
        className="mt-20 text-center text-sm text-foreground-dim relative z-10"
      >
        <p className="flex items-center justify-center gap-2">
          <span>Powered by</span>
          <span className="text-primary font-semibold">OptiMUS & OptiMind</span>
          <span>•</span>
          <span>Built with GPT-4 & Gurobi</span>
        </p>
      </motion.footer>
    </div>
  );
}

/**
 * Feature Card with sophisticated hover effects
 */
function FeatureCard({
  title,
  description,
  icon,
  delay,
}: {
  title: string;
  description: string;
  icon: string;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay }}
      className="glass-card gradient-border rounded-2xl p-8 group relative overflow-hidden hover:border-primary/30 transition-all"
    >
      <div className="relative z-10">
        <div className="text-5xl mb-5">
          {icon}
        </div>
        <h3 className="text-xl font-bold mb-3" style={{ color: '#e76a28' }}>{title}</h3>
        <p className="text-sm text-foreground-dim leading-relaxed">{description}</p>
      </div>
    </motion.div>
  );
}

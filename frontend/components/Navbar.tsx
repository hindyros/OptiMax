'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ThemeToggle } from './ThemeToggle';

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 bg-background/95 border-b border-border backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo/Brand */}
          <Link
            href="/"
            className="flex items-center space-x-2 group"
          >
            <span className="text-xl font-bold group-hover:scale-105 transition-transform">
              <span className="text-foreground">Opti</span>
              <span className="text-primary italic">MATE</span>
            </span>
          </Link>

          {/* Navigation Items */}
          <div className="flex items-center space-x-4">
            {/* Theme Toggle */}
            <ThemeToggle />

            {/* Show "New Problem" button when not on landing or refine page */}
            {pathname !== '/' && pathname !== '/refine' && (
              <Link
                href="/refine"
                className="px-4 py-2 bg-primary/90 hover:bg-primary text-background font-semibold rounded-lg transition-all"
              >
                New Problem
              </Link>
            )}

            {/* Show "Get Started" on landing page */}
            {pathname === '/' && (
              <Link
                href="/refine"
                className="px-4 py-2 bg-primary/90 hover:bg-primary text-background font-semibold rounded-lg transition-all"
              >
                Get Started
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

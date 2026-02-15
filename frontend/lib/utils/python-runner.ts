/**
 * Python Process Runner
 *
 * Utilities for spawning and managing Python processes from Next.js API routes.
 * This allows us to run optimus.py and judge.py from the frontend.
 */

import { exec } from 'child_process';
import path from 'path';
import { promisify } from 'util';

const execAsync = promisify(exec);

/**
 * Get the absolute path to the backend directory
 */
export function getBackendPath(): string {
  // From frontend/ to backend/
  const backendPath = path.join(process.cwd(), '..', 'backend');
  return backendPath;
}

/**
 * Clear previous optimization files
 *
 * Runs: python optimus.py --clear
 * This archives old results and wipes current_query/ for a fresh start
 */
export async function clearPreviousOptimization(): Promise<void> {
  const backendPath = getBackendPath();

  console.log('[Python] Clearing previous optimization files...');

  try {
    const { stdout, stderr } = await execAsync('python optimus.py --clear', {
      cwd: backendPath,
      timeout: 30000,  // 30 second timeout
    });

    if (stdout) console.log('[Python] Clear stdout:', stdout);
    if (stderr) console.warn('[Python] Clear stderr:', stderr);

    console.log('[Python] ✓ Cleared successfully');
  } catch (error: any) {
    console.error('[Python] Failed to clear:', error.message);
    throw new Error(`Failed to clear previous optimization: ${error.message}`);
  }
}

/**
 * Run the OptiMUS optimization pipeline
 *
 * Runs: python optimus.py
 * This processes desc.txt and params.json, generates code, and executes it
 *
 * Note: This is a LONG-RUNNING process (5-10 minutes)
 */
export async function runOptiMUS(): Promise<void> {
  const backendPath = getBackendPath();

  console.log('[Python] Starting OptiMUS pipeline...');

  try {
    const { stdout, stderr } = await execAsync('python optimus.py', {
      cwd: backendPath,
      timeout: 600000,  // 10 minute timeout (OptiMUS can take 5-7 minutes)
    });

    if (stdout) console.log('[Python] OptiMUS stdout:', stdout);
    if (stderr) console.warn('[Python] OptiMUS stderr:', stderr);

    console.log('[Python] ✓ OptiMUS completed');
  } catch (error: any) {
    console.error('[Python] OptiMUS failed:', error.message);
    throw new Error(`OptiMUS pipeline failed: ${error.message}`);
  }
}

/**
 * Run the judge to compare solutions
 *
 * Runs: python judge.py
 * This evaluates OptiMUS/OptiMind outputs and generates verdict.json
 */
export async function runJudge(): Promise<void> {
  const backendPath = getBackendPath();

  console.log('[Python] Running judge...');

  try {
    const { stdout, stderr } = await execAsync('python judge.py', {
      cwd: backendPath,
      timeout: 60000,  // 1 minute timeout
    });

    if (stdout) console.log('[Python] Judge stdout:', stdout);
    if (stderr) console.warn('[Python] Judge stderr:', stderr);

    console.log('[Python] ✓ Judge completed');
  } catch (error: any) {
    console.error('[Python] Judge failed:', error.message);
    throw new Error(`Judge failed: ${error.message}`);
  }
}

/**
 * Execute a custom Python command in the backend directory
 * (Used for debugging/testing)
 */
export async function runPythonCommand(command: string): Promise<string> {
  const backendPath = getBackendPath();

  console.log(`[Python] Running custom command: ${command}`);

  try {
    const { stdout, stderr } = await execAsync(command, {
      cwd: backendPath,
      timeout: 60000,
    });

    if (stderr) console.warn('[Python] stderr:', stderr);

    return stdout;
  } catch (error: any) {
    console.error('[Python] Command failed:', error.message);
    throw new Error(`Python command failed: ${error.message}`);
  }
}

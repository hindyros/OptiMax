/**
 * File Operations
 *
 * Utilities for reading/writing files in the backend directory.
 * These handle communication between Next.js and the Python backend via files.
 */

import { promises as fs } from 'fs';
import path from 'path';
import { VerDict, ParamsJSON, OptimizationStage } from '../types';
import { getBackendPath } from './python-runner';

/**
 * Write the problem description to desc.txt
 *
 * This is the input for OptiMUS pipeline
 */
export async function writeDescriptionFile(description: string): Promise<void> {
  const descPath = path.join(getBackendPath(), 'current_query', 'desc.txt');

  console.log('[FileOps] Writing desc.txt...');

  try {
    await fs.writeFile(descPath, description, 'utf-8');
    console.log('[FileOps] ✓ desc.txt written');
  } catch (error: any) {
    console.error('[FileOps] Failed to write desc.txt:', error.message);
    throw new Error(`Failed to write description file: ${error.message}`);
  }
}

/**
 * Write parameters to params.json
 *
 * If params is null, OptiMUS will extract them from the description
 */
export async function writeParamsFile(params: ParamsJSON | null): Promise<void> {
  const paramsPath = path.join(getBackendPath(), 'current_query', 'params.json');

  console.log('[FileOps] Writing params.json...');

  try {
    if (params === null) {
      // Write empty object - OptiMUS will extract params from desc.txt
      await fs.writeFile(paramsPath, JSON.stringify({}, null, 2), 'utf-8');
      console.log('[FileOps] ✓ params.json written (empty - will be extracted)');
    } else {
      await fs.writeFile(paramsPath, JSON.stringify(params, null, 2), 'utf-8');
      console.log('[FileOps] ✓ params.json written with user-provided data');
    }
  } catch (error: any) {
    console.error('[FileOps] Failed to write params.json:', error.message);
    throw new Error(`Failed to write params file: ${error.message}`);
  }
}

/**
 * Read the final verdict.json from backend
 *
 * This contains the optimization results and explanations
 */
export async function readVerdictFile(): Promise<VerDict> {
  const verdictPath = path.join(
    getBackendPath(),
    'current_query',
    'final_output',
    'verdict.json'
  );

  console.log('[FileOps] Reading verdict.json...');

  try {
    const verdictData = await fs.readFile(verdictPath, 'utf-8');
    const verdict: VerDict = JSON.parse(verdictData);

    console.log('[FileOps] ✓ verdict.json read successfully');

    return verdict;
  } catch (error: any) {
    console.error('[FileOps] Failed to read verdict.json:', error.message);
    throw new Error(`Failed to read verdict file: ${error.message}`);
  }
}

/**
 * Check which optimization stage files exist
 *
 * This lets us track progress by polling for state_*.json files
 */
export async function getCurrentOptimizationStage(): Promise<{
  stage: OptimizationStage;
  progress: number;
}> {
  const optimusOutputPath = path.join(
    getBackendPath(),
    'current_query',
    'optimus_output'
  );

  // Define stage files and their progress percentages
  const stageFiles: Record<string, { stage: OptimizationStage; progress: number }> = {
    'state_1_params.json': { stage: 'state_1_params', progress: 14 },
    'state_2_objective.json': { stage: 'state_2_objective', progress: 28 },
    'state_3_constraints.json': { stage: 'state_3_constraints', progress: 42 },
    'state_4_constraints_modeled.json': { stage: 'state_4_constraints_modeled', progress: 57 },
    'state_5_objective_modeled.json': { stage: 'state_5_objective_modeled', progress: 71 },
    'state_6_code.json': { stage: 'state_6_code', progress: 85 },
    'code_output.txt': { stage: 'executing', progress: 95 },
  };

  // Check files in reverse order to find the latest completed stage
  const fileNames = Object.keys(stageFiles).reverse();

  for (const fileName of fileNames) {
    const filePath = path.join(optimusOutputPath, fileName);

    try {
      await fs.access(filePath);  // Check if file exists
      // File exists - this is the current stage
      return stageFiles[fileName];
    } catch {
      // File doesn't exist yet, keep checking earlier stages
      continue;
    }
  }

  // No stage files exist yet - optimization hasn't started
  return { stage: 'state_1_params', progress: 0 };
}

/**
 * Check if verdict.json exists (optimization is complete)
 */
export async function isOptimizationComplete(): Promise<boolean> {
  const verdictPath = path.join(
    getBackendPath(),
    'current_query',
    'final_output',
    'verdict.json'
  );

  try {
    await fs.access(verdictPath);
    return true;
  } catch {
    return false;
  }
}

/**
 * Wait for a file to exist (used for monitoring progress)
 *
 * Polls every 500ms until file exists or timeout
 */
export async function waitForFile(
  relativePath: string,
  timeoutMs: number = 180000  // 3 minutes default
): Promise<void> {
  const fullPath = path.join(getBackendPath(), relativePath);
  const startTime = Date.now();

  while (Date.now() - startTime < timeoutMs) {
    try {
      await fs.access(fullPath);
      return;  // File exists!
    } catch {
      // File doesn't exist yet, wait and retry
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }

  throw new Error(`Timeout waiting for file: ${relativePath}`);
}

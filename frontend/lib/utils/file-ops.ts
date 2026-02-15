/**
 * File Operations
 *
 * Utilities for reading/writing files in the backend directory.
 * These handle communication between Next.js and the Python backend via files.
 *
 * NEW STRUCTURE:
 * - desc.txt goes to data_upload/ (contains problem + baseline)
 * - Multiple CSV files go to data_upload/
 * - Backend runs main.py to process everything
 */

import { promises as fs } from 'fs';
import path from 'path';
import { VerDict,  ParamsJSON, OptimizationStage } from '../types';
import { getBackendPath } from './python-runner';

/**
 * Write the problem description + baseline to desc.txt in data_upload/
 *
 * This file contains the full problem description and baseline assessment
 */
export async function writeDescriptionToDataUpload(description: string): Promise<void> {
  const descPath = path.join(getBackendPath(), 'data_upload', 'desc.txt');

  console.log('[FileOps] Writing desc.txt to data_upload/...');

  try {
    // Ensure data_upload directory exists
    const dataUploadDir = path.join(getBackendPath(), 'data_upload');
    await fs.mkdir(dataUploadDir, { recursive: true });

    await fs.writeFile(descPath, description, 'utf-8');
    console.log('[FileOps] ✓ desc.txt written to data_upload/');
  } catch (error: any) {
    console.error('[FileOps] Failed to write desc.txt:', error.message);
    throw new Error(`Failed to write description file: ${error.message}`);
  }
}

/**
 * Write CSV files to data_upload/
 *
 * Handles multiple CSV file uploads
 */
export async function writeCsvFilesToDataUpload(files: { name: string; content: Buffer }[]): Promise<void> {
  const dataUploadDir = path.join(getBackendPath(), 'data_upload');

  console.log(`[FileOps] Writing ${files.length} CSV file(s) to data_upload/...`);

  try {
    // Ensure data_upload directory exists
    await fs.mkdir(dataUploadDir, { recursive: true });

    // Write each CSV file
    for (const file of files) {
      const filePath = path.join(dataUploadDir, file.name);
      await fs.writeFile(filePath, file.content);
      console.log(`[FileOps] ✓ ${file.name} written to data_upload/`);
    }
  } catch (error: any) {
    console.error('[FileOps] Failed to write CSV files:', error.message);
    throw new Error(`Failed to write CSV files: ${error.message}`);
  }
}

/**
 * Clear data_upload directory before new job
 */
export async function clearDataUpload(): Promise<void> {
  const dataUploadDir = path.join(getBackendPath(), 'data_upload');

  console.log('[FileOps] Clearing data_upload directory...');

  try {
    // Read all files in data_upload
    const files = await fs.readdir(dataUploadDir);

    // Delete each file
    for (const file of files) {
      const filePath = path.join(dataUploadDir, file);
      await fs.unlink(filePath);
    }

    console.log('[FileOps] ✓ data_upload cleared');
  } catch (error: any) {
    if (error.code === 'ENOENT') {
      // Directory doesn't exist, create it
      await fs.mkdir(dataUploadDir, { recursive: true });
      console.log('[FileOps] ✓ data_upload directory created');
    } else {
      console.error('[FileOps] Failed to clear data_upload:', error.message);
      throw new Error(`Failed to clear data_upload: ${error.message}`);
    }
  }
}

/**
 * Clear current_query directory before new job
 * This fixes the issue where progress gets stuck at 15% on subsequent runs
 */
export async function clearCurrentQuery(): Promise<void> {
  const currentQueryDir = path.join(getBackendPath(), 'current_query');

  console.log('[FileOps] Clearing current_query directory...');

  try {
    // Recursively delete the entire current_query directory
    await fs.rm(currentQueryDir, { recursive: true, force: true });
    console.log('[FileOps] ✓ current_query cleared');
  } catch (error: any) {
    // If it doesn't exist, that's fine
    if (error.code !== 'ENOENT') {
      console.error('[FileOps] Failed to clear current_query:', error.message);
      throw new Error(`Failed to clear current_query: ${error.message}`);
    }
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
 * Check which optimization stage the pipeline is currently in
 *
 * NEW PIPELINE STAGES (Unified Optima branding):
 * 1. preprocessing - Converting raw inputs to structured format
 * 2. analyzing - Analyzing parameters and constraints
 * 3. solving - Running optimization algorithms
 * 4. finalizing - Generating final report with baseline comparison
 * 5. complete - Ready to view results
 */
export async function getCurrentOptimizationStage(): Promise<{
  stage: string;
  progress: number;
  message: string;
}> {
  const backendPath = getBackendPath();

  // Check stages in order (unified Optima branding - don't show individual solvers)
  const stages = [
    {
      file: 'current_query/model_input/desc.txt',
      stage: 'preprocessing',
      progress: 15,
      message: 'Preprocessing your data and problem description...',
    },
    {
      file: 'current_query/optimus_output/state_1_params.json',
      stage: 'analyzing',
      progress: 35,
      message: 'Optima is analyzing parameters and constraints...',
    },
    {
      file: 'current_query/optimus_output/state_6_code.json',
      stage: 'solving',
      progress: 60,
      message: 'Optima is solving your optimization problem...',
    },
    {
      file: 'current_query/final_output/verdict.json',
      stage: 'finalizing',
      progress: 85,
      message: 'Generating executive report and baseline comparison...',
    },
    {
      file: 'current_query/final_output/report.md',
      stage: 'complete',
      progress: 100,
      message: 'Optimization complete! Your results are ready.',
    },
  ];

  // Check stages in reverse order to find the latest completed stage
  for (let i = stages.length - 1; i >= 0; i--) {
    const stageInfo = stages[i];
    const filePath = path.join(backendPath, stageInfo.file);

    try {
      await fs.access(filePath);
      // File exists - this stage is complete/running
      return {
        stage: stageInfo.stage,
        progress: stageInfo.progress,
        message: stageInfo.message,
      };
    } catch {
      // File doesn't exist yet, check previous stages
      continue;
    }
  }

  // No stage files exist yet - just started
  return {
    stage: 'initializing',
    progress: 5,
    message: 'Initializing optimization pipeline...',
  };
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
 * Read the professional report.md from backend NEW
 *
 * This contains the full consultant-generated report with baseline comparison
 */
export async function readReportFile(): Promise<string> {
  const reportPath = path.join(
    getBackendPath(),
    'current_query',
    'final_output',
    'report.md'
  );

  console.log('[FileOps] Reading report.md...');

  try {
    const reportData = await fs.readFile(reportPath, 'utf-8');

    console.log('[FileOps] ✓ report.md read successfully');

    return reportData;
  } catch (error: any) {
    console.error('[FileOps] Failed to read report.md:', error.message);
    throw new Error(`Failed to read report file: ${error.message}`);
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

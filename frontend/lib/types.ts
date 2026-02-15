/**
 * TypeScript Types for OptiMax Frontend
 *
 * These types define the shape of data flowing through our application,
 * from user input → LLM refinement → optimization → results display
 */

// ===== LLM Refinement Types =====

/**
 * Represents a single message in the LLM refinement conversation
 */
export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

/**
 * Response from /api/refine/start - initiates LLM conversation
 */
export interface RefinementStartResponse {
  conversation_id: string;
  question: string | null;  // LLM's clarifying question
  ready_for_optimization: boolean;  // true when confidence is high enough (hidden from user)
}

/**
 * Response from /api/refine/continue - continues conversation
 */
export interface RefinementContinueResponse {
  conversation_id: string;
  question: string | null;  // null means ready
  ready_for_optimization: boolean;
  refined_description?: string;  // final cleaned description
  needs_data: boolean;  // true if params unclear, need file upload
}

/**
 * Internal conversation state (server-side only, NOT sent to frontend)
 */
export interface ConversationState {
  id: string;
  initial_description: string;  // Original user input
  history: Message[];
  refined_description: string;
  confidence: number;  // 0-1, NEVER exposed to user
  iteration: number;
  params_extracted: boolean;
  needs_data: boolean;  // true if params unclear, need file upload
}

// ===== Optimization Types =====

/**
 * Job status - tracks optimization progress
 */
export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed';

/**
 * Represents the current stage of the OptiMUS pipeline
 */
export type OptimizationStage =
  | 'state_1_params'
  | 'state_2_objective'
  | 'state_3_constraints'
  | 'state_4_constraints_modeled'
  | 'state_5_objective_modeled'
  | 'state_6_code'
  | 'executing'
  | 'complete';

/**
 * Response from /api/optimize - starts optimization
 */
export interface OptimizeResponse {
  job_id: string;
  status: JobStatus;
}

/**
 * Response from /api/optimize/[jobId]/status - check progress
 */
export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  current_stage: OptimizationStage;
  progress_percent: number;  // 0-100
  message: string;  // Human-readable stage description
  error?: string;  // If status === 'failed'
}

/**
 * Final results from /api/optimize/[jobId]/result
 */
export interface OptimizationResult {
  explanation: string;  // Executive summary (markdown)
  technical_details: string;  // Math formulas + code + solver output
  objective_value: number;  // The optimal value found
  key_metrics: Record<string, number>;  // Decision variables for chart
  direction: 'maximize' | 'minimize';
  report_content?: string;  // NEW: Full report.md content
  baseline_comparison?: string;  // NEW: Baseline comparison section
  has_baseline_comparison?: boolean;  // NEW: Flag
  executive_summary?: string;  // NEW: Executive summary
}

// ===== Backend File System Types =====

/**
 * Structure of verdict.json from backend (WITH BASELINE)
 */
export interface VerDict {
  winner: 'optimus' | 'optimind';
  objective_value: number;
  direction: 'maximize' | 'minimize';
  solvers: {
    optimus: {
      status: 'success' | 'executed' | 'not_available';
      objective_value: number | null;
    };
    optimind: {
      status: 'success' | 'executed' | 'not_available';
      objective_value: number | null;
    };
  };
  reasoning: string;
  optimus_assessment: string;  // NOT shown to user
  optimind_assessment: string;  // NOT shown to user
  explanation: string;  // Shown to user
  technical_details: string;  // Shown to user
  baseline_comparison?: string;  // NEW: Baseline comparison section from consultant
  has_baseline_comparison?: boolean;  // NEW: Flag indicating if baseline exists
  executive_summary?: string;  // NEW: Executive summary from consultant
}

/**
 * Parameters structure from params.json
 */
export interface ParameterDefinition {
  shape: number[];
  definition: string;
  type: 'float' | 'int' | 'string';
  value: number | string;
}

export interface ParamsJSON {
  [paramName: string]: ParameterDefinition;
}

// ===== Internal Job Tracking (Server-side only) =====

/**
 * Tracks running optimization jobs on the server
 */
export interface JobInfo {
  id: string;
  status: JobStatus;
  current_stage: OptimizationStage;
  progress_percent: number;
  conversation_id: string;
  created_at: Date;
  completed_at?: Date;
  result?: OptimizationResult;
  error?: string;
}

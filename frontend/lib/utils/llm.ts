/**
 * LLM Utility (OpenAI API)
 *
 * Handles conversational refinement of optimization problems using GPT-4.
 * CRITICAL: Confidence scores are tracked internally but NEVER exposed to the user.
 */

import OpenAI from 'openai';

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

/**
 * System prompt for LLM refinement
 *
 * This instructs the LLM to act as an optimization expert and extract key information
 */
const REFINEMENT_SYSTEM_PROMPT = `You are an expert optimization consultant helping users formulate mathematical optimization problems.

Your task is to extract the following from the user's description:
1. **Objective**: What are they trying to maximize or minimize?
2. **Decision Variables**: What values need to be determined?
3. **Constraints**: What limitations or requirements exist?
4. **Parameters**: What are the known values (costs, capacities, demands, etc.)?

Ask clarifying questions ONE AT A TIME if anything is unclear. Be conversational and friendly.

After each user response, internally assess your confidence (0-100%) that you have ALL the information needed to create a complete mathematical formulation.

Respond in JSON format:
{
  "question": "Your clarifying question (null if you're confident)",
  "confidence": 0.92,
  "refined_description": "Complete problem description with all details",
  "needs_data": false  // true if numerical parameters are unclear
}

IMPORTANT:
- If confidence >= 90%, set question to null (ready to proceed)
- If user lacks concrete numerical data (costs, capacities, etc.), set needs_data to true and ask them to provide a CSV or JSON file with the parameters
- If user says things like "not sure", "don't know", "where can I find", they need to upload data
- Prioritize getting actual data files over vague estimates
- Be thorough but efficient - don't ask unnecessary questions`;

/**
 * LLM Response structure (internal only)
 */
interface LLMResponse {
  question: string | null;
  confidence: number;  // 0-1, NEVER sent to frontend
  refined_description: string;
  needs_data: boolean;
}

/**
 * Start refinement conversation
 *
 * Takes initial user description and asks first clarifying question
 */
export async function startRefinement(initialDescription: string): Promise<{
  question: string | null;
  readyForOptimization: boolean;
  needsData: boolean;
  internalConfidence: number;  // For backend tracking only
}> {
  console.log('[LLM] Starting refinement conversation...');

  try {
    const response = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages: [
        { role: 'system', content: REFINEMENT_SYSTEM_PROMPT },
        { role: 'user', content: initialDescription },
      ],
      response_format: { type: 'json_object' },
      temperature: 0.3,  // Lower temperature for consistency
    });

    const content = response.choices[0].message.content;
    if (!content) {
      throw new Error('Empty response from LLM');
    }

    const llmResponse: LLMResponse = JSON.parse(content);

    console.log(`[LLM] Confidence: ${(llmResponse.confidence * 100).toFixed(0)}% (internal only)`);

    // Check if we're ready to proceed
    const readyForOptimization = llmResponse.confidence >= 0.90 || llmResponse.question === null;

    return {
      question: llmResponse.question,
      readyForOptimization,
      needsData: llmResponse.needs_data,
      internalConfidence: llmResponse.confidence,  // NOT sent to frontend
    };
  } catch (error: any) {
    console.error('[LLM] Refinement failed:', error.message);
    throw new Error(`LLM refinement failed: ${error.message}`);
  }
}

/**
 * Continue refinement conversation
 *
 * Takes conversation history and user's latest response
 */
export async function continueRefinement(
  conversationHistory: { role: 'system' | 'user' | 'assistant'; content: string }[],
  userResponse: string,
  iterationCount: number
): Promise<{
  question: string | null;
  readyForOptimization: boolean;
  refinedDescription: string;
  needsData: boolean;
  internalConfidence: number;
}> {
  console.log(`[LLM] Continuing refinement (iteration ${iterationCount})...`);

  // Check if we've hit max iterations
  const atMaxIterations = iterationCount >= 5;

  try {
    const messages = [
      { role: 'system' as const, content: REFINEMENT_SYSTEM_PROMPT },
      ...conversationHistory,
      { role: 'user' as const, content: userResponse },
    ];

    if (atMaxIterations) {
      // At max iterations, ask LLM to make final assessment
      messages.push({
        role: 'system' as const,
        content: 'This is the 5th iteration. Assess if you have enough information. If parameters are still unclear, set needs_data to true.',
      });
    }

    const response = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages,
      response_format: { type: 'json_object' },
      temperature: 0.3,
    });

    const content = response.choices[0].message.content;
    if (!content) {
      throw new Error('Empty response from LLM');
    }

    const llmResponse: LLMResponse = JSON.parse(content);

    console.log(`[LLM] Confidence: ${(llmResponse.confidence * 100).toFixed(0)}% (internal only)`);

    // Ready if: high confidence AND no data needed
    // NEVER proceed if confidence < 80% or data is explicitly needed
    const hasHighConfidence = llmResponse.confidence >= 0.90;
    const hasSufficientConfidence = llmResponse.confidence >= 0.80;

    let readyForOptimization = false;
    let finalQuestion = llmResponse.question;

    if (hasHighConfidence && !llmResponse.needs_data) {
      // Ideal: high confidence and all data available
      readyForOptimization = true;
      finalQuestion = null;
    } else if (atMaxIterations) {
      // At max iterations with incomplete data: request file upload
      if (llmResponse.needs_data || !hasSufficientConfidence) {
        // Force data upload request
        readyForOptimization = false;
        finalQuestion = "I need specific numerical data to set up this optimization. Please upload a CSV or JSON file containing your data to progress further.";
      } else {
        // Sufficient confidence, proceed
        readyForOptimization = true;
        finalQuestion = null;
      }
    }

    return {
      question: readyForOptimization ? null : finalQuestion,
      readyForOptimization,
      refinedDescription: llmResponse.refined_description,
      needsData: llmResponse.needs_data,
      internalConfidence: llmResponse.confidence,
    };
  } catch (error: any) {
    console.error('[LLM] Refinement continuation failed:', error.message);
    throw new Error(`LLM refinement failed: ${error.message}`);
  }
}

/**
 * Parse user-provided data (JSON or CSV format)
 *
 * Users can paste data directly in the chat if they don't have a file
 */
export function parseUserProvidedData(userInput: string): Record<string, any> | null {
  try {
    // Try parsing as JSON first
    const jsonData = JSON.parse(userInput);
    return jsonData;
  } catch {
    // Try parsing as CSV
    try {
      const lines = userInput.trim().split('\n');
      if (lines.length < 2) return null;

      const params: Record<string, any> = {};

      // Simple CSV: parameter,value format
      for (const line of lines) {
        const [key, value] = line.split(',').map(s => s.trim());
        if (key && value && key !== 'parameter') {  // Skip header
          // Try to parse as number
          const numValue = parseFloat(value);
          params[key] = {
            shape: [],
            definition: `Parameter: ${key}`,
            type: Number.isInteger(numValue) ? 'int' : 'float',
            value: isNaN(numValue) ? value : numValue,
          };
        }
      }

      return Object.keys(params).length > 0 ? params : null;
    } catch {
      return null;
    }
  }
}

/**
 * Extract parameters from description (if user doesn't upload data)
 *
 * This generates params.json content from the refined description
 */
export async function extractParameters(refinedDescription: string): Promise<Record<string, any>> {
  console.log('[LLM] Extracting parameters from description...');

  const extractionPrompt = `Extract all numerical parameters from this optimization problem description and format them as JSON matching this structure:

{
  "ParameterName": {
    "shape": [],
    "definition": "Description of this parameter",
    "type": "float" | "int",
    "value": <number>
  }
}

Description:
${refinedDescription}

Return ONLY valid JSON, no additional text.`;

  try {
    const response = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages: [
        { role: 'system', content: 'You are a parameter extraction expert.' },
        { role: 'user', content: extractionPrompt },
      ],
      response_format: { type: 'json_object' },
      temperature: 0.1,  // Very low for accuracy
    });

    const content = response.choices[0].message.content;
    if (!content) {
      throw new Error('Empty response from LLM');
    }

    const params = JSON.parse(content);

    console.log('[LLM] ✓ Parameters extracted:', Object.keys(params).length, 'parameters');

    return params;
  } catch (error: any) {
    console.error('[LLM] Parameter extraction failed:', error.message);
    throw new Error(`Failed to extract parameters: ${error.message}`);
  }
}

/**
 * API Route: POST /api/refine/start
 *
 * Starts the baseline assessment conversation (NEW WORKFLOW).
 *
 * Flow:
 * 1. User has already provided problem description
 * 2. Now we ask about their CURRENT approach (baseline)
 * 3. Ask up to 3 questions about current metrics, methods, challenges
 * 4. Build baseline understanding for comparison
 */

import { NextRequest, NextResponse } from 'next/server';
import { nanoid } from 'nanoid';
import { startBaselineAssessment } from '@/lib/utils/llm';
import { saveConversation } from '@/lib/utils/store';
import { ConversationState } from '@/lib/types';

export async function POST(request: NextRequest) {
  console.log('\n[API] POST /api/refine/start (Baseline Assessment)');

  try {
    // Parse request body
    const body = await request.json();
    const { initial_description, stage } = body;

    if (!initial_description || typeof initial_description !== 'string') {
      return NextResponse.json(
        { error: 'initial_description is required and must be a string' },
        { status: 400 }
      );
    }

    // Check if this is baseline stage
    if (stage !== 'baseline') {
      return NextResponse.json(
        { error: 'This route is for baseline assessment only' },
        { status: 400 }
      );
    }

    console.log('[API] Problem description:', initial_description.substring(0, 100) + '...');
    console.log('[API] Starting baseline assessment...');

    // Call LLM to start baseline assessment
    const llmResponse = await startBaselineAssessment(initial_description);

    // Create conversation state
    const conversationId = nanoid();
    const conversation: ConversationState = {
      id: conversationId,
      initial_description: initial_description,
      history: [],
      refined_description: initial_description,
      confidence: 1.0,  // Not used for baseline
      iteration: 1,
      params_extracted: false,
      needs_data: false,
    };

    // Add LLM's baseline question to history
    if (llmResponse.question) {
      conversation.history.push({
        role: 'assistant',
        content: llmResponse.question,
        timestamp: new Date(),
      });
    }

    // Save conversation
    saveConversation(conversation);

    // Prepare response
    const response = {
      conversation_id: conversationId,
      question: llmResponse.question,
      ready_for_optimization: llmResponse.question === null,
      baseline_summary: llmResponse.baselineSummary,
    };

    console.log('[API] ✓ Baseline assessment started, conversation:', conversationId);

    return NextResponse.json(response);
  } catch (error: any) {
    console.error('[API] Error in /api/refine/start:', error.message);

    return NextResponse.json(
      { error: 'Failed to start baseline assessment', details: error.message },
      { status: 500 }
    );
  }
}

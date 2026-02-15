/**
 * API Route: POST /api/refine/start
 *
 * Starts the LLM refinement conversation.
 *
 * Flow:
 * 1. User submits initial problem description
 * 2. Call OpenAI to analyze and ask clarifying question
 * 3. Create conversation state (with hidden confidence)
 * 4. Return question to user
 *
 * CRITICAL: Confidence is tracked internally but NEVER sent to frontend!
 */

import { NextRequest, NextResponse } from 'next/server';
import { nanoid } from 'nanoid';
import { startRefinement } from '@/lib/utils/llm';
import { saveConversation } from '@/lib/utils/store';
import { ConversationState } from '@/lib/types';

export async function POST(request: NextRequest) {
  console.log('\n[API] POST /api/refine/start');

  try {
    // Parse request body
    const body = await request.json();
    const { initial_description } = body;

    if (!initial_description || typeof initial_description !== 'string') {
      return NextResponse.json(
        { error: 'initial_description is required and must be a string' },
        { status: 400 }
      );
    }

    console.log('[API] Initial description:', initial_description.substring(0, 100) + '...');

    // Call LLM to start refinement
    const llmResponse = await startRefinement(initial_description);

    // Create conversation state
    const conversationId = nanoid();
    const conversation: ConversationState = {
      id: conversationId,
      initial_description: initial_description,  // Store original input
      history: [
        {
          role: 'user',
          content: initial_description,
          timestamp: new Date(),
        },
      ],
      refined_description: initial_description,
      confidence: llmResponse.internalConfidence,  // Stored internally only
      iteration: 1,
      params_extracted: false,
      needs_data: llmResponse.needsData,  // Track if data upload is needed
    };

    // Add LLM's question to history if it exists
    if (llmResponse.question) {
      conversation.history.push({
        role: 'assistant',
        content: llmResponse.question,
        timestamp: new Date(),
      });
    }

    // Save conversation
    saveConversation(conversation);

    // Prepare response (WITHOUT confidence!)
    const response = {
      conversation_id: conversationId,
      question: llmResponse.question,
      ready_for_optimization: llmResponse.readyForOptimization,
      needs_data: llmResponse.needsData,
      // Include refined_description when ready (for immediate high-confidence scenarios)
      ...(llmResponse.readyForOptimization && { refined_description: initial_description }),
    };

    console.log('[API] ✓ Refinement started, conversation:', conversationId);

    return NextResponse.json(response);
  } catch (error: any) {
    console.error('[API] Error in /api/refine/start:', error.message);

    return NextResponse.json(
      { error: 'Failed to start refinement', details: error.message },
      { status: 500 }
    );
  }
}

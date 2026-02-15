/**
 * API Route: POST /api/refine/continue
 *
 * Continues the baseline assessment conversation (NEW WORKFLOW).
 *
 * Flow:
 * 1. Get conversation state
 * 2. Add user's baseline response
 * 3. Ask next baseline question (max 3 total)
 * 4. When baseline is complete, mark ready for optimization
 */

import { NextRequest, NextResponse } from 'next/server';
import { continueBaselineAssessment } from '@/lib/utils/llm';
import { getConversation, saveConversation } from '@/lib/utils/store';

export async function POST(request: NextRequest) {
  console.log('\n[API] POST /api/refine/continue (Baseline Assessment)');

  try {
    // Parse request body
    const body = await request.json();
    const { conversation_id, user_response, iteration } = body;

    if (!conversation_id || !user_response) {
      return NextResponse.json(
        { error: 'conversation_id and user_response are required' },
        { status: 400 }
      );
    }

    console.log('[API] Conversation:', conversation_id, 'Iteration:', iteration);

    // Get existing conversation
    const conversation = getConversation(conversation_id);
    if (!conversation) {
      return NextResponse.json(
        { error: 'Conversation not found' },
        { status: 404 }
      );
    }

    // Add user response to history
    conversation.history.push({
      role: 'user',
      content: user_response,
      timestamp: new Date(),
    });

    // Build baseline history (filter out any non-user/assistant messages)
    const baselineHistory = conversation.history
      .map(msg => ({
        role: msg.role,
        content: msg.content,
      }));

    // Call LLM to continue baseline assessment
    const llmResponse = await continueBaselineAssessment(
      conversation.initial_description,
      baselineHistory,
      user_response,
      iteration || conversation.iteration
    );

    // Update conversation with baseline summary
    conversation.refined_description += `\n\nBASELINE: ${llmResponse.baselineSummary}`;
    conversation.iteration = (iteration || conversation.iteration) + 1;

    // Add LLM's next question to history if exists
    if (llmResponse.question) {
      conversation.history.push({
        role: 'assistant',
        content: llmResponse.question,
        timestamp: new Date(),
      });
    }

    // Update conversation
    saveConversation(conversation);

    // Prepare response
    const response = {
      conversation_id: conversation_id,
      question: llmResponse.question,
      ready_for_optimization: llmResponse.ready,
      refined_description: conversation.refined_description,
      baseline_summary: llmResponse.baselineSummary,
    };

    console.log('[API] ✓ Baseline assessment continued, ready:', llmResponse.ready);

    return NextResponse.json(response);
  } catch (error: any) {
    console.error('[API] Error in /api/refine/continue:', error.message);

    return NextResponse.json(
      { error: 'Failed to continue baseline assessment', details: error.message },
      { status: 500 }
    );
  }
}

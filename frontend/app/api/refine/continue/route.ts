/**
 * API Route: POST /api/refine/continue
 *
 * Continues the LLM refinement conversation.
 *
 * Flow:
 * 1. User responds to LLM's question
 * 2. Add response to conversation history
 * 3. Call OpenAI to continue refinement
 * 4. Check confidence (internally)
 * 5. If confident enough OR max iterations: ready_for_optimization = true
 * 6. Otherwise:return next question
 *
 * CRITICAL: Confidence is NEVER exposed to user! They just see smooth progression.
 */

import { NextRequest, NextResponse } from 'next/server';
import { continueRefinement, parseUserProvidedData } from '@/lib/utils/llm';
import { getConversation, saveConversation } from '@/lib/utils/store';
import { writeParamsFile } from '@/lib/utils/file-ops';

export async function POST(request: NextRequest) {
  console.log('\n[API] POST /api/refine/continue');

  try {
    // Parse request body
    const body = await request.json();
    const { conversation_id, user_response } = body;

    if (!conversation_id || !user_response) {
      return NextResponse.json(
        { error: 'conversation_id and user_response are required' },
        { status: 400 }
      );
    }

    console.log('[API] Conversation:', conversation_id, '| User response:', user_response.substring(0, 50) + '...');

    // Get existing conversation
    const conversation = getConversation(conversation_id);
    if (!conversation) {
      return NextResponse.json(
        { error: 'Conversation not found. It may have expired.' },
        { status: 404 }
      );
    }

    // Add user's response to history
    conversation.history.push({
      role: 'user',
      content: user_response,
      timestamp: new Date(),
    });

    // Check if user provided data inline (JSON/CSV format)
    const providedData = parseUserProvidedData(user_response);
    if (providedData && conversation.needs_data) {
      console.log('[API] User provided inline data! Writing to params.json...');

      // Save data to params.json
      await writeParamsFile(providedData);

      // Mark conversation as having data
      conversation.needs_data = false;
      conversation.refined_description = conversation.refined_description || conversation.initial_description;

      // Save and return ready for optimization
      saveConversation(conversation);

      console.log('[API] ✓ Data received! Ready for optimization.');

      return NextResponse.json({
        conversation_id,
        question: null,
        ready_for_optimization: true,
        refined_description: conversation.refined_description,
        needs_data: false,
      });
    }

    // Increment iteration
    conversation.iteration += 1;

    console.log(`[API] Iteration ${conversation.iteration}/5`);

    // Build conversation history for LLM
    const llmHistory = conversation.history.map((msg) => ({
      role: msg.role,
      content: msg.content,
    }));

    // Call LLM to continue refinement
    const llmResponse = await continueRefinement(
      llmHistory,
      user_response,
      conversation.iteration
    );

    // Update conversation state
    conversation.refined_description = llmResponse.refinedDescription;
    conversation.confidence = llmResponse.internalConfidence;  // Internal only
    conversation.needs_data = llmResponse.needsData;  // Track if data is needed

    // Add LLM's next question to history (if it exists)
    if (llmResponse.question) {
      conversation.history.push({
        role: 'assistant',
        content: llmResponse.question,
        timestamp: new Date(),
      });
    }

    // Save updated conversation
    saveConversation(conversation);

    // Prepare response (WITHOUT confidence!)
    const response = {
      conversation_id,
      question: llmResponse.question,  // null if ready
      ready_for_optimization: llmResponse.readyForOptimization,
      refined_description: llmResponse.readyForOptimization ? llmResponse.refinedDescription : undefined,
      needs_data: llmResponse.needsData,
    };

    if (llmResponse.readyForOptimization) {
      console.log('[API] ✓ Refinement complete! Ready for optimization.');
    } else {
      console.log('[API] ✓ Continuing refinement...');
    }

    return NextResponse.json(response);
  } catch (error: any) {
    console.error('[API] Error in /api/refine/continue:', error.message);

    return NextResponse.json(
      { error: 'Failed to continue refinement', details: error.message },
      { status: 500 }
    );
  }
}

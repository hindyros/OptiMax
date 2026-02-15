/**
 * API Route: POST /api/refine/upload
 *
 * Handles file uploads containing numerical parameters (CSV or JSON)
 * Writes to params.json and updates conversation state
 */

import { NextRequest, NextResponse } from 'next/server';
import { getConversation, saveConversation } from '@/lib/utils/store';
import fs from 'fs/promises';
import path from 'path';

/**
 * Write parameters to params.json file
 */
async function writeParamsFile(params: Record<string, any>): Promise<void> {
  const backendPath = path.join(process.cwd(), '../backend');
  const currentQueryPath = path.join(backendPath, 'current_query');
  const paramsPath = path.join(currentQueryPath, 'params.json');

  // Ensure directory exists
  await fs.mkdir(currentQueryPath, { recursive: true });

  // Write params.json
  await fs.writeFile(paramsPath, JSON.stringify(params, null, 2), 'utf-8');

  console.log(`[API] ✓ Wrote params.json with ${Object.keys(params).length} parameters`);
}

export async function POST(request: NextRequest) {
  console.log('[API] POST /api/refine/upload');

  try {
    const body = await request.json();
    const { conversation_id, params } = body;

    if (!conversation_id) {
      return NextResponse.json(
        { error: 'conversation_id is required' },
        { status: 400 }
      );
    }

    if (!params || Object.keys(params).length === 0) {
      return NextResponse.json(
        { error: 'params object is required' },
        { status: 400 }
      );
    }

    // Get conversation state
    const conversation = getConversation(conversation_id);
    if (!conversation) {
      return NextResponse.json(
        { error: 'Conversation not found' },
        { status: 404 }
      );
    }

    console.log('[API] Writing parameters to params.json...');

    // Write params to file
    await writeParamsFile(params);

    // Also write desc.txt with refined description
    const backendPath = path.join(process.cwd(), '../backend');
    const currentQueryPath = path.join(backendPath, 'current_query');
    const descPath = path.join(currentQueryPath, 'desc.txt');

    const refinedDesc = conversation.refined_description || conversation.initial_description;
    await fs.writeFile(descPath, refinedDesc, 'utf-8');
    console.log('[API] ✓ Wrote desc.txt');

    // Update conversation state
    conversation.needs_data = false;
    conversation.params_extracted = true;
    conversation.refined_description =
      conversation.refined_description || conversation.initial_description;

    saveConversation(conversation);

    console.log('[API] ✓ File upload complete! Ready for optimization.');

    return NextResponse.json({
      success: true,
      conversation_id,
      refined_description: conversation.refined_description,
      ready_for_optimization: true,
    });
  } catch (error: any) {
    console.error('[API] File upload failed:', error.message);
    return NextResponse.json(
      { error: 'Failed to process uploaded file', details: error.message },
      { status: 500 }
    );
  }
}

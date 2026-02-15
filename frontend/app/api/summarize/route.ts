/**
 * API Route: POST /api/summarize
 * 
 * Generates a concise executive summary of the optimization report using OpenAI
 */

import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(request: NextRequest) {
  console.log('\n[API] POST /api/summarize');

  try {
    const body = await request.json();
    const { report } = body;

    if (!report) {
      return NextResponse.json(
        { error: 'Report content is required' },
        { status: 400 }
      );
    }

    console.log('[API] Generating summary for report...');

    // Call OpenAI to generate a concise summary
    const completion = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages: [
        {
          role: 'system',
          content: `You are an expert at summarizing optimization reports. Generate a concise, executive-level summary that highlights:
1. The key objective and what was being optimized
2. The most important results (objective value, key decision variables)
3. Main recommendations or insights

Keep the summary to 3-5 bullet points. Be specific with numbers and concrete outcomes. Focus on business value and actionable insights.`
        },
        {
          role: 'user',
          content: `Summarize this optimization report:\n\n${report}`
        }
      ],
      temperature: 0.7,
      max_tokens: 500,
    });

    const summary = completion.choices[0]?.message?.content || '';

    console.log('[API] ✓ Summary generated');

    return NextResponse.json({
      summary,
      success: true,
    });

  } catch (error) {
    console.error('[API] Error generating summary:', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      {
        error: 'Failed to generate summary',
        details: errorMessage,
        // Return a fallback message if OpenAI fails
        summary: 'Summary generation unavailable. Please review the full report below for details.'
      },
      { status: 500 }
    );
  }
}

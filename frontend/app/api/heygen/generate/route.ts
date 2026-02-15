/**
 * API Route: POST /api/heygen/generate
 *
 * Server-side proxy for HeyGen video generation
 * Prevents CORS issues and keeps API key secure
 */

import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  console.log('[API] POST /api/heygen/generate');

  try {
    const body = await request.json();
    const { script } = body;

    if (!script) {
      return NextResponse.json(
        { error: 'script is required' },
        { status: 400 }
      );
    }

    const apiKey = process.env.NEXT_PUBLIC_HEYGEN_API_KEY;

    if (!apiKey) {
      console.error('[HeyGen] API key not configured');
      return NextResponse.json(
        { error: 'HeyGen API key not configured' },
        { status: 500 }
      );
    }

    console.log('[HeyGen] Generating video...');

    // Call HeyGen API v2
    const response = await fetch('https://api.heygen.com/v2/video/generate', {
      method: 'POST',
      headers: {
        'X-Api-Key': apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        video_inputs: [{
          character: {
            type: 'avatar',
            avatar_id: 'Abigail_expressive_2024112501',
            avatar_style: 'normal',
          },
          voice: {
            type: 'text',
            input_text: script,
            voice_id: '1bd001e7e50f421d891986aad5158bc8',  // Default English female voice
          },
        }],
        dimension: {
          width: 1280,
          height: 720,
        },
        aspect_ratio: '16:9',
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      console.error('[HeyGen] API error:', data);
      return NextResponse.json(
        { error: 'HeyGen API error', details: data },
        { status: response.status }
      );
    }

    console.log('[HeyGen] ✓ Video generation started:', data.data?.video_id || data.video_id);

    return NextResponse.json(data);
  } catch (error: any) {
    console.error('[HeyGen] Generation failed:', error.message);
    return NextResponse.json(
      { error: 'Failed to generate video', details: error.message },
      { status: 500 }
    );
  }
}

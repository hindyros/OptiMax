/**
 * API Route: GET /api/heygen/status
 *
 * Check HeyGen video generation status
 */

import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const videoId = searchParams.get('video_id');

  if (!videoId) {
    return NextResponse.json(
      { error: 'video_id parameter is required' },
      { status: 400 }
    );
  }

  const apiKey = process.env.NEXT_PUBLIC_HEYGEN_API_KEY;

  if (!apiKey) {
    return NextResponse.json(
      { error: 'HeyGen API key not configured' },
      { status: 500 }
    );
  }

  try {
    const response = await fetch(`https://api.heygen.com/v1/video_status.get?video_id=${videoId}`, {
      headers: {
        'X-Api-Key': apiKey,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      console.error('[HeyGen] Status check error:', data);
      return NextResponse.json(
        { error: 'HeyGen API error', details: data },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('[HeyGen] Status check failed:', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: 'Failed to check status', details: errorMessage },
      { status: 500 }
    );
  }
}

/**
 * HeyGen video generation — minimal working API flow
 * Use with your existing routes: POST /api/heygen/generate, GET /api/heygen/status
 */

const BASE = ''; // same origin

/**
 * 1. Start video generation. Pass the script text (cleaned summary).
 * Returns the HeyGen video_id to poll for status.
 */
export async function startHeyGenVideo(scriptContent: string): Promise<string> {
  const res = await fetch(`${BASE}/api/heygen/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ report_content: scriptContent }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error || 'Failed to start video');
  const videoId = data?.data?.video_id ?? data?.video_id;
  if (!videoId) throw new Error('No video_id in response');
  return videoId;
}

/**
 * 2. Check status once. Returns { status, videoUrl }.
 */
export async function getHeyGenStatus(videoId: string): Promise<{
  status: 'processing' | 'completed' | 'failed';
  videoUrl?: string;
  error?: string;
}> {
  const res = await fetch(`${BASE}/api/heygen/status?video_id=${encodeURIComponent(videoId)}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error || 'Failed to get status');
  const status = (data?.data?.status ?? data?.status) ?? 'processing';
  const videoUrl = data?.data?.video_url ?? data?.video_url;
  const error = data?.data?.error ?? data?.error;
  return { status, videoUrl, error };
}

/**
 * 3. Poll until completed or failed (max 15 min). Returns the playable video URL.
 */
export async function waitForHeyGenVideo(
  videoId: string,
  onProgress?: (message: string) => void
): Promise<string> {
  const start = Date.now();
  const maxMs = 15 * 60 * 1000;
  const intervalMs = 5000;

  while (Date.now() - start < maxMs) {
    const { status, videoUrl, error } = await getHeyGenStatus(videoId);

    if (status === 'completed' && videoUrl) return videoUrl;
    if (status === 'failed') throw new Error(error || 'Video generation failed');

    const elapsed = Math.floor((Date.now() - start) / 1000);
    onProgress?.(`Rendering... ${Math.floor(elapsed / 60)}m ${elapsed % 60}s`);
    await new Promise((r) => setTimeout(r, intervalMs));
  }

  throw new Error('Timeout waiting for video');
}

/**
 * Full flow: start generation, poll until done, return video URL.
 * Pass the cleaned script content (e.g., LLM-generated summary).
 */
export async function generateHeyGenVideo(
  scriptContent: string,
  onProgress?: (message: string) => void
): Promise<string> {
  onProgress?.('Starting...');
  const videoId = await startHeyGenVideo(scriptContent);
  onProgress?.('Rendering started.');
  return waitForHeyGenVideo(videoId, onProgress);
}

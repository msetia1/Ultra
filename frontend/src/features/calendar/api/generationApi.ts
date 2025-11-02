/**
 * API service for week generation
 * Streams generation events from backend SSE endpoint
 */

import type { WeekGenerationRequest, GenerationSSEEvent } from '../types/generation.types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Stream week generation events from backend
 * Uses async generator pattern for easy consumption
 */
export async function* streamWeekGeneration(
  weekId: string,
  request: WeekGenerationRequest
): AsyncGenerator<GenerationSSEEvent> {
  console.log('[generationApi] Starting generation for week:', weekId);
  console.log('[generationApi] Request:', request);

  const response = await fetch(
    `${API_BASE_URL}/calendar/generate-week/${weekId}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    console.error('[generationApi] HTTP error:', response.status, errorText);
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error('No response body');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let eventCount = 0;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        console.log('[generationApi] Stream complete, total events:', eventCount);
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Split by SSE event separator
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const event of events) {
        if (!event.trim() || !event.startsWith('data: ')) continue;

        try {
          const data: GenerationSSEEvent = JSON.parse(event.slice(6));
          eventCount++;
          console.log('[generationApi] Event received:', data.event_type);
          yield data;
        } catch (e) {
          console.error('[generationApi] Failed to parse SSE event:', e);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

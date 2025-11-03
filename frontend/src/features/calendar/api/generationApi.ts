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
        console.log('[generationApi] ✅ Stream done, total events:', eventCount);
        console.log('[generationApi] Remaining buffer:', buffer.length, 'bytes');
        if (buffer.trim()) {
          console.warn('[generationApi] ⚠️ Unparsed buffer remaining:', buffer.substring(0, 200));
        }
        break;
      }

      const chunk = decoder.decode(value, { stream: true });
      console.log('[generationApi] 📥 Received chunk:', chunk.length, 'bytes');

      buffer += chunk;
      console.log('[generationApi] Current buffer size:', buffer.length, 'bytes');

      // Split by SSE event separator
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      console.log('[generationApi] Processing', events.length, 'potential events from chunk');

      for (const event of events) {
        if (!event.trim()) {
          console.log('[generationApi] Skipping empty event');
          continue;
        }

        if (!event.startsWith('data: ')) {
          console.log('[generationApi] Skipping non-data event:', event.substring(0, 50));
          continue;
        }

        try {
          const jsonStr = event.slice(6);
          console.log('[generationApi] Parsing JSON:', jsonStr.substring(0, 100) + '...');

          const data: GenerationSSEEvent = JSON.parse(jsonStr);
          eventCount++;
          console.log('[generationApi] ✓ Event', eventCount, ':', data.event_type);

          if (data.event_type === 'event_ready') {
            console.log('[generationApi]   → Event #' + data.event_number + ':', data.event_data.title);
          } else if (data.event_type === 'generation_complete') {
            console.log('[generationApi]   → 🎉 Complete! Total:', data.total_events);
          }

          console.log('[generationApi] ⏰ About to yield event at', new Date().toISOString());
          yield data;
          console.log('[generationApi] ⏰ After yielding event at', new Date().toISOString());

          // Stop reading immediately after terminal events
          if (data.event_type === 'generation_complete' || data.event_type === 'generation_error') {
            console.log('[generationApi] 🏁 Terminal event received at', new Date().toISOString());
            console.log('[generationApi] 🏁 Calling reader.cancel()...');
            reader.cancel();
            console.log('[generationApi] 🏁 Returning from generator at', new Date().toISOString());
            return;
          }
        } catch (e) {
          console.error('[generationApi] ❌ Parse error:', e);
          console.error('[generationApi] Failed event string:', event.substring(0, 200));
        }
      }
    }
  } finally {
    console.log('[generationApi] Releasing reader lock');
    reader.releaseLock();
  }
}

/**
 * Hook for week generation with SSE streaming
 */

import { useState, useCallback } from 'react';
import { streamWeekGeneration } from '../api/generationApi';
import type { GeneratedEvent, WeekGenerationRequest } from '../types/generation.types';

export function useWeekGeneration() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [events, setEvents] = useState<GeneratedEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [totalEvents, setTotalEvents] = useState(0);

  const generateWeek = useCallback(async (
    weekId: string,
    request: WeekGenerationRequest
  ) => {
    console.log('[useWeekGeneration] Starting generation for week:', weekId);

    // Prevent duplicate calls while generation is in progress
    if (isGenerating) {
      console.warn('[useWeekGeneration] ⚠️ Generation already in progress, ignoring duplicate call');
      return;
    }

    try {
      setIsGenerating(true);
      setEvents([]);
      setError(null);
      setIsComplete(false);
      setTotalEvents(0);

      // Stream events from API
      for await (const event of streamWeekGeneration(weekId, request)) {
        if (event.event_type === 'streaming_started') {
          console.log('[useWeekGeneration] Streaming started:', event.message);

        } else if (event.event_type === 'event_ready') {
          // Accumulate generated events
          console.log('[useWeekGeneration] Event ready:', event.event_number, event.event_data.title);
          setEvents(prev => [...prev, event.event_data]);

        } else if (event.event_type === 'generation_complete') {
          // Mark generation as complete
          console.log('[useWeekGeneration] Generation complete:', event.total_events, 'events');
          setTotalEvents(event.total_events);
          setIsComplete(true);
          break;

        } else if (event.event_type === 'generation_error') {
          // Handle error
          console.error('[useWeekGeneration] Generation error:', event.error);
          setError(event.error);
          break;
        }
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Generation failed';
      console.error('[useWeekGeneration] Exception:', errorMessage);
      setError(errorMessage);
    } finally {
      setIsGenerating(false);
    }
  }, [isGenerating]);

  const reset = useCallback(() => {
    setEvents([]);
    setError(null);
    setIsComplete(false);
    setTotalEvents(0);
  }, []);

  return {
    generateWeek,
    isGenerating,
    events,
    error,
    isComplete,
    totalEvents,
    reset,
  };
}

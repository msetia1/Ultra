/**
 * Types for week generation feature
 */

export interface GeneratedEvent {
  title: string;
  description: string;
  scheduled_date: string;  // YYYY-MM-DD
  start_time: string;       // HH:MM
  end_time: string;         // HH:MM
  event_type?: string;
  priority?: string;
}

export interface WeekGenerationRequest {
  user_goals?: string;
  user_context?: Record<string, any>;
}

export type GenerationSSEEvent =
  | { event_type: 'streaming_started'; message: string; progress: number }
  | { event_type: 'event_ready'; event_number: number; event_data: GeneratedEvent; event_id?: string }
  | { event_type: 'generation_complete'; total_events: number }
  | { event_type: 'generation_error'; error: string };

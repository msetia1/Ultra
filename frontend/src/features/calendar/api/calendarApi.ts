/**
 * API service for calendar events
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface CalendarEvent {
  id: string;
  user_id: string;
  title: string;
  description: string;
  scheduled_date: string; // YYYY-MM-DD
  start_time: string;     // HH:MM
  end_time: string;       // HH:MM
  created_at: string;
  updated_at: string;
}

export interface FetchEventsResponse {
  events: CalendarEvent[];
}

/**
 * Fetch calendar events for a specific week
 */
export async function fetchWeekEvents(weekId: string): Promise<CalendarEvent[]> {
  console.log('[calendarApi] Fetching events for week:', weekId);

  const response = await fetch(
    `${API_BASE_URL}/calendar/events?week_id=${weekId}`,
    {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    console.error('[calendarApi] HTTP error:', response.status, errorText);
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const data: FetchEventsResponse = await response.json();
  console.log('[calendarApi] Fetched', data.events.length, 'events');

  return data.events;
}

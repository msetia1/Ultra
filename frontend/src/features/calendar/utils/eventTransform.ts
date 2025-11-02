/**
 * Event transformation utilities
 * Converts between API formats (GeneratedEvent, CalendarEvent) and UI format (Task)
 */

import type { Task } from '../types/calendar.types';
import type { GeneratedEvent } from '../types/generation.types';
import type { CalendarEvent } from '../api/calendarApi';

/**
 * Convert a generated event (from SSE stream) to Task format
 */
export function transformGeneratedEventToTask(
  event: GeneratedEvent,
  weekStart: Date
): Task {
  // Parse scheduled_date (YYYY-MM-DD)
  const scheduledDate = new Date(event.scheduled_date);

  // Create Date objects for start and end times
  const [startHour, startMinute] = event.start_time.split(':').map(Number);
  const startTime = new Date(scheduledDate);
  startTime.setHours(startHour, startMinute, 0, 0);

  const [endHour, endMinute] = event.end_time.split(':').map(Number);
  const endTime = new Date(scheduledDate);
  endTime.setHours(endHour, endMinute, 0, 0);

  // Calculate dayOfWeek (0=Monday, 6=Sunday)
  const dayOfWeek = calculateDayOfWeek(scheduledDate, weekStart);

  return {
    id: `generated-${Date.now()}-${Math.random()}`, // Temporary ID until backend assigns one
    title: event.title,
    description: event.description,
    startTime,
    endTime,
    dayOfWeek,
  };
}

/**
 * Convert a calendar event (from API) to Task format
 */
export function transformCalendarEventToTask(
  event: CalendarEvent,
  weekStart: Date
): Task {
  // Parse scheduled_date (YYYY-MM-DD)
  const scheduledDate = new Date(event.scheduled_date);

  // Create Date objects for start and end times
  const [startHour, startMinute] = event.start_time.split(':').map(Number);
  const startTime = new Date(scheduledDate);
  startTime.setHours(startHour, startMinute, 0, 0);

  const [endHour, endMinute] = event.end_time.split(':').map(Number);
  const endTime = new Date(scheduledDate);
  endTime.setHours(endHour, endMinute, 0, 0);

  // Calculate dayOfWeek (0=Monday, 6=Sunday)
  const dayOfWeek = calculateDayOfWeek(scheduledDate, weekStart);

  return {
    id: event.id,
    title: event.title,
    description: event.description,
    startTime,
    endTime,
    dayOfWeek,
  };
}

/**
 * Calculate day of week index relative to week start (Monday)
 * Returns: 0=Monday, 1=Tuesday, ... 6=Sunday
 */
function calculateDayOfWeek(date: Date, weekStart: Date): number {
  const msPerDay = 86400000;
  const daysDiff = Math.floor((date.getTime() - weekStart.getTime()) / msPerDay);
  return daysDiff;
}

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
  // Parse scheduled_date (YYYY-MM-DD) in local timezone
  const [year, month, day] = event.scheduled_date.split('-').map(Number);
  const scheduledDate = new Date(year, month - 1, day);

  // Create Date objects for start and end times
  const [startHour, startMinute] = event.start_time.split(':').map(Number);
  const startTime = new Date(scheduledDate);
  startTime.setHours(startHour, startMinute, 0, 0);

  const [endHour, endMinute] = event.end_time.split(':').map(Number);
  const endTime = new Date(scheduledDate);
  endTime.setHours(endHour, endMinute, 0, 0);

  // Calculate dayOfWeek (0=Monday, 6=Sunday)
  const dayOfWeek = calculateDayOfWeek(event.scheduled_date, weekStart);

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
  // Parse scheduled_date (YYYY-MM-DD) in local timezone
  const [year, month, day] = event.scheduled_date.split('-').map(Number);
  const scheduledDate = new Date(year, month - 1, day);

  // Create Date objects for start and end times
  const [startHour, startMinute] = event.start_time.split(':').map(Number);
  const startTime = new Date(scheduledDate);
  startTime.setHours(startHour, startMinute, 0, 0);

  const [endHour, endMinute] = event.end_time.split(':').map(Number);
  const endTime = new Date(scheduledDate);
  endTime.setHours(endHour, endMinute, 0, 0);

  // Calculate dayOfWeek (0=Monday, 6=Sunday)
  const dayOfWeek = calculateDayOfWeek(event.scheduled_date, weekStart);

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
 *
 * @param dateStr - Date string in YYYY-MM-DD format
 * @param weekStart - Week start date (will be normalized to midnight)
 */
function calculateDayOfWeek(dateStr: string, weekStart: Date): number {
  // Parse date in local timezone (not UTC) to avoid timezone conversion
  const [year, month, day] = dateStr.split('-').map(Number);
  const eventDate = new Date(year, month - 1, day);

  // Normalize both dates to midnight for accurate day comparison
  eventDate.setHours(0, 0, 0, 0);
  const normalizedWeekStart = new Date(weekStart);
  normalizedWeekStart.setHours(0, 0, 0, 0);

  const msPerDay = 86400000;
  const daysDiff = Math.round((eventDate.getTime() - normalizedWeekStart.getTime()) / msPerDay);
  return daysDiff;
}

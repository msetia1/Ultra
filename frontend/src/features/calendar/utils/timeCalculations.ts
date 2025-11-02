/**
 * Format time for display (e.g., "10:00 AM")
 */
export function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
}

/**
 * Calculate the vertical position of a task card based on its start time
 * Assumes a day starts at 6 AM and ends at 10 PM (16 hours)
 * Returns a percentage value for positioning
 */
export function calculateTaskPosition(startTime: Date): number {
  const hours = startTime.getHours();
  const minutes = startTime.getMinutes();

  const dayStartHour = 6; // 6 AM
  const dayEndHour = 22;  // 10 PM
  const totalDayHours = dayEndHour - dayStartHour;

  // Convert time to hours since day start
  const hoursSinceDayStart = (hours - dayStartHour) + (minutes / 60);

  // Calculate percentage (clamped between 0 and 100)
  const percentage = (hoursSinceDayStart / totalDayHours) * 100;
  return Math.max(0, Math.min(100, percentage));
}

/**
 * Calculate the height of a task card based on duration
 * Returns a percentage value
 */
export function calculateTaskHeight(startTime: Date, endTime: Date): number {
  const durationMs = endTime.getTime() - startTime.getTime();
  const durationHours = durationMs / (1000 * 60 * 60);

  const totalDayHours = 16; // 6 AM to 10 PM
  const percentage = (durationHours / totalDayHours) * 100;

  return Math.max(5, Math.min(100, percentage)); // Minimum 5% height
}

/**
 * Parse time string (e.g., "10:00 AM") to Date object for today
 */
export function parseTimeString(timeStr: string, baseDate: Date = new Date()): Date {
  const [time, period] = timeStr.split(' ');
  const [hours, minutes] = time.split(':').map(Number);

  let hour24 = hours;
  if (period === 'PM' && hours !== 12) {
    hour24 = hours + 12;
  } else if (period === 'AM' && hours === 12) {
    hour24 = 0;
  }

  const date = new Date(baseDate);
  date.setHours(hour24, minutes, 0, 0);
  return date;
}

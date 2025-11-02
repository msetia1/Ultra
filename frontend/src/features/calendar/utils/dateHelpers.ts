/**
 * Get the start of the week (Monday) for a given date
 */
export function getWeekStart(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust when day is Sunday
  return new Date(d.setDate(diff));
}

/**
 * Get the end of the week (Sunday) for a given date
 */
export function getWeekEnd(date: Date): Date {
  const start = getWeekStart(date);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  return end;
}

/**
 * Format date range for display (e.g., "November 3rd-10th")
 */
export function formatDateRange(startDate: Date, endDate: Date): string {
  const monthName = startDate.toLocaleDateString('en-US', { month: 'long' });
  const startDay = formatDayWithSuffix(startDate.getDate());
  const endDay = formatDayWithSuffix(endDate.getDate());

  return `${monthName} ${startDay}-${endDay}`;
}

/**
 * Add ordinal suffix to day number (1st, 2nd, 3rd, 4th, etc.)
 */
function formatDayWithSuffix(day: number): string {
  const suffixes = ['th', 'st', 'nd', 'rd'];
  const value = day % 100;
  return day + (suffixes[(value - 20) % 10] || suffixes[value] || suffixes[0]);
}

/**
 * Get day name and date number for a given date
 */
export function getDayInfo(date: Date): { name: string; number: number } {
  const dayName = date.toLocaleDateString('en-US', { weekday: 'long' });
  const number = date.getDate();
  return { name: dayName, number };
}

/**
 * Generate array of dates for current week
 */
export function getWeekDates(startDate: Date): Date[] {
  const dates: Date[] = [];
  for (let i = 0; i < 7; i++) {
    const date = new Date(startDate);
    date.setDate(startDate.getDate() + i);
    dates.push(date);
  }
  return dates;
}

/**
 * Get the current week start date
 */
export function getCurrentWeekStart(): Date {
  return getWeekStart(new Date());
}

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

/**
 * Check if two tasks overlap in time
 */
export function tasksOverlap(
  task1: { startTime: Date; endTime: Date },
  task2: { startTime: Date; endTime: Date }
): boolean {
  // Tasks overlap if one starts before the other ends
  return !(
    task1.endTime.getTime() <= task2.startTime.getTime() ||
    task2.endTime.getTime() <= task1.startTime.getTime()
  );
}

/**
 * Group overlapping tasks into collision groups
 * Each group contains tasks that overlap with each other
 */
export interface TaskWithLayout {
  id: string;
  startTime: Date;
  endTime: Date;
  lane: number;      // Horizontal lane assignment (0, 1, 2, ...)
  totalLanes: number; // Total lanes in this group
}

export function calculateTaskLayout<T extends { id: string; startTime: Date; endTime: Date }>(
  tasks: T[]
): Map<string, { lane: number; totalLanes: number }> {
  const layout = new Map<string, { lane: number; totalLanes: number }>();

  if (tasks.length === 0) return layout;

  // Sort tasks by start time
  const sortedTasks = [...tasks].sort(
    (a, b) => a.startTime.getTime() - b.startTime.getTime()
  );

  // Find all collision groups (sets of overlapping tasks)
  const collisionGroups: T[][] = [];

  for (const task of sortedTasks) {
    // Find groups this task overlaps with
    const overlappingGroups = collisionGroups.filter(group =>
      group.some(groupTask => tasksOverlap(task, groupTask))
    );

    if (overlappingGroups.length === 0) {
      // No overlap, create new group
      collisionGroups.push([task]);
    } else if (overlappingGroups.length === 1) {
      // Overlaps with one group, add to it
      overlappingGroups[0].push(task);
    } else {
      // Overlaps with multiple groups, merge them
      const mergedGroup = overlappingGroups.reduce((acc, group) => {
        // Remove this group from collisionGroups
        const index = collisionGroups.indexOf(group);
        if (index > -1) {
          collisionGroups.splice(index, 1);
        }
        return [...acc, ...group];
      }, [task]);
      collisionGroups.push(mergedGroup);
    }
  }

  // Assign lanes within each collision group
  for (const group of collisionGroups) {
    const totalLanes = calculateMaxConcurrentTasks(group);

    // Sort group by start time
    const sortedGroup = [...group].sort(
      (a, b) => a.startTime.getTime() - b.startTime.getTime()
    );

    // Assign lanes using greedy algorithm
    const laneEndTimes: (number | null)[] = Array(totalLanes).fill(null);

    for (const task of sortedGroup) {
      // Find first available lane
      let assignedLane = -1;
      for (let i = 0; i < totalLanes; i++) {
        if (laneEndTimes[i] === null || laneEndTimes[i]! <= task.startTime.getTime()) {
          assignedLane = i;
          laneEndTimes[i] = task.endTime.getTime();
          break;
        }
      }

      // If no lane found (shouldn't happen), use last lane
      if (assignedLane === -1) {
        assignedLane = totalLanes - 1;
        laneEndTimes[assignedLane] = task.endTime.getTime();
      }

      layout.set(task.id, { lane: assignedLane, totalLanes });
    }
  }

  return layout;
}

/**
 * Calculate maximum number of concurrent tasks at any point in time
 */
function calculateMaxConcurrentTasks<T extends { startTime: Date; endTime: Date }>(
  tasks: T[]
): number {
  if (tasks.length === 0) return 0;

  // Create events for start and end times
  const events: { time: number; type: 'start' | 'end' }[] = [];

  for (const task of tasks) {
    events.push({ time: task.startTime.getTime(), type: 'start' });
    events.push({ time: task.endTime.getTime(), type: 'end' });
  }

  // Sort events by time, with ends before starts at same time
  events.sort((a, b) => {
    if (a.time !== b.time) return a.time - b.time;
    return a.type === 'end' ? -1 : 1;
  });

  let currentConcurrent = 0;
  let maxConcurrent = 0;

  for (const event of events) {
    if (event.type === 'start') {
      currentConcurrent++;
      maxConcurrent = Math.max(maxConcurrent, currentConcurrent);
    } else {
      currentConcurrent--;
    }
  }

  return maxConcurrent;
}

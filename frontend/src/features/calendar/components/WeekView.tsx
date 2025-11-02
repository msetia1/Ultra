import type { Task } from '../types/calendar.types';
import { getWeekDates } from '../utils/dateHelpers';
import DayColumn from './DayColumn';

interface WeekViewProps {
  weekStart: Date;
  tasks: Task[];
  className?: string;
  selectedTaskId: string | null;
  onTaskClick: (taskId: string) => void;
  isChatOpen?: boolean;
}

export default function WeekView({
  weekStart,
  tasks,
  className = '',
  selectedTaskId,
  onTaskClick,
  isChatOpen
}: WeekViewProps) {
  const weekDates = getWeekDates(weekStart);

  // Group tasks by day of week
  const getTasksForDay = (dayIndex: number) => {
    return tasks.filter(task => task.dayOfWeek === dayIndex);
  };

  return (
    <div
      className={`
        grid grid-cols-7 flex-1
        ${className}
      `}
    >
      {weekDates.map((date, index) => (
        <DayColumn
          key={date.toISOString()}
          date={date}
          tasks={getTasksForDay(index)}
          className={index === 6 ? 'border-r-0' : ''}
          selectedTaskId={selectedTaskId}
          onTaskClick={onTaskClick}
          isChatOpen={isChatOpen}
        />
      ))}
    </div>
  );
}

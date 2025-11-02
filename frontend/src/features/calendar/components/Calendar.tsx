import { useEffect } from 'react';
import { useCalendarStore } from '../store/calendarStore';
import { getWeekEnd } from '../utils/dateHelpers';
import CalendarHeader from './CalendarHeader';
import WeekView from './WeekView';

interface CalendarProps {
  onToggleChat?: () => void;
  className?: string;
}

export default function Calendar({ onToggleChat, className = '' }: CalendarProps) {
  const {
    currentWeekStart,
    tasks,
    isLoading,
    error,
    nextWeek,
    previousWeek,
    loadMockData
  } = useCalendarStore();

  // Load mock data on mount
  useEffect(() => {
    loadMockData();
  }, [loadMockData]);

  const weekEnd = getWeekEnd(currentWeekStart);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-black text-red-500">
        Error: {error}
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full bg-black ${className}`}>
      <CalendarHeader
        weekStart={currentWeekStart}
        weekEnd={weekEnd}
        onPreviousWeek={previousWeek}
        onNextWeek={nextWeek}
        onToggleChat={onToggleChat}
      />

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center text-[#fcecc9]">
          Loading...
        </div>
      ) : (
        <WeekView weekStart={currentWeekStart} tasks={tasks} />
      )}
    </div>
  );
}

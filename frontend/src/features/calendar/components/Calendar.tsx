import { useEffect, useState } from 'react';
import { useCalendarStore } from '../store/calendarStore';
import { getWeekEnd, getWeekIdFromDate } from '../utils/dateHelpers';
import CalendarHeader from './CalendarHeader';
import WeekView from './WeekView';
import RevertButton from './RevertButton';

interface CalendarProps {
  onToggleChat?: () => void;
  isChatOpen?: boolean;
  className?: string;
  selectedTaskId: string | null;
  onTaskClick: (taskId: string) => void;
}

export default function Calendar({
  onToggleChat,
  isChatOpen,
  className = '',
  selectedTaskId,
  onTaskClick
}: CalendarProps) {
  const {
    currentWeekStart,
    tasks,
    isLoading,
    error,
    loadWeekEvents,
    highlightedTaskIds,
    hasPendingChanges,
    revertChanges
  } = useCalendarStore();

  const [isVisible, setIsVisible] = useState(false);

  // Load events from API if tasks are empty (e.g., page refresh, direct navigation)
  useEffect(() => {
    if (tasks.length === 0 && !isLoading) {
      console.log('[Calendar] No tasks found, loading events from API...');
      const weekId = getWeekIdFromDate(currentWeekStart);
      loadWeekEvents(weekId);
    }
  }, [currentWeekStart, tasks.length, isLoading, loadWeekEvents]);

  // Trigger animation when loading completes
  useEffect(() => {
    if (!isLoading) {
      const timer = setTimeout(() => {
        setIsVisible(true);
      }, 50);
      return () => clearTimeout(timer);
    } else {
      setIsVisible(false);
    }
  }, [isLoading]);

  const weekEnd = getWeekEnd(currentWeekStart);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-black text-red-500">
        Error: {error}
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full bg-black relative ${className}`}>
      <CalendarHeader
        weekStart={currentWeekStart}
        weekEnd={weekEnd}
        onToggleChat={onToggleChat}
        isChatOpen={isChatOpen}
      />

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center text-[#fcecc9]">
          Loading...
        </div>
      ) : (
        <WeekView
          weekStart={currentWeekStart}
          tasks={tasks}
          selectedTaskId={selectedTaskId}
          onTaskClick={onTaskClick}
          isChatOpen={isChatOpen}
          isVisible={isVisible}
          highlightedTaskIds={highlightedTaskIds}
        />
      )}

      {/* Revert Button - Shows when there are pending changes */}
      {hasPendingChanges && (
        <RevertButton onRevert={revertChanges} />
      )}
    </div>
  );
}

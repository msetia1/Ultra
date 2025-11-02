import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useCalendarStore } from '../store/calendarStore';
import { getWeekEnd } from '../utils/dateHelpers';
import CalendarHeader from './CalendarHeader';
import WeekView from './WeekView';

interface CalendarProps {
  onToggleChat?: () => void;
  isChatOpen?: boolean;
  className?: string;
}

export default function Calendar({ onToggleChat, isChatOpen, className = '' }: CalendarProps) {
  const {
    currentWeekStart,
    tasks,
    isLoading,
    error,
    loadMockData
  } = useCalendarStore();

  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  // Load mock data on mount
  useEffect(() => {
    loadMockData();
  }, [loadMockData]);

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

  const handleTaskClick = (taskId: string) => {
    setSelectedTaskId(selectedTaskId === taskId ? null : taskId);
  };

  const handleBackdropClick = () => {
    setSelectedTaskId(null);
  };

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
          onTaskClick={handleTaskClick}
          isChatOpen={isChatOpen}
          isVisible={isVisible}
        />
      )}

      {/* Backdrop overlay when a task is selected */}
      <motion.div
        onClick={handleBackdropClick}
        className="absolute inset-0 bg-black pointer-events-none z-40"
        style={{ pointerEvents: selectedTaskId ? 'auto' : 'none' }}
        animate={{ opacity: selectedTaskId ? 0.6 : 0 }}
        transition={{ duration: 0.3 }}
      />
    </div>
  );
}

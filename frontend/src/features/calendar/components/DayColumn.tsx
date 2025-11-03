import { AnimatePresence } from 'framer-motion';
import type { Task } from '../types/calendar.types';
import { getDayInfo } from '../utils/dateHelpers';
import { calculateTaskPosition, calculateTaskHeight, adjustPositionsForMinimumGaps, type EventWithPosition } from '../utils/timeCalculations';
import AnimatedTaskCard from './AnimatedTaskCard';
import { useMemo, useRef, useState, useEffect, useLayoutEffect } from 'react';

interface DayColumnProps {
  date: Date;
  tasks: Task[];
  className?: string;
  selectedTaskId: string | null;
  onTaskClick: (taskId: string) => void;
  isChatOpen?: boolean;
  isVisible: boolean;
  index: number;
  highlightedTaskIds: Set<string>;
}

export default function DayColumn({
  date,
  tasks,
  className = '',
  selectedTaskId,
  onTaskClick,
  isChatOpen,
  isVisible,
  index,
  highlightedTaskIds
}: DayColumnProps) {
  const { name, number } = getDayInfo(date);

  // Ref to measure container height for gap calculations
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerHeight, setContainerHeight] = useState(800); // Default fallback

  // Measure container height on mount and window resize
  // Using useLayoutEffect for earlier measurement before paint
  useLayoutEffect(() => {
    const updateHeight = () => {
      if (containerRef.current) {
        const height = containerRef.current.offsetHeight;
        console.log(`[DayColumn ${getDayInfo(date).name}] Container height measured:`, height + 'px');
        setContainerHeight(height);
      } else {
        console.warn(`[DayColumn ${getDayInfo(date).name}] containerRef not attached yet`);
      }
    };

    // Immediate measurement
    updateHeight();

    // Also measure after a brief delay to ensure flex layout is complete
    const timeoutId = setTimeout(() => {
      updateHeight();
    }, 50);

    window.addEventListener('resize', updateHeight);
    return () => {
      window.removeEventListener('resize', updateHeight);
      clearTimeout(timeoutId);
    };
  }, [date]);

  // Calculate adjusted positions with minimum gaps
  const adjustedPositions = useMemo(() => {
    console.log(`[DayColumn ${name}] Calculating adjusted positions for ${tasks.length} tasks`);

    const eventsWithPositions: EventWithPosition[] = tasks.map(task => ({
      id: task.id,
      startTime: task.startTime,
      endTime: task.endTime,
      topPercent: calculateTaskPosition(task.startTime),
      heightPercent: calculateTaskHeight(task.startTime, task.endTime),
    }));

    const adjusted = adjustPositionsForMinimumGaps(eventsWithPositions, containerHeight);

    console.log(`[DayColumn ${name}] Adjusted positions:`, {
      containerHeight,
      adjustedCount: adjusted.size,
      sample: Array.from(adjusted.entries()).slice(0, 3).map(([id, pos]) => ({
        id: id.substring(0, 8),
        adjustedTop: pos.toFixed(2) + '%'
      }))
    });

    return adjusted;
  }, [tasks, containerHeight, name]);

  return (
    <div
      className={`
        bg-black border-r border-[#252525]
        flex flex-col
        ${className}
      `}
      style={{
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? 'translateY(0)' : 'translateY(20px)',
        transition: `opacity 600ms ease-out ${index * 100}ms, transform 600ms ease-out ${index * 100}ms`,
      }}
    >
      {/* Day Header */}
      <div className="bg-black border-b border-[#252525] px-4 pt-4 pb-px flex flex-col" style={{ paddingTop: '16px', paddingLeft: '16px', paddingRight: '16px', paddingBottom: '1px' }}>
        <div className="flex items-center justify-between h-[24px]" style={{ height: '24px' }}>
          {/* Day Name */}
          <div className="font-inter font-normal text-[16px] leading-[24px] tracking-[-0.3125px] text-[#f7f9f7]">
            {name}
          </div>

          {/* Day Number */}
          <div className="font-inter font-normal text-[16px] leading-[24px] tracking-[-0.3125px] text-[#f7f9f7]">
            {number}
          </div>
        </div>
        {/* Spacer */}
        <div className="h-[20px] w-full shrink-0" style={{ height: '20px' }} />
      </div>

      {/* Tasks Container - Positioned based on time */}
      <div ref={containerRef} className="flex-1 relative px-4">
        <AnimatePresence mode="popLayout">
          {tasks.map((task) => {
            // Use adjusted position with minimum gap enforcement, fallback to calculated if not found
            const topPosition = adjustedPositions.get(task.id) ?? calculateTaskPosition(task.startTime);
            const height = calculateTaskHeight(task.startTime, task.endTime);

            return (
              <AnimatedTaskCard
                key={task.id}
                task={task}
                isSelected={selectedTaskId === task.id}
                onClick={() => onTaskClick(task.id)}
                isChatOpen={isChatOpen}
                isHighlighted={highlightedTaskIds.has(task.id)}
                style={{
                  top: `${topPosition}%`,
                  height: `${height}%`,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  width: '90%',
                }}
              />
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}

import type { Task } from '../types/calendar.types';
import { getDayInfo } from '../utils/dateHelpers';
import { calculateTaskPosition, calculateTaskHeight } from '../utils/timeCalculations';
import AnimatedTaskCard from './AnimatedTaskCard';

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
      <div className="flex-1 relative px-4">
        {tasks.map((task) => {
          const topPosition = calculateTaskPosition(task.startTime);
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
              }}
            />
          );
        })}
      </div>
    </div>
  );
}

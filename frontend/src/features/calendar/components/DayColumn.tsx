import type { Task } from '../types/calendar.types';
import { getDayInfo } from '../utils/dateHelpers';
import TaskCard from './TaskCard';

interface DayColumnProps {
  date: Date;
  tasks: Task[];
  className?: string;
}

export default function DayColumn({ date, tasks, className = '' }: DayColumnProps) {
  const { name, number } = getDayInfo(date);

  return (
    <div
      className={`
        bg-black border-r border-[#606060]
        flex flex-col relative
        ${className}
      `}
    >
      {/* Day Header */}
      <div className="bg-black border-b border-[#606060] px-4 py-4 flex flex-col gap-1">
        <div className="flex items-center justify-between">
          {/* Day Name */}
          <div className="text-[#f7f9f7] text-base font-normal leading-6 tracking-[-0.3125px]">
            {name}
          </div>

          {/* Day Number */}
          <div className="text-[#f7f9f7] text-base font-normal leading-6 tracking-[-0.3125px]">
            {number}
          </div>
        </div>
      </div>

      {/* Tasks Container */}
      <div className="flex-1 relative p-4 space-y-4">
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} />
        ))}
      </div>
    </div>
  );
}

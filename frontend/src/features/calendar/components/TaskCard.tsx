import type { Task } from '../types/calendar.types';
import { formatTime } from '../utils/timeCalculations';

interface TaskCardProps {
  task: Task;
  className?: string;
}

export default function TaskCard({ task, className = '' }: TaskCardProps) {
  return (
    <div
      className={`
        bg-[#f7f9f7] border border-gray-100 rounded-[10px]
        px-3 py-2 flex flex-col gap-1
        ${className}
      `}
    >
      {/* Title */}
      <h3 className="text-neutral-950 text-base font-normal leading-6 tracking-[-0.3125px]">
        {task.title}
      </h3>

      {/* Description */}
      <p className="text-[#6a7282] text-xs font-normal leading-5 tracking-[-0.1504px] whitespace-pre-wrap">
        {task.description}
      </p>

      {/* Start Time */}
      <p className="text-[#6a7282] text-sm font-normal leading-5 tracking-[-0.1504px] text-center">
        {formatTime(task.startTime)}
      </p>

      {/* Time Separator Line */}
      <div className="flex items-center justify-center">
        <div className="w-[53px] h-0 border-t border-gray-300" />
      </div>

      {/* End Time */}
      <p className="text-[#6a7282] text-sm font-normal leading-5 tracking-[-0.1504px] text-center">
        {formatTime(task.endTime)}
      </p>
    </div>
  );
}

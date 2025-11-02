import { useState } from 'react';
import type { Task } from '../types/calendar.types';
import { formatTime } from '../utils/timeCalculations';
import { cn } from '@/lib/utils';

interface AnimatedTaskCardProps {
  task: Task;
  isSelected: boolean;
  onClick: () => void;
  style?: React.CSSProperties;
  isChatOpen?: boolean;
}

export default function AnimatedTaskCard({
  task,
  isSelected,
  onClick,
  style,
  isChatOpen
}: AnimatedTaskCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  // Extract transform from parent style for proper hover handling
  const parentTransform = style?.transform || '';

  return (
    <div
      onClick={(e) => {
        console.log('[AnimatedTaskCard] Clicked! isSelected:', isSelected, 'taskId:', task.id);
        e.stopPropagation();
        if (!isSelected) {
          console.log('[AnimatedTaskCard] Opening card, calling onClick');
          onClick();
        } else {
          console.log('[AnimatedTaskCard] Card already selected, ignoring click');
        }
      }}
      onMouseEnter={() => !isSelected && setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={cn(
        "group relative cursor-pointer rounded-[10px] overflow-hidden transition-all duration-300",
        "border border-white/10 bg-black",
        "flex flex-col",
        isSelected
          ? "fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[500px] min-h-[450px] px-6 py-6"
          : `absolute w-[90%] ${isChatOpen ? 'max-w-[100px]' : 'max-w-[120px]'} px-[14px] pt-[6px] pb-[14px]`
      )}
      style={!isSelected ? {
        ...style,
        backgroundColor: 'black',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        transform: isHovered ? `${parentTransform} translateY(-2px)` : parentTransform,
        boxShadow: isHovered ? '0 2px 12px rgba(255, 255, 255, 0.03)' : 'none',
      } : {
        backgroundColor: 'black',
        borderColor: 'rgba(255, 255, 255, 0.1)',
      }}
    >
      {/* Radial gradient dot pattern background - visible on hover when not selected */}
      {!isSelected && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            right: 0,
            bottom: 0,
            left: 0,
            opacity: isHovered ? 1 : 0,
            transition: 'opacity 300ms',
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 0,
              right: 0,
              bottom: 0,
              left: 0,
              background: 'radial-gradient(circle at center, rgba(255, 255, 255, 0.5) 1px, transparent 1px)',
              backgroundSize: '4px 4px',
            }}
          />
        </div>
      )}

      {/* Content */}
      <div className="relative flex flex-col">
        {/* Time Window - Top Left (only show when expanded) */}
        {isSelected && (
          <div
            className="text-[11px] text-gray-400 font-inter font-normal tracking-tight mb-6"
            style={{ color: 'rgb(156, 163, 175)', paddingLeft: '12px', paddingTop: '12px' }}
          >
            {formatTime(task.startTime)} - {formatTime(task.endTime)}
          </div>
        )}
        {/* Time Window - Top Right Corner (only show when not expanded) */}
        {!isSelected && (
          <div
            className="absolute top-1 right-1 text-[7px] text-gray-400 font-inter font-normal tracking-tight text-right whitespace-nowrap"
            style={{ color: 'rgb(156, 163, 175)' }}
          >
            {formatTime(task.startTime)} - {formatTime(task.endTime)}
          </div>
        )}

        {/* Title */}
        <h3
          className="font-inter font-medium text-[16px] tracking-[-0.3125px] text-gray-100 m-0 mb-[2px]"
          style={{
            color: 'rgb(243, 244, 246)',
            paddingLeft: isSelected ? '12px' : '0'
          }}
        >
          {task.title}
        </h3>

        {/* Description */}
        <p
          className="font-inter font-normal text-[12px] leading-[16px] tracking-[-0.15px] text-gray-300 m-0 mb-[8px]"
          style={{
            color: 'rgb(209, 213, 219)',
            paddingLeft: isSelected ? '12px' : '0'
          }}
        >
          {task.description}
        </p>

        {/* Start Time - only show when not expanded */}
        {!isSelected && (
          <p
            className="font-inter font-normal text-[14px] leading-[20px] tracking-[-0.1504px] text-center text-gray-300 mb-[8px]"
            style={{ color: 'rgb(209, 213, 219)' }}
          >
            {formatTime(task.startTime)}
          </p>
        )}

        {/* Time Separator Line - only show when not expanded */}
        {!isSelected && (
          <div className="flex items-center justify-center mb-[8px]">
            <div className="w-[53px] h-0 border-t border-white/30" />
          </div>
        )}

        {/* End Time - only show when not expanded */}
        {!isSelected && (
          <p
            className="font-inter font-normal text-[14px] leading-[20px] tracking-[-0.1504px] text-center text-gray-300"
            style={{ color: 'rgb(209, 213, 219)' }}
          >
            {formatTime(task.endTime)}
          </p>
        )}
      </div>

      {/* Expanded content - only show when selected */}
      {isSelected && (
        <div className="mt-4">
          <p className="text-gray-300 text-sm text-center">
            Additional task details can go here...
          </p>
        </div>
      )}

      {/* Gradient border effect - visible on hover when not selected */}
      {!isSelected && (
        <div className="absolute inset-0 -z-10 rounded-[10px] p-px bg-gradient-to-br from-transparent via-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      )}
    </div>
  );
}

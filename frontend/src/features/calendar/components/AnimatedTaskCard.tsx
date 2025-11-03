import { useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import type { Task } from '../types/calendar.types';
import { formatTime } from '../utils/timeCalculations';
import { cn } from '@/lib/utils';

interface AnimatedTaskCardProps {
  task: Task;
  isSelected: boolean;
  onClick: () => void;
  style?: React.CSSProperties;
  isChatOpen?: boolean;
  isHighlighted?: boolean;
}

export default function AnimatedTaskCard({
  task,
  isSelected,
  onClick,
  style,
  isChatOpen,
  isHighlighted = false
}: AnimatedTaskCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  // Extract translateX from style.transform for framer-motion compatibility
  const extractTranslateX = (transformString?: string): string => {
    if (!transformString) return '-50%';
    const match = transformString.match(/translateX\(([^)]+)\)/);
    return match ? match[1] : '-50%';
  };

  // Animation variants for smooth enter/exit/edit
  const cardVariants = {
    initial: {
      opacity: 0,
      scale: 0.95,
    },
    animate: {
      opacity: 1,
      scale: 1,
      transition: {
        duration: 0.4,
        ease: "easeOut"
      }
    },
    exit: {
      opacity: 0,
      scale: 0.95,
      transition: {
        duration: 0.3,
        ease: "easeIn"
      }
    }
  };

  // Render expanded card content
  const expandedCardContent = (
    <motion.div
      key={`expanded-${task.id}`}
      onClick={(e) => {
        console.log('[AnimatedTaskCard] Clicked! isSelected:', isSelected, 'taskId:', task.id);
        e.stopPropagation();
        console.log('[AnimatedTaskCard] Card already selected, ignoring click');
      }}
      className={cn(
        "group cursor-pointer rounded-[10px] overflow-hidden",
        "border border-white/10 bg-black",
        "flex flex-col",
        "fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] min-h-[450px] px-6 py-6"
      )}
      style={{
        position: 'fixed',
        zIndex: 9999,
        backgroundColor: 'black',
        borderColor: 'rgba(255, 255, 255, 0.1)',
      }}
      initial={{ scale: 0.5, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0.5, opacity: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
    >
      {/* Content */}
      <div className="relative flex flex-col">
        {/* Time Window - Top Left (only show when expanded) */}
        <div
          className="text-[11px] text-gray-400 font-inter font-normal tracking-tight mb-6"
          style={{ color: 'rgb(156, 163, 175)', paddingLeft: '12px', paddingTop: '12px' }}
        >
          {formatTime(task.startTime)} - {formatTime(task.endTime)}
        </div>

        {/* Title */}
        <h3
          className="font-inter font-medium text-[16px] tracking-[-0.3125px] text-gray-100 m-0 mb-[2px]"
          style={{
            color: 'rgb(243, 244, 246)',
            paddingLeft: '12px'
          }}
        >
          {task.title}
        </h3>

        {/* Description */}
        <p
          className="font-inter font-normal text-[12px] leading-[16px] tracking-[-0.15px] text-gray-300 m-0 mb-[8px]"
          style={{
            color: 'rgb(209, 213, 219)',
            paddingLeft: '12px'
          }}
        >
          {task.description}
        </p>
      </div>

      {/* Expanded content */}
      <div className="mt-4">
        <p className="text-gray-300 text-sm text-center">
          Additional task details can go here...
        </p>
      </div>
    </motion.div>
  );

  return (
    <>
    <motion.div
      variants={cardVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      onClick={(e) => {
        console.log('[AnimatedTaskCard] Clicked! isSelected:', isSelected, 'taskId:', task.id);
        e.stopPropagation();
        if (!isSelected) {
          console.log('[AnimatedTaskCard] Opening card, calling onClick');
          onClick();
        }
      }}
      onMouseEnter={() => !isSelected && setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={cn(
        "group relative cursor-pointer rounded-[10px] overflow-hidden",
        "border border-white/10 bg-black",
        "flex flex-col",
        `absolute ${isChatOpen ? 'max-w-[100px]' : 'max-w-[120px]'} px-[14px] pt-[6px] pb-[14px]`,
        isSelected && "invisible"
      )}
      style={{
        // Spread only positioning props, not transform
        top: style?.top,
        height: style?.height,
        left: style?.left,
        // Use framer-motion's composable transform props
        x: extractTranslateX(style?.transform as string),  // Extract from transform string
        y: isHovered ? -2 : 0,  // Replaces translateY(-2px) on hover
        backgroundColor: 'black',
        borderColor: isHighlighted ? 'rgba(252, 236, 201, 0.8)' : 'rgba(255, 255, 255, 0.1)',
        boxShadow: isHighlighted
          ? '0 0 20px rgba(252, 236, 201, 0.5), 0 0 40px rgba(252, 236, 201, 0.3), 0 0 60px rgba(252, 236, 201, 0.1)'
          : isHovered
            ? '0 2px 12px rgba(255, 255, 255, 0.03)'
            : 'none',
        animation: isHighlighted ? 'pulse-glow 2s ease-in-out infinite' : 'none',
        transition: 'box-shadow 0.4s ease, border-color 0.4s ease',
        // Ensure width from style prop is respected, with fallback
        width: style?.width || '90%',
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
    </motion.div>
    {/* Render expanded card via portal to escape stacking context */}
    {createPortal(
      <AnimatePresence>
        {isSelected && expandedCardContent}
      </AnimatePresence>,
      document.body
    )}
    </>
  );
}

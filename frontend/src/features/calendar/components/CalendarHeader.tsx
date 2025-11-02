import { formatDateRange } from '../utils/dateHelpers';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface CalendarHeaderProps {
  weekStart: Date;
  weekEnd: Date;
  onPreviousWeek: () => void;
  onNextWeek: () => void;
  onToggleChat?: () => void;
  className?: string;
}

export default function CalendarHeader({
  weekStart,
  weekEnd,
  onPreviousWeek,
  onNextWeek,
  onToggleChat,
  className = ''
}: CalendarHeaderProps) {
  return (
    <div
      className={`
        bg-black border-b border-[#606060]
        h-[81px] flex items-center justify-between px-6
        ${className}
      `}
    >
      {/* Logo Section */}
      <div className="flex items-center gap-3">
        {/* Icon/Logo placeholder - you can replace with actual logo */}
        <div className="text-[#fcecc9] text-xl italic font-['Turbo_Driver'] select-none">
          ltra
        </div>
      </div>

      {/* Date Range & Navigation */}
      <div className="flex items-center gap-4">
        <button
          onClick={onPreviousWeek}
          className="text-[#fcecc9] hover:text-white transition-colors p-1"
          aria-label="Previous week"
        >
          <ChevronLeft size={24} />
        </button>

        <div className="text-[#fcecc9] text-2xl font-medium tracking-[0.0703px]">
          {formatDateRange(weekStart, weekEnd)}
        </div>

        <button
          onClick={onNextWeek}
          className="text-[#fcecc9] hover:text-white transition-colors p-1"
          aria-label="Next week"
        >
          <ChevronRight size={24} />
        </button>
      </div>

      {/* Right Section - Chat Toggle (optional) */}
      {onToggleChat && (
        <button
          onClick={onToggleChat}
          className="text-[#888888] hover:text-[#fcecc9] transition-colors text-2xl font-medium"
          aria-label="Toggle chat"
        >
          ☰
        </button>
      )}
    </div>
  );
}

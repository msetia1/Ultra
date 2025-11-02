import { formatDateRange } from '../utils/dateHelpers';
import ChatIcon from './ChatIcon';

interface CalendarHeaderProps {
  weekStart: Date;
  weekEnd: Date;
  onToggleChat?: () => void;
  isChatOpen?: boolean;
  className?: string;
}

export default function CalendarHeader({
  weekStart,
  weekEnd,
  onToggleChat,
  isChatOpen = false,
  className = ''
}: CalendarHeaderProps) {
  return (
    <div
      className={`
        bg-black border-b border-[#252525]
        h-[81px] flex items-center justify-between pl-[24px] pr-[26px]
        ${className}
      `}
    >
      {/* Logo Section */}
      <div className="flex items-center gap-3">
        {/* Ultra Logo */}
        <img
          src="/icons/UltraLogo.png"
          alt="Ultra Logo"
          className="h-[43px] rounded-[10px]"
        />
      </div>

      {/* Date Range - Centered */}
      <div className="font-inter font-medium text-[20px] leading-[30px] tracking-[0.0703px]" style={{ color: '#ffffff' }}>
        {formatDateRange(weekStart, weekEnd)}
      </div>

      {/* Right Section - Chat Toggle */}
      {onToggleChat && (
        <div style={{ visibility: isChatOpen ? 'hidden' : 'visible' }}>
          <button
            onClick={onToggleChat}
            className="bg-transparent border-none p-0 outline-none text-[#888888] hover:text-[#fcecc9] transition-colors cursor-pointer"
            aria-label="Toggle chat"
          >
            <ChatIcon />
          </button>
        </div>
      )}
    </div>
  );
}

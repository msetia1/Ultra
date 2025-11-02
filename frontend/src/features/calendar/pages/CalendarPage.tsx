import { Calendar } from '../components';
import { ChatPanel } from '@/features/chat/components';
import { useChatStore } from '@/features/chat/store/chatStore';

export default function CalendarPage() {
  console.log('[CalendarPage] Component rendering');
  const { toggleChat, isOpen } = useChatStore();
  console.log('[CalendarPage] Chat isOpen state:', isOpen);

  return (
    <div className="fixed inset-0 w-full h-full bg-black">
      {/* Main Calendar View */}
      <div
        className={`
          h-full overflow-hidden transition-all duration-300 ease-in-out
          ${isOpen ? 'mr-[418px]' : 'mr-0'}
        `}
      >
        <Calendar onToggleChat={toggleChat} isChatOpen={isOpen} />
      </div>

      {/* Chat Panel (Collapsible) */}
      {console.log('[CalendarPage] About to render ChatPanel')}
      <ChatPanel />
    </div>
  );
}

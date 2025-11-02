import { Calendar } from '../components';
import { ChatPanel } from '@/features/chat/components';
import { useChatStore } from '@/features/chat/store/chatStore';

export default function CalendarPage() {
  const { toggleChat, isOpen } = useChatStore();

  return (
    <div className="fixed inset-0 w-full h-full bg-black overflow-hidden">
      {/* Main Calendar View */}
      <div
        className={`
          h-full transition-all duration-300 ease-in-out
          ${isOpen ? 'mr-[418px]' : 'mr-0'}
        `}
      >
        <Calendar onToggleChat={toggleChat} isChatOpen={isOpen} />
      </div>

      {/* Chat Panel (Collapsible) */}
      <ChatPanel />
    </div>
  );
}

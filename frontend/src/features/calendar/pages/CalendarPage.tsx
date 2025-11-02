import { useState } from 'react';
import { Calendar } from '../components';
import { ChatPanel } from '@/features/chat/components';
import { useChatStore } from '@/features/chat/store/chatStore';

export default function CalendarPage() {
  console.log('[CalendarPage] Component rendering');
  const { toggleChat, isOpen } = useChatStore();
  console.log('[CalendarPage] Chat isOpen state:', isOpen);

  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  const handleTaskClick = (taskId: string) => {
    console.log('[CalendarPage] handleTaskClick called with taskId:', taskId);
    console.log('[CalendarPage] Current selectedTaskId:', selectedTaskId);
    const newValue = selectedTaskId === taskId ? null : taskId;
    console.log('[CalendarPage] Setting selectedTaskId to:', newValue);
    setSelectedTaskId(newValue);
  };

  const handleBackdropClick = () => {
    console.log('[CalendarPage] handleBackdropClick called!');
    console.log('[CalendarPage] Closing card, setting selectedTaskId to null');
    setSelectedTaskId(null);
  };

  return (
    <div className="fixed inset-0 w-full h-full bg-black">
      {/* Main Calendar View */}
      <div
        className={`
          h-full overflow-hidden transition-all duration-300 ease-in-out
          ${isOpen ? 'mr-[418px]' : 'mr-0'}
        `}
      >
        <Calendar
          onToggleChat={toggleChat}
          isChatOpen={isOpen}
          selectedTaskId={selectedTaskId}
          onTaskClick={handleTaskClick}
        />
      </div>

      {/* Chat Panel (Collapsible) */}
      <ChatPanel />

      {/* Backdrop overlay when a task is selected - OUTSIDE overflow container */}
      {selectedTaskId && (
        <div
          onClick={(e) => {
            console.log('[CalendarPage] Backdrop clicked!', e.target);
            handleBackdropClick();
          }}
          className="fixed z-40"
          style={{
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(8px)',
            cursor: 'pointer',
          }}
          data-backdrop="true"
        />
      )}
      {console.log('[CalendarPage] Rendering - selectedTaskId:', selectedTaskId, 'Backdrop should render:', !!selectedTaskId)}
    </div>
  );
}

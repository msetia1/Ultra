import { useChatStore } from '../store/chatStore';
import { X } from 'lucide-react';

export default function ChatPanel() {
  const { isOpen, closeChat } = useChatStore();

  if (!isOpen) return null;

  return (
    <div
      className={`
        fixed right-0 top-0 h-full w-[418px] bg-black border-l border-[#606060]
        transform transition-transform duration-300 ease-in-out z-50
        ${isOpen ? 'translate-x-0' : 'translate-x-full'}
      `}
    >
      {/* Chat Header */}
      <div className="relative p-6">
        <button
          onClick={closeChat}
          className="text-[#888888] hover:text-[#fcecc9] transition-colors text-2xl font-medium"
          aria-label="Close chat"
        >
          <X size={24} />
        </button>
      </div>

      {/* Chat Content */}
      <div className="px-6 py-4">
        <div className="text-[#fcecc9] text-lg">
          Chat Panel
        </div>
        <div className="text-[#888888] text-sm mt-2">
          Chat functionality coming soon...
        </div>
      </div>
    </div>
  );
}

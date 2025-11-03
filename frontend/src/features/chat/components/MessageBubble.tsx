import type { Message } from '../types/chat.types';

interface MessageBubbleProps {
  message: Message;
  isLatest?: boolean;
  showRevertButton?: boolean;
  onRevert?: () => void;
}

export default function MessageBubble({
  message,
  isLatest = false,
  showRevertButton = false,
  onRevert
}: MessageBubbleProps) {
  const isUser = message.sender === 'user';

  console.log('[MessageBubble] Rendering message - isUser:', isUser, 'showRevertButton:', showRevertButton, 'onRevert exists:', !!onRevert);

  const shouldRenderButton = isUser && showRevertButton && onRevert;
  console.log('[MessageBubble] shouldRenderButton:', shouldRenderButton);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        marginBottom: '12px',
        width: '100%',
      }}
    >
      <div
        style={{
          maxWidth: '80%',
          backgroundColor: isUser ? '#000000' : 'transparent',
          border: isUser ? '2px solid #252525' : 'none',
          color: '#ffffff',
          borderRadius: isUser ? '12px' : '0',
          padding: '12px 16px',
          wordWrap: 'break-word',
          overflowWrap: 'break-word',
        }}
      >
        <div
          style={{
            fontSize: '15px',
            lineHeight: '1.5',
            whiteSpace: 'pre-wrap',
          }}
        >
          {message.content}
        </div>
      </div>

      {/* Show revert button below user message */}
      {isUser && showRevertButton && onRevert && (
        <button
          onClick={onRevert}
          className="text-[#888888] hover:text-[#fcecc9] transition-colors duration-200 cursor-pointer"
          aria-label="Revert changes"
          style={{
            marginTop: '8px',
            background: 'none',
            border: 'none',
            padding: 0,
          }}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 14 4 9l5-5"/>
            <path d="M20 20v-7a4 4 0 0 0-4-4H4"/>
          </svg>
        </button>
      )}
    </div>
  );
}

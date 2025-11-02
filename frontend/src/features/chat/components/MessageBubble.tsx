import type { Message } from '../types/chat.types';

interface MessageBubbleProps {
  message: Message;
  isLatest?: boolean;
}

export default function MessageBubble({ message, isLatest = false }: MessageBubbleProps) {
  const isUser = message.sender === 'user';

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
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
    </div>
  );
}

import { useEffect, useRef } from 'react';
import type { Message } from '../types/chat.types';
import MessageBubble from './MessageBubble';
import StreamingMessage from './StreamingMessage';

interface MessageListProps {
  messages: Message[];
  streamingMessage?: string;
  isStreaming?: boolean;
  error?: string | null;
  showRevertButton?: boolean;
  onRevert?: () => void;
}

export default function MessageList({
  messages,
  streamingMessage = '',
  isStreaming = false,
  error = null,
  showRevertButton = false,
  onRevert,
}: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  console.log('[MessageList] Render - showRevertButton:', showRevertButton);
  console.log('[MessageList] messages count:', messages.length);
  console.log('[MessageList] messages:', messages.map(m => ({ sender: m.sender, id: m.id })));

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage]);

  return (
    <div
      className="flex-1 overflow-y-auto space-y-4 scrollbar-hide"
      style={{
        backgroundColor: '#000000',
        paddingLeft: '24px',
        paddingRight: '16px',
        paddingTop: '24px',
        paddingBottom: '24px',
      }}
    >
      {/* Error message */}
      {error && (
        <div
          style={{
            backgroundColor: '#3d1a1a',
            border: '1px solid #7d2d2d',
            borderRadius: '8px',
            padding: '12px 16px',
            color: '#ff6b6b',
            fontSize: '14px',
          }}
        >
          {error}
        </div>
      )}

      {/* Message list */}
      {messages.map((message, index) => {
        // Find the index of the last user message
        const lastUserMessageIndex = messages.map((m, i) => m.sender === 'user' ? i : -1)
          .filter(i => i !== -1)
          .pop() ?? -1;

        const isLastUserMessage = message.sender === 'user' && index === lastUserMessageIndex;
        const shouldShowRevert = isLastUserMessage && showRevertButton;

        console.log('[MessageList] Message', index, '- sender:', message.sender, 'isLastUserMessage:', isLastUserMessage, 'lastUserMessageIndex:', lastUserMessageIndex, 'shouldShowRevert:', shouldShowRevert);

        return (
          <MessageBubble
            key={message.id}
            message={message}
            isLatest={index === messages.length - 1}
            showRevertButton={shouldShowRevert}
            onRevert={onRevert}
          />
        );
      })}

      {/* Streaming message */}
      {(streamingMessage || isStreaming) && (
        <StreamingMessage content={streamingMessage} isStreaming={isStreaming} />
      )}

      {/* Scroll anchor */}
      <div ref={messagesEndRef} />
    </div>
  );
}

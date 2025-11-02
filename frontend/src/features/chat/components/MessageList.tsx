import { useEffect, useRef } from 'react';
import type { Message } from '../types/chat.types';
import MessageBubble from './MessageBubble';
import StreamingMessage from './StreamingMessage';

interface MessageListProps {
  messages: Message[];
  streamingMessage?: string;
  isStreaming?: boolean;
  error?: string | null;
}

export default function MessageList({
  messages,
  streamingMessage = '',
  isStreaming = false,
  error = null,
}: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage]);

  return (
    <div
      className="flex-1 overflow-y-auto space-y-4"
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
      {messages.map((message, index) => (
        <MessageBubble
          key={message.id}
          message={message}
          isLatest={index === messages.length - 1}
        />
      ))}

      {/* Streaming message */}
      {(streamingMessage || isStreaming) && (
        <StreamingMessage content={streamingMessage} isStreaming={isStreaming} />
      )}

      {/* Scroll anchor */}
      <div ref={messagesEndRef} />
    </div>
  );
}

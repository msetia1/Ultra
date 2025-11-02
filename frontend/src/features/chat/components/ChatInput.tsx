import { useRef, useEffect } from 'react';
import { ArrowUp, Square } from 'lucide-react';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isLoading?: boolean;
  placeholder?: string;
  maxHeight?: number;
}

export default function ChatInput({
  value,
  onChange,
  onSubmit,
  isLoading = false,
  placeholder = 'Type a message...',
  maxHeight = 240,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea based on content
  useEffect(() => {
    if (!textareaRef.current) return;

    textareaRef.current.style.height = 'auto';
    const newHeight = Math.min(textareaRef.current.scrollHeight, maxHeight);
    textareaRef.current.style.height = `${newHeight}px`;
  }, [value, maxHeight]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !isLoading) {
        onSubmit();
      }
    }
  };

  const handleSubmit = () => {
    if (value.trim() && !isLoading) {
      onSubmit();
    }
  };

  return (
    <div
      style={{
        backgroundColor: '#000000',
        border: '1px solid #252525',
        borderRadius: '24px',
        padding: '8px',
      }}
    >
      {/* Textarea */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={isLoading}
        rows={1}
        style={{
          width: '95%',
          minHeight: '44px',
          maxHeight: `${maxHeight}px`,
          backgroundColor: 'transparent',
          border: 'none',
          outline: 'none',
          resize: 'none',
          color: '#ffffff',
          fontSize: '16px',
          fontFamily: 'inherit',
          lineHeight: '1.5',
          padding: '8px 12px',
          overflow: 'auto',
        }}
        className="placeholder:text-[#888888]"
      />

      {/* Actions */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          gap: '8px',
          paddingTop: '8px',
        }}
      >
        {/* Send Button */}
        <button
          onClick={handleSubmit}
          disabled={isLoading || !value.trim()}
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            backgroundColor: isLoading || !value.trim() ? '#606060' : '#ffffff',
            color: '#000000',
            border: 'none',
            cursor: isLoading || !value.trim() ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'background-color 0.2s',
            opacity: isLoading || !value.trim() ? 0.5 : 1,
          }}
          onMouseEnter={(e) => {
            if (!isLoading && value.trim()) {
              e.currentTarget.style.backgroundColor = '#e6e6e6';
            }
          }}
          onMouseLeave={(e) => {
            if (!isLoading && value.trim()) {
              e.currentTarget.style.backgroundColor = '#ffffff';
            }
          }}
        >
          {isLoading ? (
            <Square size={20} fill="currentColor" />
          ) : (
            <ArrowUp size={20} />
          )}
        </button>
      </div>
    </div>
  );
}

interface StreamingMessageProps {
  content: string;
  isStreaming: boolean;
}

export default function StreamingMessage({ content, isStreaming }: StreamingMessageProps) {
  if (!content && !isStreaming) return null;

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'flex-start',
        marginBottom: '12px',
        width: '100%',
      }}
    >
      <div
        style={{
          maxWidth: '80%',
          backgroundColor: 'transparent',
          color: '#ffffff',
          borderRadius: '0',
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
          {content}
          {isStreaming && (
            <span
              style={{
                display: 'inline-block',
                width: '8px',
                height: '16px',
                backgroundColor: '#ffffff',
                marginLeft: '2px',
                animation: 'blink 1s infinite',
              }}
            />
          )}
        </div>
        {isStreaming && (
          <div
            style={{
              fontSize: '11px',
              color: '#888888',
              marginTop: '6px',
            }}
          >
            AI is typing...
          </div>
        )}
      </div>
      <style>
        {`
          @keyframes blink {
            0%, 49% { opacity: 1; }
            50%, 100% { opacity: 0; }
          }
        `}
      </style>
    </div>
  );
}

import { useEffect, useRef } from 'react';
import OnboardingLogo from './OnboardingLogo';

interface QuestionScreenProps {
  question: string;
  value: string;
  onChange: (value: string) => void;
  onNext: () => void;
  onBack: () => void;
  canGoBack: boolean;
}

export default function QuestionScreen({
  question,
  value,
  onChange,
  onNext,
  onBack,
  canGoBack,
}: QuestionScreenProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus the input when component mounts
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Allow Enter to submit if there's content and Shift isn't held (Shift+Enter for new line)
    if (e.key === 'Enter' && !e.shiftKey && value.trim()) {
      e.preventDefault();
      onNext();
    }
  };

  const canProceed = value.trim().length > 0;

  return (
    <div className="relative w-full h-screen bg-black">
      {/* Logo - top-left */}
      <OnboardingLogo />

      {/* Main content - centered, accounting for button space */}
      <div className="flex items-center justify-center h-full w-full pb-32 md:pb-36 lg:pb-40 px-6 md:px-12 lg:px-24">
        <div className="max-w-[815px]">
          {/* Question */}
          <h1 className="font-['Inter',sans-serif] font-normal text-[#aaaaaa] text-[clamp(24px,5vw,30px)] leading-[1.2] mb-16 md:mb-20 lg:mb-24">
            {question}
          </h1>

          {/* Input area with underline */}
          <div className="relative">
            <textarea
              ref={inputRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your answer here"
              className="
                w-full
                bg-transparent
                border-none
                outline-none
                resize-none
                font-['Inter',sans-serif]
                text-[clamp(20px,4vw,28px)]
                text-[#aaaaaa]
                placeholder:text-[rgba(170,170,170,0.4)]
                pb-4
                min-h-[60px]
                overflow-hidden
              "
              rows={1}
              style={{
                fieldSizing: 'content',
              } as React.CSSProperties}
            />
            {/* Underline */}
            <div className="absolute bottom-0 left-0 right-0 h-[1px] bg-[#aaaaaa]" />
          </div>
        </div>
      </div>

      {/* Buttons - bottom center */}
      <div className="absolute bottom-12 md:bottom-16 lg:bottom-20 left-1/2 -translate-x-1/2 flex gap-4 md:gap-6">
        {/* Back button */}
        <button
          onClick={onBack}
          disabled={!canGoBack}
          className="
            w-[110px] md:w-[125px]
            h-[44px] md:h-[52px]
            rounded-lg
            border border-[#aaaaaa]
            font-['Inter',sans-serif]
            text-[18px] md:text-[20px]
            text-[#aaaaaa]
            transition-all
            duration-200
            disabled:opacity-30
            disabled:cursor-not-allowed
            hover:bg-[#aaaaaa]/10
            active:bg-[#aaaaaa]/20
          "
        >
          Back
        </button>

        {/* Next button */}
        <button
          onClick={onNext}
          disabled={!canProceed}
          className="
            w-[110px] md:w-[125px]
            h-[44px] md:h-[52px]
            rounded-lg
            bg-[#aaaaaa]
            font-['Inter',sans-serif]
            text-[18px] md:text-[20px]
            text-black
            transition-all
            duration-200
            disabled:opacity-30
            disabled:cursor-not-allowed
            hover:bg-white
            active:bg-[#cccccc]
          "
        >
          Next
        </button>
      </div>
    </div>
  );
}

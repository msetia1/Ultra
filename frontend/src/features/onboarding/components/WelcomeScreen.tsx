import { useState, useEffect, useCallback } from 'react';
import OnboardingLogo from './OnboardingLogo';
import { ResponseStream } from '@/components/ui/response-stream';

interface WelcomeScreenProps {
  lines: string[];
  isItalic?: boolean;
  onComplete?: () => void;
}

export default function WelcomeScreen({ lines, isItalic = false, onComplete }: WelcomeScreenProps) {
  const [currentLineIndex, setCurrentLineIndex] = useState(0);
  const [completedLines, setCompletedLines] = useState<number[]>([]);

  const handleLineComplete = useCallback((lineIndex: number) => {
    setCompletedLines(prev => {
      if (prev.includes(lineIndex)) return prev;
      return [...prev, lineIndex];
    });
  }, []);

  useEffect(() => {
    // When a line completes, move to next line after a brief delay
    if (completedLines.length === currentLineIndex + 1 && currentLineIndex < lines.length - 1) {
      const timer = setTimeout(() => {
        setCurrentLineIndex(prev => prev + 1);
      }, 400); // Small delay between lines
      return () => clearTimeout(timer);
    }

    // When all lines are complete, call onComplete after a delay
    if (completedLines.length === lines.length) {
      const timer = setTimeout(() => {
        onComplete?.();
      }, 1500); // Pause before moving to next screen
      return () => clearTimeout(timer);
    }
  }, [completedLines, currentLineIndex, lines.length, onComplete]);

  return (
    <div
      className="relative w-full h-screen"
      style={{ backgroundColor: '#000000' }}
    >
      {/* Logo - absolutely positioned top-left */}
      <OnboardingLogo />

      {/* Text - centered container with left-aligned text */}
      <div className="flex items-center justify-center h-full w-full">
        <div className="text-left">
          {lines.map((line, index) => (
            <div
              key={index}
              className={`
                font-['Inter',sans-serif]
                text-[#aaaaaa]
                text-[36px]
                leading-[36px]
                tracking-[-0.3125px]
                ${isItalic ? 'font-light italic' : 'font-normal'}
              `}
            >
              {index <= currentLineIndex && (
                <ResponseStream
                  textStream={line}
                  mode="fade"
                  speed={75}
                  fadeDuration={500}
                  segmentDelay={50}
                  onComplete={() => handleLineComplete(index)}
                />
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

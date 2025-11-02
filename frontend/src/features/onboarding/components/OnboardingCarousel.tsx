import { useState, useEffect, useCallback } from 'react';
import WelcomeScreen from './WelcomeScreen';
import { welcomeScreens } from '../data/welcomeScreens';
import { useOnboardingStore } from '../store/onboardingStore';

export default function OnboardingCarousel() {
  const [localStep, setLocalStep] = useState(0);
  const { setCurrentStep } = useOnboardingStore();

  const handleNext = useCallback(() => {
    if (localStep < welcomeScreens.length - 1) {
      setLocalStep(localStep + 1);
    } else {
      setCurrentStep(5);
    }
  }, [localStep, setCurrentStep]);

  const handleScreenComplete = useCallback(() => {
    handleNext();
  }, [handleNext]);

  const handleSkip = useCallback((e: React.MouseEvent | KeyboardEvent) => {
    e.preventDefault();
    handleNext();
  }, [handleNext]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowRight') {
      handleSkip(e);
    }
  }, [handleSkip]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const currentScreen = welcomeScreens[localStep];

  return (
    <div
      className="absolute inset-0 w-full h-full cursor-pointer"
      style={{ backgroundColor: '#000000' }}
      onClick={(e) => handleSkip(e)}
    >
      <WelcomeScreen
        key={localStep} // Reset component when step changes
        lines={currentScreen.lines}
        isItalic={currentScreen.isItalic}
        onComplete={handleScreenComplete}
      />

      {/* Progress indicators */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 flex gap-2 pointer-events-none">
        {welcomeScreens.map((_, index) => (
          <div
            key={index}
            className={`
              w-2 h-2 rounded-full transition-colors duration-300
              ${index === localStep ? 'bg-[#aaaaaa]' : 'bg-[#333333]'}
            `}
          />
        ))}
      </div>
    </div>
  );
}

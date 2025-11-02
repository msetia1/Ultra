import { useEffect } from 'react';
import { useOnboardingStore } from '../store/onboardingStore';
import OnboardingCarousel from '../components/OnboardingCarousel';
import QuestionFlow from '../components/QuestionFlow';
import IntegrationsScreen from '../components/IntegrationsScreen';
import LoadingScreen from '../components/LoadingScreen';

export default function Onboarding() {
  const { currentStep } = useOnboardingStore();

  useEffect(() => {
    console.log('[Onboarding] currentStep changed to:', currentStep);
    if (currentStep < 5) console.log('[Onboarding] Rendering: OnboardingCarousel');
    else if (currentStep >= 5 && currentStep < 8) console.log('[Onboarding] Rendering: QuestionFlow');
    else if (currentStep === 8) console.log('[Onboarding] Rendering: IntegrationsScreen');
    else if (currentStep >= 9) console.log('[Onboarding] Rendering: LoadingScreen');
  }, [currentStep]);

  return (
    <div
      className="fixed inset-0 w-full h-full"
      style={{ backgroundColor: '#000000' }}
    >
      {/* Steps 0-4: Welcome carousel screens */}
      {currentStep < 5 && <OnboardingCarousel />}

      {/* Steps 5-7: Question screens */}
      {currentStep >= 5 && currentStep < 8 && <QuestionFlow />}

      {/* Step 8: Integration screen */}
      {currentStep === 8 && <IntegrationsScreen />}

      {/* Step 9: Loading screen */}
      {currentStep >= 9 && <LoadingScreen />}
    </div>
  );
}

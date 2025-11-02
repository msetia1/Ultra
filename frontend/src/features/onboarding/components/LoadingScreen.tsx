import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import UniqueLoading from '@/components/ui/morph-loading';
import OnboardingLogo from './OnboardingLogo';
import { useOnboardingStore } from '../store/onboardingStore';
import { useWeekGeneration } from '@/features/calendar/hooks/useWeekGeneration';
import { getCurrentWeekId, buildGenerationRequest } from '@/features/calendar/utils/generationHelpers';

export default function LoadingScreen() {
  const navigate = useNavigate();
  const { goals, values, projects } = useOnboardingStore();
  const { generateWeek, isComplete, error } = useWeekGeneration();

  useEffect(() => {
    console.log('[LoadingScreen] Component mounted, starting week generation...');

    // Start generation immediately with onboarding data
    const weekId = getCurrentWeekId();
    const request = buildGenerationRequest({ goals, values, projects });

    console.log('[LoadingScreen] Generating week:', weekId);
    console.log('[LoadingScreen] User goals:', request.user_goals);

    generateWeek(weekId, request);
  }, []); // Run once on mount

  useEffect(() => {
    // Navigate when generation completes
    if (isComplete) {
      console.log('[LoadingScreen] Generation complete! Navigating to calendar...');
      navigate('/calendar');
    }
  }, [isComplete, navigate]);

  useEffect(() => {
    // Handle errors - still navigate to calendar after short delay
    if (error) {
      console.error('[LoadingScreen] Generation error:', error);
      console.log('[LoadingScreen] Navigating to calendar anyway after 2s...');

      const timer = setTimeout(() => {
        navigate('/calendar');
      }, 2000);

      return () => clearTimeout(timer);
    }
  }, [error, navigate]);

  return (
    <div className="relative w-full h-screen bg-black overflow-hidden">
      {/* Logo - top-left */}
      <OnboardingLogo />

      {/* Loading animation - centered */}
      <div className="flex items-center justify-center h-screen">
        <UniqueLoading variant="morph" size="lg" className="w-32 h-32" />
      </div>
    </div>
  );
}

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

    let cancelled = false;

    // Start generation immediately with onboarding data
    const weekId = getCurrentWeekId();
    const request = buildGenerationRequest({ goals, values, projects });

    console.log('[LoadingScreen] Generating week:', weekId);
    console.log('[LoadingScreen] User goals:', request.user_goals);

    // Wrap in async IIFE to properly await generateWeek
    (async () => {
      try {
        console.log('[LoadingScreen] 🚀 Calling generateWeek...');
        await generateWeek(weekId, request);

        if (!cancelled) {
          console.log('[LoadingScreen] ✅ generateWeek completed successfully');
        }
      } catch (error) {
        console.error('[LoadingScreen] ❌ generateWeek failed:', error);
        if (!cancelled) {
          // Still navigate on error after short delay
          setTimeout(() => navigate('/calendar'), 2000);
        }
      }
    })();

    return () => {
      cancelled = true;
      console.log('[LoadingScreen] Component unmounting, setting cancelled flag');
    };
  }, [generateWeek, goals, values, projects, navigate]); // Add dependencies

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

  useEffect(() => {
    // Safety timeout: navigate after 60 seconds regardless
    console.log('[LoadingScreen] Setting 60s safety timeout...');

    const safetyTimeout = setTimeout(() => {
      console.warn('[LoadingScreen] ⏰ Safety timeout reached (60s), navigating to calendar...');
      navigate('/calendar');
    }, 60000);

    return () => {
      console.log('[LoadingScreen] Clearing safety timeout');
      clearTimeout(safetyTimeout);
    };
  }, [navigate]);

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

import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import UniqueLoading from '@/components/ui/morph-loading';
import OnboardingLogo from './OnboardingLogo';
import { useOnboardingStore } from '../store/onboardingStore';
import { useWeekGeneration } from '@/features/calendar/hooks/useWeekGeneration';
import { getCurrentWeekId, buildGenerationRequest } from '@/features/calendar/utils/generationHelpers';
import { useCalendarStore } from '@/features/calendar/store/calendarStore';
import { getCurrentWeekStart } from '@/features/calendar/utils/dateHelpers';
import { transformGeneratedEventToTask } from '@/features/calendar/utils/eventTransform';

export default function LoadingScreen() {
  const navigate = useNavigate();
  const { goals, values, projects } = useOnboardingStore();
  const { generateWeek, isComplete, error, events } = useWeekGeneration();
  const { setTasks } = useCalendarStore();

  // Guard to prevent duplicate generation in React StrictMode (development)
  const hasStartedGeneration = useRef(false);

  useEffect(() => {
    console.log('[LoadingScreen] Component mounted, starting week generation...');

    // Prevent duplicate execution in StrictMode double-render
    if (hasStartedGeneration.current) {
      console.log('[LoadingScreen] ⚠️ Generation already started, skipping duplicate request');
      return;
    }

    hasStartedGeneration.current = true;
    console.log('[LoadingScreen] 🔒 Generation guard activated');

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
    // Pre-populate calendar store and navigate when generation completes
    if (isComplete && events.length > 0) {
      console.log('[LoadingScreen] Generation complete! Pre-populating calendar store...');
      console.log('[LoadingScreen] Generated events:', events.length);

      // Transform generated events to tasks
      const weekStart = getCurrentWeekStart();
      const tasks = events.map(event =>
        transformGeneratedEventToTask(event, weekStart)
      );

      console.log('[LoadingScreen] Transformed to', tasks.length, 'tasks');

      // Pre-populate calendar store
      setTasks(tasks);
      console.log('[LoadingScreen] ✅ Calendar store populated, navigating...');

      // Now navigate - calendar will have data ready
      navigate('/calendar');
    } else if (isComplete && events.length === 0) {
      // Generation complete but no events - still navigate
      console.warn('[LoadingScreen] Generation complete but no events generated');
      navigate('/calendar');
    }
  }, [isComplete, events, navigate, setTasks]);

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

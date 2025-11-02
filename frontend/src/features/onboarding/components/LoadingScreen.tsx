import { useEffect } from 'react';
import UniqueLoading from '@/components/ui/morph-loading';
import OnboardingLogo from './OnboardingLogo';

export default function LoadingScreen() {
  useEffect(() => {
    console.log('[LoadingScreen] Component mounted');
  }, []);

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

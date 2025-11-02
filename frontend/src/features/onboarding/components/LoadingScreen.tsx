import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import UniqueLoading from '@/components/ui/morph-loading';
import OnboardingLogo from './OnboardingLogo';

export default function LoadingScreen() {
  const navigate = useNavigate();

  useEffect(() => {
    console.log('[LoadingScreen] Component mounted');

    // Navigate to calendar page after 5 seconds
    const timer = setTimeout(() => {
      console.log('[LoadingScreen] Navigating to calendar...');
      navigate('/calendar');
    }, 5000);

    // Cleanup timer on unmount
    return () => clearTimeout(timer);
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

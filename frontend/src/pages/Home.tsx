import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ONBOARDING_RETURN_KEY } from '@/features/onboarding/api/integrationsApi';

export default function Home() {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const hasIntegrationQuery =
      params.get('whoop') === 'connected' ||
      params.get('github') === 'connected' ||
      params.get('linear') === 'connected' ||
      params.has('error');

    if (hasIntegrationQuery) {
      navigate(`/onboarding${location.search}`, { replace: true });
      return;
    }

    try {
      if (localStorage.getItem(ONBOARDING_RETURN_KEY)) {
        localStorage.removeItem(ONBOARDING_RETURN_KEY);
        navigate('/onboarding', { replace: true });
      }
    } catch {
      // ignore storage errors
    }
  }, [location, navigate]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-4xl font-bold mb-4">AI Scheduler</h1>
      <p className="text-muted-foreground">
        Your TypeScript React frontend is ready!
      </p>
    </div>
  );
}

import OnboardingLogo from './OnboardingLogo';
import IntegrationCard from './IntegrationCard';
import { integrations } from '../data/integrations';
import { useOnboardingStore } from '../store/onboardingStore';

export default function IntegrationsScreen() {
  const {
    connectedIntegrations,
    connectIntegration,
    disconnectIntegration,
    nextStep,
  } = useOnboardingStore();

  const handleToggleConnection = (id: string) => {
    if (connectedIntegrations.includes(id)) {
      disconnectIntegration(id);
    } else {
      connectIntegration(id);
    }
  };

  const handleFinishClick = () => {
    console.log('[IntegrationsScreen] Finish button clicked, calling nextStep()');
    nextStep();
  };

  return (
    <div className="relative w-full h-screen bg-black overflow-y-auto">
      {/* Logo - top-left */}
      <OnboardingLogo />

      {/* Main content area */}
      <div className="flex flex-col items-center justify-start pt-[93px] px-6 pb-32">
        <div className="max-w-[950px]">
          {/* Title & Subtitle Section */}
          <div className="mb-[25px]">
            {/* Title */}
            <h1 className="font-['Inter',sans-serif] font-normal text-[#aaaaaa] text-[30px] leading-[36px] mb-6">
              Connect your systems of progress.
            </h1>

            {/* Subtitle */}
            <p className="font-['Inter',sans-serif] font-normal text-[16px] text-[rgba(237,237,237,0.4)] leading-normal max-w-[565px]">
              Ultra syncs your work and your recovery — learning when you're
              building momentum, and when you need rest — so every day moves you
              closer to flow.
            </p>
          </div>

          {/* Integration Cards */}
          <div className="grid grid-cols-2 gap-[24px]">
            {integrations.map((integration) => (
              <IntegrationCard
                key={integration.id}
                integration={integration}
                isConnected={connectedIntegrations.includes(integration.id)}
                onToggleConnection={handleToggleConnection}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Finish button - bottom right */}
      <button
        onClick={handleFinishClick}
        className="
          absolute
          bottom-12
          right-12
          bg-transparent
          border-0
          outline-none
          p-0
          m-0
          font-['Inter',sans-serif]
          text-[20px]
          text-[#aaaaaa]
          transition-colors
          duration-200
          hover:text-white
          cursor-pointer
        "
      >
        Finish
      </button>
    </div>
  );
}

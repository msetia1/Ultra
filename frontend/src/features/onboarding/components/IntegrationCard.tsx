import type { Integration } from '../data/integrations';

interface IntegrationCardProps {
  integration: Integration;
  isConnected: boolean;
  onToggleConnection: (id: string) => void;
}

export default function IntegrationCard({
  integration,
  isConnected,
  onToggleConnection,
}: IntegrationCardProps) {
  const handleClick = () => {
    onToggleConnection(integration.id);
  };

  return (
    <div className="bg-[rgba(255,255,255,0.1)] border-[0.5px] border-[rgba(255,255,255,0.2)] rounded-[10px] px-[26px] pt-[23px] pb-[26px] relative">
      {/* Connect Button */}
      <button
        onClick={handleClick}
        className="
          absolute right-[26px] top-[26px]
          p-[10px]
          rounded-[15px]
          font-['Inter',sans-serif]
          text-[14px]
          text-white
          bg-[rgba(255,255,255,0.2)]
          hover:bg-[rgba(255,255,255,0.25)]
          transition-all
          duration-200
        "
      >
        {isConnected ? 'Connected' : 'Connect'}
      </button>

      {/* Icon */}
      <div className="w-[40px] h-[40px] bg-[rgba(255,255,255,0.2)] border border-[#8d8d8d] rounded-[10px] flex items-center justify-center overflow-hidden mb-[9px]">
        <img
          src={integration.icon}
          alt={`${integration.name} icon`}
          className="max-w-[34px] max-h-[34px] object-contain"
        />
      </div>

      {/* Name */}
      <h3 className="font-['Inter',sans-serif] font-medium text-[20px] text-[#ffffff] leading-[normal] mb-[10px]">
        {integration.name}
      </h3>

      {/* Description */}
      <p className="font-['Inter',sans-serif] text-[14px] text-[rgba(255,255,255,0.4)] leading-normal">
        {integration.description}
      </p>
    </div>
  );
}

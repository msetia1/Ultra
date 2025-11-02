import type { Integration } from '../data/integrations';

interface IntegrationCardProps {
  integration: Integration;
  isConnected: boolean;
  onToggleConnection: (id: string) => void;
  index: number;
  isVisible: boolean;
}

export default function IntegrationCard({
  integration,
  isConnected,
  onToggleConnection,
  index,
  isVisible,
}: IntegrationCardProps) {
  const handleClick = () => {
    onToggleConnection(integration.id);
  };

  return (
    <div
      className="bg-[rgba(255,255,255,0.1)] border-[0.5px] border-[rgba(255,255,255,0.2)] rounded-[10px] px-[26px] pt-[23px] pb-[26px] relative"
      style={{
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? 'translateY(0)' : 'translateY(20px)',
        transition: `opacity 600ms ease-out ${index * 100}ms, transform 600ms ease-out ${index * 100}ms`,
      }}
    >
      {/* Connect Button */}
      <button
        onClick={handleClick}
        style={{
          position: 'absolute',
          right: '26px',
          top: '26px',
          padding: '10px',
          borderRadius: '15px',
          backgroundColor: 'rgba(255,255,255,0.2)',
          border: 'none',
          outline: 'none',
          fontFamily: 'Inter, sans-serif',
          fontSize: '14px',
          color: 'white',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '10px',
          cursor: 'pointer',
          transition: 'all 200ms',
        }}
        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.25)'}
        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.2)'}
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

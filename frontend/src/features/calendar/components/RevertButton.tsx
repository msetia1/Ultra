import { Undo2 } from 'lucide-react';

interface RevertButtonProps {
  onRevert: () => void;
}

export default function RevertButton({ onRevert }: RevertButtonProps) {
  return (
    <button
      onClick={onRevert}
      className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50
        flex items-center gap-2
        px-4 py-3
        bg-[#fcecc9] text-black
        rounded-lg
        font-inter font-medium text-sm
        hover:bg-[#fcecc9]/90
        transition-all duration-200
        shadow-lg hover:shadow-xl"
      style={{
        boxShadow: '0 4px 20px rgba(252, 236, 201, 0.4)'
      }}
    >
      <Undo2 size={16} />
      Revert Changes
    </button>
  );
}

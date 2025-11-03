import { Undo2 } from 'lucide-react';

interface RevertButtonProps {
  onRevert: () => void;
}

export default function RevertButton({ onRevert }: RevertButtonProps) {
  return (
    <button
      onClick={onRevert}
      className="p-2
        text-[#888888] hover:text-[#fcecc9]
        rounded-full
        hover:bg-white/5
        transition-all duration-200
        cursor-pointer"
      aria-label="Revert changes"
    >
      <Undo2 size={18} />
    </button>
  );
}

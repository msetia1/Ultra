import type { CalendarPatch } from '../hooks/useCalendarChat';

interface PatchPreviewProps {
  patches: CalendarPatch[];
  onAccept: (patches: CalendarPatch[]) => void;
  onReject: () => void;
  isAccepting?: boolean;
}

export default function PatchPreview({ patches, onAccept, onReject, isAccepting }: PatchPreviewProps) {
  if (patches.length === 0) return null;

  return (
    <div className="border-t border-[#606060] p-4 bg-black/50">
      <h3 className="text-[#fcecc9] text-sm font-medium mb-3">
        Proposed Changes ({patches.length})
      </h3>

      <div className="space-y-2 mb-4 max-h-48 overflow-y-auto">
        {patches.map((patch, idx) => (
          <div key={patch.patch_id || idx} className="text-xs">
            <PatchDiff patch={patch} />
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => onAccept(patches)}
          disabled={isAccepting}
          className="flex-1 bg-[#fcecc9] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#fcecc9]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isAccepting ? 'Applying...' : '✓ Accept All'}
        </button>
        <button
          onClick={onReject}
          disabled={isAccepting}
          className="flex-1 bg-[#606060] text-[#fcecc9] px-4 py-2 rounded text-sm font-medium hover:bg-[#606060]/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          ✗ Reject
        </button>
      </div>
    </div>
  );
}

function PatchDiff({ patch }: { patch: CalendarPatch }) {
  switch (patch.op) {
    case 'add_event':
      return (
        <div className="bg-green-900/20 border border-green-700/30 rounded p-2 text-[#fcecc9]">
          <span className="text-green-400">+ Add</span>{' '}
          "{patch.complete_event?.title || 'New Event'}" on{' '}
          {patch.complete_event?.date} at {patch.complete_event?.start_time}
        </div>
      );

    case 'remove_event':
      return (
        <div className="bg-red-900/20 border border-red-700/30 rounded p-2 text-[#fcecc9]">
          <span className="text-red-400">- Remove</span> event on{' '}
          {patch.target_day.scheduled_date}
        </div>
      );

    case 'modify_event':
      return (
        <div className="bg-blue-900/20 border border-blue-700/30 rounded p-2 text-[#fcecc9]">
          <span className="text-blue-400">✎ Modify</span> event:
          {patch.field_patches?.map((fp: any, i: number) => (
            <div key={i} className="ml-4 mt-1 text-xs">
              {fp.field}: <del className="text-[#888888]">{fp.from_value}</del> →{' '}
              <ins className="text-green-400 no-underline">{fp.to_value}</ins>
            </div>
          ))}
        </div>
      );

    case 'move_event':
      return (
        <div className="bg-purple-900/20 border border-purple-700/30 rounded p-2 text-[#fcecc9]">
          <span className="text-purple-400">→ Move</span> event from{' '}
          {patch.from_day?.scheduled_date} to {patch.to_day?.scheduled_date}
        </div>
      );

    default:
      return (
        <div className="bg-[#606060]/20 border border-[#606060]/30 rounded p-2 text-[#888888]">
          Unknown operation: {patch.op}
        </div>
      );
  }
}

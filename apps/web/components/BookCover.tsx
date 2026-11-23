const COVER_COLORS = ["#2f6558", "#bd4f35", "#31536a", "#7b5a35", "#4d5f3b", "#6c496c"];

function colorFor(value: string): string {
  let hash = 0;
  for (const character of value) {
    hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  }
  return COVER_COLORS[hash % COVER_COLORS.length];
}

export function BookCover({
  title,
  code,
  compact = false,
}: {
  title: string;
  code: string;
  compact?: boolean;
}) {
  const color = colorFor(`${title}${code}`);
  return (
    <div
      className={`relative overflow-hidden text-chalk ${
        compact ? "h-32 w-24" : "h-48 w-36"
      }`}
      style={{ backgroundColor: color }}
      aria-hidden="true"
    >
      <div className="absolute inset-y-0 left-2 w-px bg-white/30" />
      <div className="absolute inset-y-0 left-4 w-px bg-black/15" />
      <div className="flex h-full flex-col justify-between p-4 pl-6">
        <span className="text-[9px] font-semibold tracking-[0.2em] text-white/60">{code}</span>
        <span className="font-display text-lg font-bold leading-snug">{title}</span>
        <span className="text-[9px] tracking-[0.14em] text-white/60">CAMPUS EDITION</span>
      </div>
      <div className="absolute -bottom-8 -right-8 h-24 w-24 rounded-full border border-white/20" />
    </div>
  );
}

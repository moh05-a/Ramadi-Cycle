type MarkProps = { size?: number; title?: string; reversed?: boolean };

/** Roof, downpipe, half-full tank. Rectangles only. Colours follow the theme unless `reversed` forces the dark-ground version. */
export function Mark({ size = 32, title = "Ramadi-Cycle", reversed = false }: MarkProps) {
  const c = reversed
    ? { roof: "#E3E6E2", tank: "#6F7578", water: "#3A86B0" }
    : { roof: "var(--rc-mark-roof)", tank: "var(--rc-mark-tank)", water: "var(--rc-mark-water)" };
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" {...(title ? { role: "img", "aria-label": title } : { "aria-hidden": true })}>
      <rect x="6" y="10" width="52" height="6" fill={c.roof} />
      <rect x="14" y="22" width="36" height="34" fill={c.tank} />
      <rect x="14" y="38" width="36" height="18" fill={c.water} />
      <rect x="29" y="16" width="6" height="6" fill={c.roof} />
    </svg>
  );
}

/** Mark with English and Arabic names. Minimum width 120px. */
export function Logo({ width = 220 }: { width?: number }) {
  return (
    <span className="rc-logo" style={{ width }} role="img" aria-label="Ramadi-Cycle, رمادي">
      <Mark size={width * 0.23} title="" />
      <span className="rc-logo__words" aria-hidden="true">
        <span className="rc-logo__en" style={{ fontSize: width * 0.086 }}>Ramadi-Cycle</span>
        <span className="rc-logo__ar" lang="ar" style={{ fontSize: width * 0.06 }}>رمادي</span>
      </span>
    </span>
  );
}

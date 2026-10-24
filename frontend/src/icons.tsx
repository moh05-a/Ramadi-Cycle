// Small inline icons. Colours come from currentColor or brand tokens, so both themes work.

/** Drop with a leaf. A concept sketch from the v5 handoff; have a designer finalise it. */
export function DropLogo({ size = 44 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden="true">
      <path d="M50 8 C50 8 20 44 20 62 A30 30 0 0 0 80 62 C80 44 50 8 50 8 Z" fill="var(--rc-cistern)" />
      <g transform="rotate(-32 50 64)">
        <path d="M50 84 C37 76 37 56 50 45 C63 56 63 76 50 84 Z" fill="var(--rc-paper)" />
        <path d="M50 80 V52" stroke="var(--rc-olive)" strokeWidth="2.5" strokeLinecap="round" />
      </g>
    </svg>
  );
}

const base = { width: 20, height: 20, viewBox: "0 0 20 20", "aria-hidden": true, className: "sh-icon" } as const;

/** Points forward in reading direction; mirrored in RTL by CSS. */
export const ArrowIcon = () => (
  <svg {...base} className="sh-icon sh-arrow"><path d="M3 10h13M11 5l5 5-5 5" stroke="currentColor" strokeWidth="2.2" fill="none" strokeLinecap="square" /></svg>
);
export const PrintIcon = () => (
  <svg {...base}><path d="M5 7V2h10v5M5 15H2V7h16v8h-3" fill="none" stroke="currentColor" strokeWidth="2" /><rect x="5" y="12" width="10" height="6" fill="none" stroke="currentColor" strokeWidth="2" /></svg>
);
export const DownloadIcon = () => (
  <svg {...base}><path d="M10 2v11M5 8l5 5 5-5M3 18h14" fill="none" stroke="currentColor" strokeWidth="2" /></svg>
);

/* Navigation icons, 24px grid, stroke only (currentColor), for the limelight top bar. */
const nav = { width: 20, height: 20, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2,
  strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true } as const;
export const NavHomeIcon = () => <svg {...nav}><path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" /></svg>;
export const NavGardenIcon = () => (
  <svg {...nav}><path d="M12 21v-9" /><path d="M12 13C12 8.6 9 6 4 6c0 4.4 3 7 8 7z" /><path d="M12 11c0-3.9 2.5-6 7-6 0 3.9-2.5 6-7 6z" /></svg>
);
export const NavSaveIcon = () => <svg {...nav}><circle cx="9" cy="9" r="6" /><path d="M15.7 10.4a6 6 0 1 1-5.3 5.3" /></svg>;
export const NavPlanIcon = () => (
  <svg {...nav}><rect x="5" y="4" width="14" height="17" rx="2" /><path d="M9 4V3h6v1M9 10h6M9 14h6M9 18h3" /></svg>
);
export const NavCalcIcon = () => (
  <svg {...nav}><rect x="5" y="3" width="14" height="18" rx="2" /><path d="M8 7h8M8 12h.01M12 12h.01M16 12h.01M8 16h.01M12 16h.01M16 16h.01" /></svg>
);

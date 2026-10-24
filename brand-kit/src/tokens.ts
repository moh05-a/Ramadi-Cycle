// Single source for brand values. tokens.css must match; tokens.test.ts enforces it.

export const color = {
  bg: { light: "#EEEFEC", dark: "#121719", name: "Plaster", use: "Page background" },
  surface: { light: "#E2E4E0", dark: "#1A2124", name: "Concrete light", use: "Sidebar, panels, notices" },
  paper: { light: "#F8F8F6", dark: "#212A2E", name: "Paper", use: "Inputs, tables, code" },
  ink: { light: "#1F2A2E", dark: "#E3E6E2", name: "Ink", use: "Text" },
  stone: { light: "#596165", dark: "#9CA3A6", name: "Stone", use: "Captions, secondary text, axes" },
  rule: { light: "#CDD0CB", dark: "#2E383C", name: "Rule", use: "1px lines and borders" },
  cistern: { light: "#1E5B7A", dark: "#6DB0D4", name: "Cistern", use: "Primary: buttons, links, rain" },
  "cistern-hover": { light: "#164861", dark: "#8EC3E0", name: "Cistern hover", use: "Hover on primary" },
  "on-cistern": { light: "#FFFFFF", dark: "#121719", name: "On cistern", use: "Label on primary button" },
  olive: { light: "#4E6128", dark: "#A5BF70", name: "Olive", use: "Saved, passed checks, greywater" },
  "olive-tint": { light: "#E0E6D5", dark: "#26301C", name: "Olive tint", use: "Passed badge fill" },
  rust: { light: "#A2441E", dark: "#E5895F", name: "Rust", use: "Safety rules and failures only" },
  "rust-tint": { light: "#F1E1D8", dark: "#34221A", name: "Rust tint", use: "Failed badge fill" },
  bought: { light: "#C4C7C2", dark: "#3A4549", name: "Bought", use: "Chart: water still bought" },
  "mark-roof": { light: "#1F2A2E", dark: "#E3E6E2", name: "Mark roof", use: "Logo roof and downpipe" },
  "mark-tank": { light: "#8A8D8F", dark: "#6F7578", name: "Concrete", use: "Logo tank. Never text" },
  "mark-water": { light: "#1E5B7A", dark: "#3A86B0", name: "Mark water", use: "Logo water" },
} as const;

export type ColorToken = keyof typeof color;

export const font = {
  latin: '"IBM Plex Sans", "Helvetica Neue", Arial, sans-serif',
  arabic: '"IBM Plex Sans Arabic", "Geeza Pro", Tahoma, sans-serif',
  mono: '"IBM Plex Mono", ui-monospace, Menlo, monospace',
} as const;

// 1.25 ratio, 16px base
export const text = {
  "3xl": { rem: "2.441rem", px: 39, use: "Page title" },
  "2xl": { rem: "1.953rem", px: 31, use: "Metric values" },
  xl: { rem: "1.5625rem", px: 25, use: "Section heads" },
  lg: { rem: "1.25rem", px: 20, use: "Sub-heads" },
  base: { rem: "1rem", px: 16, use: "Body" },
  sm: { rem: "0.875rem", px: 14, use: "Labels, tables" },
  xs: { rem: "0.75rem", px: 12, use: "Captions, axis" },
} as const;

export const space = { 1: 4, 2: 8, 3: 12, 4: 16, 6: 24, 8: 32, 12: 48, 16: 64 } as const;
export const radius = 2;

/** WCAG 2.1 contrast ratio between two #RRGGBB colours. */
export function contrast(a: string, b: string): number {
  const lum = (hex: string) => {
    const [r, g, bl] = [1, 3, 5].map((i) => {
      const c = parseInt(hex.slice(i, i + 2), 16) / 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * bl;
  };
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

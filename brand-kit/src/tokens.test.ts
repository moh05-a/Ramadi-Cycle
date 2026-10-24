import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { niceTicks } from "./components/charts";
import { num } from "./i18n";
import { color, contrast } from "./tokens";

const css = readFileSync(new URL("./tokens.css", import.meta.url), "utf8");
const block = (sel: string) => css.slice(css.indexOf(sel)).split("}")[0];
const val = (src: string, name: string) => src.match(new RegExp(`--rc-${name}:\\s*(#[0-9A-Fa-f]{6})`))?.[1]?.toUpperCase();

describe("tokens.css matches tokens.ts", () => {
  for (const [name, c] of Object.entries(color)) {
    it(name, () => {
      expect(val(block(":root {"), name)).toBe(c.light);
      expect(val(block(':root:not([data-theme="light"])'), name)).toBe(c.dark);
      expect(val(block(':root[data-theme="dark"]'), name)).toBe(c.dark);
    });
  }
});

describe("contrast", () => {
  it("matches the WCAG reference", () => {
    expect(contrast("#000000", "#FFFFFF")).toBeCloseTo(21, 5);
    expect(contrast("#777777", "#FFFFFF")).toBeCloseTo(4.48, 2);
  });
  for (const mode of ["light", "dark"] as const) {
    for (const fg of ["ink", "stone", "cistern", "olive", "rust"] as const) {
      for (const bg of ["bg", "surface", "paper"] as const) {
        it(`${fg} on ${bg} (${mode}) passes AA`, () => expect(contrast(color[fg][mode], color[bg][mode])).toBeGreaterThanOrEqual(4.5));
      }
    }
    it(`button label on cistern (${mode}) passes AA`, () => expect(contrast(color["on-cistern"][mode], color.cistern[mode])).toBeGreaterThanOrEqual(4.5));
  }
});

describe("niceTicks", () => {
  it("covers the max with round steps from zero", () => {
    expect(niceTicks(9.2)).toEqual([0, 2, 4, 6, 8, 10]);
    expect(niceTicks(2.3)).toEqual([0, 0.5, 1, 1.5, 2, 2.5]);
    expect(niceTicks(10)).toEqual([0, 2, 4, 6, 8, 10]);
  });
  it("handles zero and bad input", () => {
    expect(niceTicks(0)).toEqual([0, 1]);
    expect(niceTicks(NaN)).toEqual([0, 1]);
  });
});

it("num uses Western digits", () => {
  expect(num(1234.56, 1)).toBe("1,234.6");
});

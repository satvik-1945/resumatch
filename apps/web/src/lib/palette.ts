import type { CSSProperties } from "react";

export const workflowPalette = [
  { color: "#c8ef80", name: "Lime" }, { color: "#f6a58b", name: "Coral" },
  { color: "#7fd6d0", name: "Seafoam" }, { color: "#b7adf5", name: "Iris" },
  { color: "#edca76", name: "Amber" }, { color: "#9bbcf2", name: "Sky" },
  { color: "#e8a3cc", name: "Rose" },
];
export function workflowStyle(color = workflowPalette[0].color): CSSProperties {
  return { "--workflow-color": color } as CSSProperties;
}
export function blendColors(colors: string[], alpha = "") {
  const unique = [...new Set(colors)];
  if (!unique.length) return "transparent";
  if (unique.length === 1) return unique[0] + alpha;
  return `linear-gradient(120deg, ${unique.map((color, i) => `${color}${alpha} ${i / (unique.length - 1) * 100}%`).join(", ")})`;
}

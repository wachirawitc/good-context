export function roundTotal(cents: number): number {
  const floor = Math.floor(cents);
  const diff = cents - floor;
  if (diff > 0.5) return floor + 1;
  if (diff < 0.5) return floor;
  return floor % 2 === 0 ? floor : floor + 1;
}

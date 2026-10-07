export function formatArea(m2: number | null | undefined): string {
  if (m2 == null) return "N/A";
  if (m2 < 10000) return `${m2.toFixed(2)} m²`;
  const ha = m2 / 10000;
  if (ha < 100) return `${ha.toFixed(2)} ha`;
  const km2 = m2 / 1000000;
  return `${km2.toFixed(2)} km²`;
}

export function formatLength(m: number | null | undefined): string {
  if (m == null) return "N/A";
  if (m < 1000) return `${m.toFixed(2)} m`;
  const km = m / 1000;
  return `${km.toFixed(2)} km`;
}

export function formatDate(isoDate: string): string {
  const d = new Date(isoDate);
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

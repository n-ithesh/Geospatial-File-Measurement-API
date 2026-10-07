import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useMeasurements(id: string, limit = 50, offset = 0, geometryType?: string, enabled = true) {
  return useQuery({
    queryKey: ["measurements", id, limit, offset, geometryType],
    queryFn: () => api.getMeasurements(id, limit, offset, geometryType),
    enabled,
    placeholderData: (prev) => prev,
  });
}

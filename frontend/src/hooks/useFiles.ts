import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useFiles(limit = 20, offset = 0) {
  return useQuery({
    queryKey: ["files", limit, offset],
    queryFn: () => api.getFiles(limit, offset),
  });
}

import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useFile(id: string) {
  return useQuery({
    queryKey: ["file", id],
    queryFn: () => api.getFile(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "PENDING" || status === "PROCESSING") {
        return 2000;
      }
      return false;
    },
  });
}

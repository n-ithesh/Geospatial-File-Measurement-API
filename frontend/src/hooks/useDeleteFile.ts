import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useDeleteFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.deleteFile(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ["files"] });
      queryClient.removeQueries({ queryKey: ["file", deletedId] });
      queryClient.removeQueries({ queryKey: ["measurements", deletedId] });
    },
  });
}

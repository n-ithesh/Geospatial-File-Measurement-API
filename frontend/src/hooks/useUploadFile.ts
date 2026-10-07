import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { FileInfo } from "../types/api";

export function useUploadFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => api.uploadFile(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["files"] });
    },
  });
}

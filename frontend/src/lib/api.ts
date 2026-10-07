import { FileInfo, FileDetail, ListFilesResponse, MeasurementsResponse } from "../types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.name = "ApiError";
  }
}

async function fetchApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...options.headers,
    },
  });

  if (res.status === 204) {
    return {} as T;
  }

  let data;
  try {
    data = await res.json();
  } catch (err) {
    throw new ApiError(res.status, "Invalid JSON response");
  }

  if (!res.ok) {
    throw new ApiError(res.status, data.detail || "An error occurred");
  }

  return data as T;
}

export const api = {
  uploadFile: async (file: File): Promise<FileInfo> => {
    const formData = new FormData();
    formData.append("file", file);
    return fetchApi<FileInfo>("/api/files/", {
      method: "POST",
      body: formData,
    });
  },

  getFiles: async (limit = 20, offset = 0): Promise<ListFilesResponse> => {
    return fetchApi<ListFilesResponse>(`/api/files/?limit=${limit}&offset=${offset}`);
  },

  getFile: async (id: string): Promise<FileDetail> => {
    return fetchApi<FileDetail>(`/api/files/${id}/`);
  },

  getMeasurements: async (
    id: string,
    limit = 50,
    offset = 0,
    geometryType?: string
  ): Promise<MeasurementsResponse> => {
    let url = `/api/files/${id}/measurements/?limit=${limit}&offset=${offset}`;
    if (geometryType) {
      url += `&geometry_type=${encodeURIComponent(geometryType)}`;
    }
    return fetchApi<MeasurementsResponse>(url);
  },

  deleteFile: async (id: string): Promise<void> => {
    await fetchApi<void>(`/api/files/${id}/`, { method: "DELETE" });
  },
};

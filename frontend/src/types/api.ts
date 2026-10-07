export type FileStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
export type MeasurementStatus = "OK" | "NOT_REQUIRED" | "UNSUPPORTED" | "FAILED";
export type MeasurementType = "area" | "length" | null;
export type MeasurementUnit = "m2" | "m" | null;

export interface FileInfo {
  id: string;
  filename: string;
  file_type: string;
  feature_count: number;
  crs: string;
  status: FileStatus;
  error_message: string | null;
  created_at: string;
}

export type FileDetail = FileInfo;

export interface ListFilesResponse {
  total: number;
  limit: number;
  offset: number;
  items: FileInfo[];
}

export interface MeasurementData {
  type: MeasurementType;
  value: number | null;
  unit: MeasurementUnit;
  projected_crs: string | null;
  status: MeasurementStatus;
  note: string | null;
}

export interface Feature {
  index: number;
  geometry_type: string;
  crs: string;
  properties: Record<string, any>;
  geometry: any;
  measurement: MeasurementData;
}

export interface Summary {
  total_area_m2: number;
  total_length_m: number;
  unsupported: number;
  failed: number;
  by_geometry_type: Record<string, number>;
}

export interface MeasurementsResponse {
  file_id: string;
  total: number;
  summary: Summary;
  features: Feature[];
}

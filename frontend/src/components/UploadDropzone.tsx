"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useRouter } from "next/navigation";
import { useUploadFile } from "../hooks/useUploadFile";
import { ErrorMessage } from "./ErrorMessage";
import { Spinner } from "./Spinner";

export function UploadDropzone() {
  const router = useRouter();
  const { mutateAsync: uploadFile, isPending } = useUploadFile();
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setError(null);
      if (acceptedFiles.length === 0) return;
      const file = acceptedFiles[0];

      if (!file.name.endsWith(".zip") && !file.name.endsWith(".kml")) {
        setError("Only .zip and .kml files are accepted.");
        return;
      }

      try {
        const result = await uploadFile(file);
        router.push(`/files/${result.id}`);
      } catch (err: any) {
        setError(err.detail || err.message || "Upload failed");
      }
    },
    [uploadFile, router]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/zip": [".zip"],
      "application/vnd.google-earth.kml+xml": [".kml"],
    },
    maxFiles: 1,
  });

  return (
    <div className="space-y-4">
      {error && <ErrorMessage message={error} />}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
          isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-gray-400"
        } ${isPending ? "opacity-50 pointer-events-none" : ""}`}
      >
        <input {...getInputProps()} />
        {isPending ? (
          <div className="flex flex-col items-center justify-center space-y-4">
            <Spinner />
            <p className="text-gray-600">Uploading...</p>
          </div>
        ) : (
          <div>
            <p className="text-lg text-gray-600">
              {isDragActive ? "Drop the file here..." : "Drag & drop a file here, or click to select"}
            </p>
            <p className="text-sm text-gray-500 mt-2">Accepts .zip (Shapefile) or .kml</p>
          </div>
        )}
      </div>
    </div>
  );
}

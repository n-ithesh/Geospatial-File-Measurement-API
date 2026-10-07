"use client";

import Link from "next/link";
import { useFiles } from "../hooks/useFiles";
import { useDeleteFile } from "../hooks/useDeleteFile";
import { formatDate } from "../lib/format";
import { FileStatusBadge } from "./FileStatusBadge";
import { EmptyState } from "./EmptyState";
import { Spinner } from "./Spinner";
import { ErrorMessage } from "./ErrorMessage";

export function FileList() {
  const { data, isLoading, error } = useFiles(20, 0);
  const { mutate: deleteFile, isPending: isDeleting } = useDeleteFile();

  if (isLoading) return <Spinner />;
  if (error) return <ErrorMessage message={(error as any).message || "Failed to load files"} />;
  if (!data?.items.length) return <EmptyState message="No files uploaded yet." />;

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    if (confirm("Are you sure you want to delete this file?")) {
      deleteFile(id);
    }
  };

  return (
    <div className="overflow-hidden bg-white shadow sm:rounded-md border border-gray-200">
      <ul role="list" className="divide-y divide-gray-200">
        {data.items.map((file) => (
          <li key={file.id}>
            <Link href={`/files/${file.id}`} className="block hover:bg-gray-50">
              <div className="flex items-center px-4 py-4 sm:px-6">
                <div className="min-w-0 flex-1 sm:flex sm:items-center sm:justify-between">
                  <div className="truncate">
                    <div className="flex text-sm">
                      <p className="truncate font-medium text-blue-600">{file.filename}</p>
                      <p className="ml-1 shrink-0 font-normal text-gray-500">
                        in {file.crs}
                      </p>
                    </div>
                    <div className="mt-2 flex">
                      <div className="flex items-center text-sm text-gray-500">
                        <p>
                          {file.feature_count} {file.feature_count === 1 ? "feature" : "features"}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 flex items-center justify-between sm:ml-5 sm:mt-0 sm:shrink-0 sm:justify-start">
                    <FileStatusBadge status={file.status} />
                    <p className="ml-4 flex items-center text-sm text-gray-500">
                      {formatDate(file.created_at)}
                    </p>
                    <button
                      onClick={(e) => handleDelete(file.id, e)}
                      disabled={isDeleting}
                      className="ml-4 text-sm text-red-600 hover:text-red-800 disabled:opacity-50"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

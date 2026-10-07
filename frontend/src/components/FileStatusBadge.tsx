import { FileStatus } from "../types/api";

export function FileStatusBadge({ status }: { status: FileStatus }) {
  let colorClass = "bg-gray-100 text-gray-800";
  if (status === "PENDING" || status === "PROCESSING") {
    colorClass = "bg-blue-100 text-blue-800";
  } else if (status === "COMPLETED") {
    colorClass = "bg-green-100 text-green-800";
  } else if (status === "FAILED") {
    colorClass = "bg-red-100 text-red-800";
  }

  return (
    <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${colorClass}`}>
      {status}
    </span>
  );
}

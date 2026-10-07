"use client";

import { useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useFile } from "../../../hooks/useFile";
import { useMeasurements } from "../../../hooks/useMeasurements";
import { Spinner } from "../../../components/Spinner";
import { ErrorMessage } from "../../../components/ErrorMessage";
import { FileStatusBadge } from "../../../components/FileStatusBadge";
import { MeasurementSummary } from "../../../components/MeasurementSummary";
import { MeasurementTable } from "../../../components/MeasurementTable";
import { formatDate } from "../../../lib/format";

// Dynamic import for MapView since leaflet requires `window`
const MapView = dynamic(() => import("../../../components/MapView"), {
  ssr: false,
  loading: () => <div className="h-[500px] w-full flex items-center justify-center bg-gray-100 rounded-lg border border-gray-200"><Spinner /></div>
});

export default function FileDetail({ params }: { params: { id: string } }) {
  const fileId = params.id;
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  
  // Table pagination & filtering
  const [offset, setOffset] = useState(0);
  const [geometryType, setGeometryType] = useState<string>("");
  const limit = 50;

  const { data: file, isLoading: fileLoading, error: fileError } = useFile(fileId);

  // Only fetch measurements if file processing is COMPLETED
  const isCompleted = file?.status === "COMPLETED";
  const { data: measurements, isLoading: measLoading, error: measError } = useMeasurements(
    fileId,
    limit,
    offset,
    geometryType,
    isCompleted
  );

  // We fetch a larger un-paginated set just for the map view (limit 1000)
  // Actually, to keep it simple as requested: "render only the current page of features in the table, but the map should load all features (request limit=1000 in a separate query)"
  const { data: allMeasurements } = useMeasurements(fileId, 1000, 0, undefined, isCompleted);

  if (fileLoading) return <div className="py-12 flex justify-center"><Spinner /></div>;
  if (fileError || !file) return <ErrorMessage message={(fileError as any)?.message || "File not found"} />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-4">
            <Link href="/" className="text-sm font-medium text-blue-600 hover:text-blue-500">
              &larr; Back to all files
            </Link>
          </div>
          <h2 className="mt-2 text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl sm:tracking-tight">
            {file.filename}
          </h2>
          <div className="mt-1 flex flex-col sm:mt-0 sm:flex-row sm:flex-wrap sm:space-x-6">
            <div className="mt-2 flex items-center text-sm text-gray-500">
              Uploaded: {formatDate(file.created_at)}
            </div>
            <div className="mt-2 flex items-center text-sm text-gray-500">
              CRS: {file.crs}
            </div>
            <div className="mt-2 flex items-center text-sm text-gray-500">
              <FileStatusBadge status={file.status} />
            </div>
          </div>
        </div>
      </div>

      {(file.status === "PENDING" || file.status === "PROCESSING") && (
        <div className="py-12 flex flex-col items-center justify-center bg-white rounded-lg border border-gray-200 shadow-sm">
          <Spinner className="h-12 w-12 mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Processing File...</h3>
          <p className="text-sm text-gray-500 mt-1">This may take a few moments for large files.</p>
        </div>
      )}

      {file.status === "FAILED" && (
        <ErrorMessage title="File Processing Failed" message={file.error_message || "Unknown error"} />
      )}

      {isCompleted && measurements && (
        <>
          <MeasurementSummary summary={measurements.summary} featureCount={file.feature_count} />

          <div className="flex flex-col lg:flex-row gap-6 mt-6">
            <div className="w-full lg:w-1/2">
              <h3 className="text-lg font-medium mb-3 text-gray-900">Map View</h3>
              {allMeasurements?.features.length === 1000 && (
                <div className="bg-yellow-50 text-yellow-800 text-xs p-2 mb-2 rounded border border-yellow-200">
                  Showing first 1000 features on the map.
                </div>
              )}
              <MapView 
                features={allMeasurements?.features || measurements.features} 
                hoveredIndex={hoveredIndex} 
                onHover={setHoveredIndex} 
              />
            </div>
            
            <div className="w-full lg:w-1/2 flex flex-col">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-medium text-gray-900">Features</h3>
                <select 
                  className="block rounded-md border-0 py-1.5 pl-3 pr-10 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-blue-600 sm:text-sm sm:leading-6"
                  value={geometryType}
                  onChange={(e) => { setGeometryType(e.target.value); setOffset(0); }}
                >
                  <option value="">All Types</option>
                  {Object.keys(measurements.summary.by_geometry_type).map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              {measLoading ? (
                <div className="py-12 flex justify-center"><Spinner /></div>
              ) : measError ? (
                <ErrorMessage message={(measError as any).message} />
              ) : (
                <>
                  <MeasurementTable 
                    features={measurements.features} 
                    hoveredIndex={hoveredIndex} 
                    onHover={setHoveredIndex}
                    onClick={(idx) => setHoveredIndex(idx === hoveredIndex ? null : idx)}
                  />
                  
                  {/* Pagination */}
                  <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6 mt-4 rounded-lg shadow-sm border">
                    <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                      <div>
                        <p className="text-sm text-gray-700">
                          Showing <span className="font-medium">{offset + 1}</span> to{" "}
                          <span className="font-medium">{Math.min(offset + limit, measurements.total)}</span> of{" "}
                          <span className="font-medium">{measurements.total}</span> results
                        </p>
                      </div>
                      <div>
                        <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                          <button
                            onClick={() => setOffset(Math.max(0, offset - limit))}
                            disabled={offset === 0}
                            className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                          >
                            <span className="sr-only">Previous</span>
                            &larr; Prev
                          </button>
                          <button
                            onClick={() => setOffset(offset + limit)}
                            disabled={offset + limit >= measurements.total}
                            className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                          >
                            <span className="sr-only">Next</span>
                            Next &rarr;
                          </button>
                        </nav>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

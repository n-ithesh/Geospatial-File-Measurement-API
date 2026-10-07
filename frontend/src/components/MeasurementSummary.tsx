import { Summary } from "../types/api";
import { formatArea, formatLength } from "../lib/format";

export function MeasurementSummary({ summary, featureCount }: { summary: Summary; featureCount: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 mt-6">
      <div className="bg-white overflow-hidden shadow rounded-lg border border-gray-200 p-5">
        <dt className="text-sm font-medium text-gray-500 truncate">Total Features</dt>
        <dd className="mt-1 text-2xl font-semibold text-gray-900">{featureCount}</dd>
        <div className="mt-2 text-xs text-gray-500 flex flex-wrap gap-2">
          {Object.entries(summary.by_geometry_type).map(([type, count]) => (
            <span key={type} className="bg-gray-100 rounded px-2 py-0.5">
              {type}: {count}
            </span>
          ))}
        </div>
      </div>
      
      <div className="bg-white overflow-hidden shadow rounded-lg border border-gray-200 p-5">
        <dt className="text-sm font-medium text-gray-500 truncate">Total Area</dt>
        <dd className="mt-1 text-2xl font-semibold text-gray-900">{formatArea(summary.total_area_m2)}</dd>
        {summary.total_area_m2 > 0 && (
          <div className="mt-2 text-xs text-gray-500" title="Raw value in m²">
            {summary.total_area_m2.toLocaleString(undefined, { maximumFractionDigits: 2 })} m²
          </div>
        )}
      </div>

      <div className="bg-white overflow-hidden shadow rounded-lg border border-gray-200 p-5">
        <dt className="text-sm font-medium text-gray-500 truncate">Total Length</dt>
        <dd className="mt-1 text-2xl font-semibold text-gray-900">{formatLength(summary.total_length_m)}</dd>
        {summary.total_length_m > 0 && (
          <div className="mt-2 text-xs text-gray-500" title="Raw value in meters">
            {summary.total_length_m.toLocaleString(undefined, { maximumFractionDigits: 2 })} m
          </div>
        )}
      </div>

      <div className="bg-white overflow-hidden shadow rounded-lg border border-gray-200 p-5">
        <dt className="text-sm font-medium text-gray-500 truncate">Processing Status</dt>
        <dd className="mt-1 text-xl font-semibold text-gray-900 flex gap-4">
          <span className={summary.failed > 0 ? "text-red-600" : "text-green-600"}>
            {summary.failed} Failed
          </span>
          <span className={summary.unsupported > 0 ? "text-amber-600" : "text-gray-500"}>
            {summary.unsupported} Unsupported
          </span>
        </dd>
      </div>
    </div>
  );
}

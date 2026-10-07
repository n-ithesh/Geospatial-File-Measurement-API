"use client";

import { useState, Fragment } from "react";
import { Feature } from "../types/api";
import { formatArea, formatLength } from "../lib/format";

function MeasurementStatusBadge({ status }: { status: string }) {
  if (status === "OK") return <span className="text-green-700 bg-green-50 px-2 py-1 rounded text-xs font-medium border border-green-200">OK</span>;
  if (status === "NOT_REQUIRED") return <span className="text-gray-600 bg-gray-100 px-2 py-1 rounded text-xs font-medium border border-gray-200">Not Required</span>;
  if (status === "UNSUPPORTED") return <span className="text-amber-700 bg-amber-50 px-2 py-1 rounded text-xs font-medium border border-amber-200">Unsupported</span>;
  return <span className="text-red-700 bg-red-50 px-2 py-1 rounded text-xs font-medium border border-red-200">Failed</span>;
}

export function MeasurementTable({
  features,
  hoveredIndex,
  onHover,
  onClick,
}: {
  features: Feature[];
  hoveredIndex: number | null;
  onHover: (idx: number | null) => void;
  onClick: (idx: number) => void;
}) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  const toggleRow = (idx: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpanded((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  return (
    <div className="overflow-x-auto shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
      <table className="min-w-full divide-y divide-gray-300 bg-white">
        <thead className="bg-gray-50">
          <tr>
            <th className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6 w-16">#</th>
            <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 w-32">Type</th>
            <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 w-64">Properties</th>
            <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 w-48">Measurement</th>
            <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 w-32">CRS</th>
            <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 w-32">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {features.map((f) => {
            const isHovered = hoveredIndex === f.index;
            const isExpanded = expanded[f.index];
            const namePreview = f.properties.name || f.properties.id || Object.values(f.properties)[0] || "-";

            return (
              <Fragment key={f.index}>
                <tr
                  className={`cursor-pointer transition-colors ${isHovered ? "bg-blue-50" : "hover:bg-gray-50"}`}
                  onMouseEnter={() => onHover(f.index)}
                  onMouseLeave={() => onHover(null)}
                  onClick={() => onClick(f.index)}
                >
                  <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">
                    {f.index}
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{f.geometry_type}</td>
                  <td className="px-3 py-4 text-sm text-gray-500 max-w-xs truncate" title={JSON.stringify(f.properties)}>
                    <div className="flex items-center justify-between">
                      <span className="truncate mr-2">{namePreview}</span>
                      <button
                        onClick={(e) => toggleRow(f.index, e)}
                        className="text-blue-600 hover:text-blue-900 text-xs shrink-0 p-1"
                      >
                        {isExpanded ? "Hide" : "Show all"}
                      </button>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-900 font-medium">
                    {f.measurement.type === "area" && (
                      <span title={`${f.measurement.value} m²`}>{formatArea(f.measurement.value)}</span>
                    )}
                    {f.measurement.type === "length" && (
                      <span title={`${f.measurement.value} m`}>{formatLength(f.measurement.value)}</span>
                    )}
                    {!f.measurement.type && <span className="text-gray-400">-</span>}
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                    {f.measurement.projected_crs || "-"}
                  </td>
                  <td className="px-3 py-4 text-sm text-gray-500">
                    <MeasurementStatusBadge status={f.measurement.status} />
                    {f.measurement.note && (
                      <div className="text-xs mt-1 text-gray-400 max-w-[150px] truncate" title={f.measurement.note}>
                        {f.measurement.note}
                      </div>
                    )}
                  </td>
                </tr>
                {isExpanded && (
                  <tr>
                    <td colSpan={6} className="px-6 py-4 bg-gray-50 text-sm">
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                        {Object.entries(f.properties).map(([k, v]) => (
                          <div key={k} className="border-b border-gray-200 pb-1">
                            <span className="text-gray-500 text-xs font-semibold uppercase block">{k}</span>
                            <span className="text-gray-900 break-words">{String(v)}</span>
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

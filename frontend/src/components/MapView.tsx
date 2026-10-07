"use client";

import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { Feature } from "../types/api";

// Fix for default marker icons in react-leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

function FitBounds({ features }: { features: Feature[] }) {
  const map = useMap();
  useEffect(() => {
    if (features.length === 0) return;
    try {
      const geoJsonLayer = L.geoJSON({
        type: "FeatureCollection",
        features: features,
      } as any);
      map.fitBounds(geoJsonLayer.getBounds(), { padding: [20, 20] });
    } catch (err) {
      console.warn("Could not fit map bounds:", err);
    }
  }, [features, map]);
  return null;
}

export default function MapView({
  features,
  hoveredIndex,
  onHover,
}: {
  features: Feature[];
  hoveredIndex: number | null;
  onHover: (idx: number | null) => void;
}) {
  const geoJsonRef = useRef<L.GeoJSON>(null);

  // Apply hover styles manually since react-leaflet GeoJSON doesn't update styles easily per-feature
  useEffect(() => {
    if (geoJsonRef.current) {
      geoJsonRef.current.eachLayer((layer: any) => {
        const featureIndex = layer.feature.index;
        if (featureIndex === hoveredIndex) {
          if (layer.setStyle) {
            layer.setStyle({ weight: 4, color: "#2563eb", fillOpacity: 0.5 });
          }
        } else {
          geoJsonRef.current?.resetStyle(layer);
        }
      });
    }
  }, [hoveredIndex]);

  const style = (feature: any) => {
    const isLine = feature.geometry.type.includes("LineString");
    return {
      color: isLine ? "#d97706" : "#3b82f6", // amber for lines, blue for polygons
      weight: 2,
      fillOpacity: 0.2,
    };
  };

  const onEachFeature = (feature: any, layer: L.Layer) => {
    const f = feature as Feature;
    
    // Popup content
    const popupContent = `
      <div class="text-sm">
        <p class="font-bold mb-1">Feature #${f.index} (${f.geometry_type})</p>
        <div class="mb-2 max-h-32 overflow-y-auto">
          ${Object.entries(f.properties).map(([k, v]) => `<div><span class="text-gray-500">${k}:</span> ${v}</div>`).join("")}
        </div>
        ${f.measurement.value != null ? `<p class="font-semibold text-blue-700">Measurement: ${f.measurement.value.toLocaleString()} ${f.measurement.unit}</p>` : ""}
        <p class="text-xs text-gray-500 mt-1">Status: ${f.measurement.status}</p>
      </div>
    `;
    layer.bindPopup(popupContent);

    // Hover events
    layer.on({
      mouseover: () => onHover(f.index),
      mouseout: () => onHover(null),
    });
  };

  return (
    <div className="h-[500px] w-full rounded-lg overflow-hidden border border-gray-300 shadow-sm relative z-0">
      <MapContainer center={[0, 0]} zoom={2} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <GeoJSON
          ref={geoJsonRef}
          data={({ type: "FeatureCollection", features: features } as any)}
          style={style}
          onEachFeature={onEachFeature}
        />
        <FitBounds features={features} />
      </MapContainer>
    </div>
  );
}

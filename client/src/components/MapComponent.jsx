import React, { useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-defaulticon-compatibility/dist/leaflet-defaulticon-compatibility.css";
import "leaflet-defaulticon-compatibility";

// Example marker data

// Utility Component to recenter the map
const RecenterMap = ({ center }) => {
  const map = useMap();
  if (center) map.setView(center, 13);
  return null;
};

const MapComponent = ({ markers, center }) => {
  return (
    <MapContainer
      center={center || [43.265505, -79.918187]}
      zoom={16}
      style={{ height: "100vh", width: "70%" }}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="© OpenStreetMap contributors"
      />
      <RecenterMap center={center} />
      {markers.map((marker, index) => (
        <Marker
          key={index}
          position={marker.position}>
          <Popup>{marker.popup}</Popup>
        </Marker>
      ))}
    </MapContainer>
  );
};

export default MapComponent;

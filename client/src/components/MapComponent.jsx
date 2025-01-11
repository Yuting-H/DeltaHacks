import React from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-defaulticon-compatibility/dist/leaflet-defaulticon-compatibility.css";
import "leaflet-defaulticon-compatibility";

const MapComponent = () => {
  const position = [51.505, -0.09]; // Coordinates for the map center

  return (
    <MapContainer
      center={position}
      zoom={13}
      style={{ height: "100vh", width: "100%" }}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="© OpenStreetMap contributors"
      />
      <Marker position={position}>
        <Popup>
          <b>Hello, World!</b>
          <br />
          This is a simple popup.
        </Popup>
      </Marker>
    </MapContainer>
  );
};

export default MapComponent;

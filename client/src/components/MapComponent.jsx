import React, { useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMap,
  useMapEvents,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-defaulticon-compatibility/dist/leaflet-defaulticon-compatibility.css";
import "leaflet-defaulticon-compatibility";
import axios from "axios";

// Utility Component to recenter the map
const RecenterMap = ({ center }) => {
  const map = useMap();
  if (center) map.setView(center, 13);
  return null;
};

const MapComponent = ({ markers, setMarkers, center }) => {
  const mapRef = useRef();

  // Function to add a new marker
  const addMarker = (position, popup, id) => {
    setMarkers((prevMarkers) => [...prevMarkers, { position, popup, id }]);
  };

  const LogBounds = () => {
    const map = useMapEvents({
      moveend: () => {
        const bounds = map.getBounds(); // Get the current bounds of the map

        axios.get("http://localhost:8000/stations").then((response) => {
          setMarkers([]); // Clear existing markers
          // Process each parent station
          response.data.stations.forEach((element) => {
            let availableChargers = 0;

            // Count available chargers
            element.stations.forEach((station) => {
              if (station.status === "Available") {
                availableChargers++;
              }
            });

            // Properly structure the description for the popup
            const description = `
              ${element.name}
                Available Chargers: ${availableChargers}
            `;

            addMarker(
              [
                element.geoCoordinates.latitude,
                element.geoCoordinates.longitude,
              ],
              description,
              element.id
            );
          });
        });
      },
    });
    return null;
  };

  return (
    <MapContainer
      ref={mapRef}
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
          <Popup>
            <div dangerouslySetInnerHTML={{ __html: marker.popup }} />
          </Popup>
        </Marker>
      ))}
      <LogBounds />
    </MapContainer>
  );
};

export default MapComponent;

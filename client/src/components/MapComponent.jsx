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

// Example marker data

// Utility Component to recenter the map
const RecenterMap = ({ center }) => {
  const map = useMap();
  if (center) map.setView(center, 13);
  return null;
};

const MapComponent = ({ markers, center }) => {
  const mapRef = useRef();

  const addMarker = (position) => {
    setMarkers((prevMarkers) => [
      ...prevMarkers,
      { position, popup: `New Marker ${prevMarkers.length + 1}` },
    ]);
  };

  const LogBounds = () => {
    const map = useMapEvents({
      moveend: () => {
        const bounds = map.getBounds(); // Get the current bounds of the map
        const northeastLat = bounds.getNorthEast().lat; // Northeast corner
        const northeastLng = bounds.getNorthEast().lng; // Northeast corner
        const southwestLat = bounds.getSouthWest().lat; // Southwest corner
        const southwestLng = bounds.getSouthWest().lng; // Southwest corner

        /* Call the Post API to Flo here */
        const postData = {
          zoomLevel: 14,
          bounds: {
            SouthWest: {
              Latitude: 43.252862718786815,
              Longitude: -79.93455302667238,
            },
            NorthEast: {
              Latitude: 43.27036402347989,
              Longitude: -79.87678897332765,
            },
          },
          filter: {
            networkIds: [],
            connectors: null,
            levels: [],
            rates: [],
            statuses: [],
            minChargingSpeed: null,
            maxChargingSpeed: null,
          },
        };

        axios
          .post("https://emobility.flo.ca/v3.0/map/markers/search", postData)
          .then((response) => {
            console.log("Response:", response.data);
          })
          .catch((error) => {
            console.error("Error:", error);
          });

        axios
          .get(
            "https://emobility.flo.ca/v3.0/parks/station/1e0335b4-b6b4-4db3-b32d-9e5bb90ba582"
          )
          .then((response) => {
            console.log("Response:", response);
          })
          .catch((error) => {
            console.error("Error:", error);
          });

        console.log("Northeast corner:", northeastLat, northeastLng); // {lat, lng}
        console.log("Southwest corner:", southwestLat, southwestLng); // {lat, lng}
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
          <Popup>{marker.popup}</Popup>
        </Marker>
      ))}

      <LogBounds />
    </MapContainer>
  );
};

export default MapComponent;

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

const MapComponent = ({ markers, setMarkers, center }) => {
  const mapRef = useRef();

  // Function to add a new marker
  const addMarker = (position, popup) => {
    setMarkers((prevMarkers) => [...prevMarkers, { position, popup }]);
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

        axios.get("http://localhost:8000/stations").then((response) => {
          setMarkers([]);
          //for each parent station
          response.data.stations.forEach((element) => {
            console.log(element);
            let freeChargers = 0;
            let description = element.name + " \n";
            element.stations.forEach((element) => {
              if (element.status == "Available") {
                freeChargers++;
              }
            });
            description += "\n \n Free Chargers: " + freeChargers + "\n";
            addMarker(
              [
                element.geoCoordinates.latitude,
                element.geoCoordinates.longitude,
              ],
              description
            );
          });
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

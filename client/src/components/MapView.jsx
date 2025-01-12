import React, { useState } from "react";
import { MapContainer, TileLayer, Polyline, Marker, Popup } from "react-leaflet";
import axios from "axios";
import { LoadScript } from "@react-google-maps/api";
import PlacesAutocomplete, { geocodeByAddress, getLatLng } from "react-places-autocomplete";
import "leaflet/dist/leaflet.css";

const libraries = ["places"]; // Specify Places API library

const MapView = () => {
  const [route, setRoute] = useState([]);
  const [chargers, setChargers] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");

  const handleSelectOrigin = async (address) => {
    try {
      setOrigin(address);
      const results = await geocodeByAddress(address);
      const latLng = await getLatLng(results[0]);
      console.log("Selected Origin Coordinates:", latLng);
    } catch (error) {
      console.error("Error selecting origin:", error);
    }
  };

  const handleSelectDestination = async (address) => {
    try {
      setDestination(address);
      const results = await geocodeByAddress(address);
      const latLng = await getLatLng(results[0]);
      console.log("Selected Destination Coordinates:", latLng);
    } catch (error) {
      console.error("Error selecting destination:", error);
    }
  };

  const fetchData = async () => {
    if (!origin || !destination) {
      setError("Please enter both origin and destination.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await axios.get("http://127.0.0.1:8000/chargers-on-route", {
        params: { origin, destination, max_distance: 5 },
      });

      setRoute(response.data.route);
      setChargers(response.data.chargers);
    } catch (err) {
      setError(err.response?.data?.detail || "An error occurred while fetching data.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <LoadScript googleMapsApiKey="AIzaSyB_H1Mb4pSSjLX3Brb9FRYZ9IVPAH0pCT0" libraries={libraries}>
      <div style={{ padding: "20px" }}>
        <h1>Route and Chargers Visualization</h1>
        <div style={{ marginBottom: "20px" }}>
          <PlacesAutocomplete value={origin} onChange={setOrigin} onSelect={handleSelectOrigin}>
            {({ getInputProps, suggestions, getSuggestionItemProps, loading }) => (
              <div>
                <label>Origin:</label>
                <input
                  {...getInputProps({
                    placeholder: "Enter origin",
                    className: "location-search-input",
                    style: { marginLeft: "10px", marginRight: "20px" },
                  })}
                />
                <div className="autocomplete-dropdown-container">
                  {loading && <div>Loading...</div>}
                  {suggestions.map((suggestion, index) => {
                    const className = suggestion.active ? "suggestion-item--active" : "suggestion-item";
                    return (
                      <div
                        key={index} // Unique key added here
                        {...getSuggestionItemProps(suggestion, {
                          className,
                          style: { backgroundColor: suggestion.active ? "#fafafa" : "#ffffff", cursor: "pointer" },
                        })}
                      >
                        <span>{suggestion.description}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </PlacesAutocomplete>

          <PlacesAutocomplete value={destination} onChange={setDestination} onSelect={handleSelectDestination}>
            {({ getInputProps, suggestions, getSuggestionItemProps, loading }) => (
              <div>
                <label>Destination:</label>
                <input
                  {...getInputProps({
                    placeholder: "Enter destination",
                    className: "location-search-input",
                    style: { marginLeft: "10px" },
                  })}
                />
                <div className="autocomplete-dropdown-container">
                  {loading && <div>Loading...</div>}
                  {suggestions.map((suggestion, index) => {
                    const className = suggestion.active ? "suggestion-item--active" : "suggestion-item";
                    return (
                      <div
                        key={index} // Unique key added here
                        {...getSuggestionItemProps(suggestion, {
                          className,
                          style: { backgroundColor: suggestion.active ? "#fafafa" : "#ffffff", cursor: "pointer" },
                        })}
                      >
                        <span>{suggestion.description}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </PlacesAutocomplete>

          <button onClick={fetchData} style={{ marginLeft: "20px" }}>
            Show Route
          </button>
        </div>

        {loading && <p>Loading route and chargers...</p>}
        {error && <p style={{ color: "red" }}>{error}</p>}

        <div style={{ height: "500px", width: "100%", marginTop: "20px" }}>
          <MapContainer center={[43.2557, -79.8711]} zoom={13} style={{ height: "100%", width: "100%" }}>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />

            {route.length > 0 && <Polyline positions={route.map((point) => [point.lat, point.lng])} color="blue" weight={4} />}
            {chargers.map((charger) => (
              <Marker
                key={charger.id}
                position={[charger.geoCoordinates.latitude, charger.geoCoordinates.longitude]}
              >
                <Popup>
                  <strong>{charger.name}</strong>
                  <br />
                  Latitude: {charger.geoCoordinates.latitude}
                  <br />
                  Longitude: {charger.geoCoordinates.longitude}
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      </div>
    </LoadScript>
  );
};

export default MapView;

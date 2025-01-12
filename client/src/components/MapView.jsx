import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import "./MapView.css"; // Custom styles for enhanced UI

const GOOGLE_MAPS_API_KEY = "AIzaSyB_H1Mb4pSSjLX3Brb9FRYZ9IVPAH0pCT0"; // Replace with your API Key

const MapView = () => {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const mapRef = useRef(null);
  const directionsServiceRef = useRef(null);
  const directionsRendererRef = useRef(null);
  const originAutocompleteRef = useRef(null);
  const destinationAutocompleteRef = useRef(null);

  // Initialize Google Maps and Directions API
  useEffect(() => {
    const initializeGoogleMaps = () => {
      directionsServiceRef.current = new google.maps.DirectionsService();
      directionsRendererRef.current = new google.maps.DirectionsRenderer();

      const map = new google.maps.Map(mapRef.current, {
        center: { lat: 43.2557, lng: -79.8711 }, // Default location
        zoom: 13,
        styles: [
          {
            featureType: "poi",
            elementType: "labels.text.fill",
            stylers: [{ color: "#746855" }],
          },
          {
            featureType: "poi.park",
            elementType: "geometry.fill",
            stylers: [{ color: "#d6e6c3" }],
          },
        ], // Custom map styling
      });

      directionsRendererRef.current.setMap(map);

      // Set up autocomplete for origin and destination
      originAutocompleteRef.current = new google.maps.places.Autocomplete(
        document.getElementById("origin-input")
      );
      destinationAutocompleteRef.current = new google.maps.places.Autocomplete(
        document.getElementById("destination-input")
      );

      originAutocompleteRef.current.addListener("place_changed", () => {
        const place = originAutocompleteRef.current.getPlace();
        setOrigin(place.formatted_address || place.name);
      });

      destinationAutocompleteRef.current.addListener("place_changed", () => {
        const place = destinationAutocompleteRef.current.getPlace();
        setDestination(place.formatted_address || place.name);
      });
    };

    if (!window.google) {
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&libraries=places`;
      script.async = true;
      script.defer = true;
      script.onload = initializeGoogleMaps;
      document.body.appendChild(script);
    } else {
      initializeGoogleMaps();
    }
  }, []);

  const handleRouteCalculation = async () => {
    if (!origin || !destination) {
      alert("Please enter both origin and destination.");
      return;
    }

    try {
      const geocodeAddress = async (address) => {
        const response = await axios.get(
          `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(
            address
          )}&key=${GOOGLE_MAPS_API_KEY}`
        );
        const location = response.data.results[0].geometry.location;
        return { lat: location.lat, lng: location.lng };
      };

      const originCoords = await geocodeAddress(origin);
      const destinationCoords = await geocodeAddress(destination);

      // Get route and charger data
      const directionsResponse = await directionsServiceRef.current.route({
        origin: originCoords,
        destination: destinationCoords,
        travelMode: google.maps.TravelMode.DRIVING,
      });

      directionsRendererRef.current.setDirections(directionsResponse);

      const response = await axios.get("http://127.0.0.1:8000/chargers-on-route", {
        params: {
          origin: `${originCoords.lat},${originCoords.lng}`,
          destination: `${destinationCoords.lat},${destinationCoords.lng}`,
          max_distance: 0.5, // Adjust as needed
        },
      });

      const map = directionsRendererRef.current.getMap();
      response.data.chargers.forEach((charger) => {
        const marker = new google.maps.Marker({
          position: {
            lat: charger.geoCoordinates.latitude,
            lng: charger.geoCoordinates.longitude,
          },
          map: map,
          title: charger.name,
          icon: {
            url: "https://maps.google.com/mapfiles/ms/icons/green-dot.png",
          },
        });

        // Create an info window for each marker
        const infoWindow = new google.maps.InfoWindow({
          content: `
            <div style="font-family: Arial, sans-serif; font-size: 14px;">
              <h3 style="margin: 0;">${charger.name}</h3>
              <p><strong>Total Chargers:</strong> ${charger.totalChargers || "Unknown"}</p>
              <p><strong>Available Chargers:</strong> ${charger.availableChargers || "Unknown"}</p>
              <p><strong>Average Charging Speed:</strong> ${
                charger.averageChargingSpeed ? `${charger.averageChargingSpeed} kW` : "Unknown"
              }</p>
            </div>
          `,
        });

        // Add click event to open the info window
        marker.addListener("click", () => {
          infoWindow.open(map, marker);
        });
      });
    } catch (error) {
      console.error("Error calculating route:", error);
      alert("Failed to calculate route. Please try again.");
    }
  };

  return (
    <div className="map-view-container">
      <h1 className="title">Google Maps API Route and Chargers</h1>
      <div className="input-container">
        <input
          id="origin-input"
          type="text"
          value={origin}
          onChange={(e) => setOrigin(e.target.value)}
          placeholder="Enter origin"
          className="input-box"
        />
        <input
          id="destination-input"
          type="text"
          value={destination}
          onChange={(e) => setDestination(e.target.value)}
          placeholder="Enter destination"
          className="input-box"
        />
        <button onClick={handleRouteCalculation} className="calculate-button">
          Calculate Route
        </button>
      </div>

      <div ref={mapRef} className="map-container"></div>
    </div>
  );
};

export default MapView;

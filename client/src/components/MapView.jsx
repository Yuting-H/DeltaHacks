import React, { useEffect, useRef, useState } from "react";
import axios from "axios";

const GOOGLE_MAPS_API_KEY = "AIzaSyB_H1Mb4pSSjLX3Brb9FRYZ9IVPAH0pCT0"; // Replace with your actual API key

const MapView = () => {
  const mapRef = useRef(null);
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [chargers, setChargers] = useState([]);
  const directionsServiceRef = useRef(null);
  const directionsRendererRef = useRef(null);

  const autocompleteRefs = {
    origin: useRef(null),
    destination: useRef(null),
  };

  // Load Google Maps script dynamically
  useEffect(() => {
    const loadGoogleMapsApi = () => {
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&libraries=places`;
      script.async = true;
      script.defer = true;
      script.onload = initializeMap;
      document.body.appendChild(script);
    };

    loadGoogleMapsApi();
  }, []);

  const initializeMap = () => {
    const map = new google.maps.Map(mapRef.current, {
      center: { lat: 43.2557, lng: -79.8711 },
      zoom: 13,
    });

    directionsServiceRef.current = new google.maps.DirectionsService();
    directionsRendererRef.current = new google.maps.DirectionsRenderer();
    directionsRendererRef.current.setMap(map);

    // Initialize Autocomplete
    autocompleteRefs.origin.current = new google.maps.places.Autocomplete(
      document.getElementById("origin-input")
    );
    autocompleteRefs.origin.current.addListener("place_changed", () => {
      const place = autocompleteRefs.origin.current.getPlace();
      if (place.geometry) {
        setOrigin(place.formatted_address || place.name);
      }
    });

    autocompleteRefs.destination.current = new google.maps.places.Autocomplete(
      document.getElementById("destination-input")
    );
    autocompleteRefs.destination.current.addListener("place_changed", () => {
      const place = autocompleteRefs.destination.current.getPlace();
      if (place.geometry) {
        setDestination(place.formatted_address || place.name);
      }
    });
  };

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

      const routePolyline = directionsResponse.routes[0].overview_polyline;

      // Fetch chargers along the route
      const response = await axios.get("http://127.0.0.1:8000/chargers-on-route", {
        params: {
          origin: `${originCoords.lat},${originCoords.lng}`,
          destination: `${destinationCoords.lat},${destinationCoords.lng}`,
          max_distance: 0.5,
        },
      });

      setChargers(response.data.chargers);

      // Add chargers to the map
      const map = directionsRendererRef.current.getMap();
      response.data.chargers.forEach((charger) => {
        new google.maps.Marker({
          position: {
            lat: charger.geoCoordinates.latitude,
            lng: charger.geoCoordinates.longitude,
          },
          map: map,
          title: charger.name,
        });
      });
    } catch (error) {
      console.error("Error calculating route:", error);
      alert("Failed to calculate route. Please try again.");
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>Google Maps API Route and Chargers</h1>
      <div style={{ marginBottom: "20px" }}>
        <div>
          <label>Origin: </label>
          <input
            type="text"
            id="origin-input"
            placeholder="Enter origin address"
            style={{ marginRight: "10px", width: "300px" }}
          />
        </div>
        <div style={{ marginTop: "10px" }}>
          <label>Destination: </label>
          <input
            type="text"
            id="destination-input"
            placeholder="Enter destination address"
            style={{ width: "300px" }}
          />
        </div>
        <button
          onClick={handleRouteCalculation}
          style={{ marginTop: "20px", padding: "10px 20px" }}
        >
          Calculate Route
        </button>
      </div>
      <div
        ref={mapRef}
        style={{
          height: "500px",
          width: "100%",
          border: "1px solid #ccc",
          marginTop: "20px",
        }}
      ></div>
    </div>
  );
};

export default MapView;

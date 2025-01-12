import React from "react";
import { useState } from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import MapComponent from "./components/MapComponent";
import MarkerListComponent from "./components/MarkerListComponent";
import MapView from "./components/MapView";

const App = () => {
  // Initial markers
  const initialMarkers = [
    { position: [43.25, -79.84], popup: "Marker 1", id: "" },
  ];
  const [markers, setMarkers] = useState(initialMarkers);

  const [selectedMarker, setSelectedMarker] = useState(null);

  const handleMarkerClick = (position) => {
    setSelectedMarker(position);
  };

  return (
    <Router>
      <div>
        <nav style={{ padding: "10px", borderBottom: "1px solid #ccc" }}>
          <Link
            to="/"
            style={{ marginRight: "10px" }}>
            Home
          </Link>
          <Link
            to="/map-view"
            style={{ marginRight: "10px" }}>
            Route MapView
          </Link>
        </nav>

        <Routes>
          {/* Home Page with MapComponent and MarkerList */}
          <Route
            path="/"
            element={
              <div style={{ display: "flex" }}>
                <MarkerListComponent
                  markers={markers}
                  onMarkerClick={handleMarkerClick}
                  handleFeedBack={() => {
                    console.log("Feedback");
                  }}
                />
                <MapComponent
                  markers={markers}
                  setMarkers={setMarkers}
                />
              </div>
            }
          />

          {/* MapView Page for Route Visualization */}
          <Route
            path="/map-view"
            element={<MapView />}
          />
        </Routes>
      </div>
    </Router>
  );
};

export default App;

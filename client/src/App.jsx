import React, { useState } from "react";
import MapComponent from "./components/MapComponent";
import MarkerListComponent from "./components/MarkerListComponent";

const App = () => {
  // Initial markers
  const [markers, setMarkers] = useState([
    { position: [51.505, -0.09], popup: "Marker 1: Central London" },
    { position: [51.515, -0.1], popup: "Marker 2: North London" },
    { position: [51.495, -0.08], popup: "Marker 3: South London" },
  ]);

  const [selectedMarker, setSelectedMarker] = useState(null);

  const handleMarkerClick = (position) => {
    setSelectedMarker(position);
  };

  return (
    <div style={{ display: "flex" }}>
      <MarkerListComponent
        markers={markers}
        onMarkerClick={handleMarkerClick}
      />
      <MapComponent
        markers={markers}
        center={selectedMarker}
      />
    </div>
  );
};

export default App;

import React, { useState } from "react";
import MapComponent from "./components/MapComponent";
import MarkerListComponent from "./components/MarkerListComponent";

const App = () => {
  // Initial markers
  const markers = [
    { position: [43.25, -79.84], popup: "Marker 1" },
    { position: [43.255, -79.845], popup: "Marker 2" },
    { position: [43.245, -79.84], popup: "Marker 3" },
  ];

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

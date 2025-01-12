import React from "react";
import ModalExample from "./modal.jsx";

const MarkerListComponent = ({ markers, onMarkerClick }) => {
  return (
    <div
      style={{
        width: "30%",
        height: "100vh",
        padding: "1rem",
        overflowY: "auto",
        background: "#f8f9fa",
      }}>
      <h3>Markers List</h3>
      <ul style={{ listStyleType: "none", padding: 0 }}>
        {markers.map((marker, index) => (
          <li
            key={index}
            style={{
              padding: "0.5rem",
              margin: "0.5rem 0",
              border: "1px solid #ddd",
              borderRadius: "4px",
              background: "#fff",
            }}>
            <div
              onClick={() => onMarkerClick(marker.position)}
              style={{ cursor: "pointer", fontWeight: "bold" }}>
              {marker.popup}
            </div>
            {/* Include only the modal button */}
            <ModalExample marker={marker} />
          </li>
        ))}
      </ul>
    </div>
  );
};

export default MarkerListComponent;

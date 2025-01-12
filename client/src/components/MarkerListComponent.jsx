import axios from "axios";
import React from "react";
import Modal from "./modal.jsx";

const MarkerListComponent = ({ markers, onMarkerClick, handleFeedBack }) => {
  return (
    <div
      style={{
        width: "30%",
        height: "100vh",
        padding: "1rem",
        overflowY: "auto",
        background: "#f8f9fa",
      }}>
      <h3>Marker List</h3>
      <ul style={{ listStyleType: "none", padding: 0 }}>
        {markers.map((marker, index) => (
          <li
            key={index}
            style={{
              padding: "0.5rem",
              margin: "0.5rem 0",
              border: "1px solid #ddd",
              borderRadius: "4px",
              cursor: "pointer",
              background: "#fff",
            }}
            onClick={() => onMarkerClick(marker.position)}>
            {marker.popup}

            <Modal marker={marker} />
          </li>
        ))}
      </ul>
    </div>
  );
};

export default MarkerListComponent;

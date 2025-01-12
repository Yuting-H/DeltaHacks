import React, { useState, useEffect } from "react";
import axios from "axios";

const ModalExample = (marker) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [stations, setStations] = useState([]);
  const [fullData, setFullData] = useState({}); // To hold the full data for PUT request

  const openModal = async () => {
    setIsModalOpen(true);
    await fetchStations();
  };

  const closeModal = () => setIsModalOpen(false);

  const fetchStations = async () => {
    try {
      const response = await axios.get(`http://localhost:8000/data/${marker.marker.id}`);
      setStations(response.data.stations);
      setFullData(response.data); // Store the full data (including non-station details) for updates
    } catch (error) {
      console.error("Error fetching stations:", error);
    }
  };

  const handleStatusChange = (stationId, newStatus) => {
    setStations((prevStations) =>
      prevStations.map((station) =>
        station.id === stationId ? { ...station, status: newStatus } : station
      )
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const updatedData = {
        ...fullData, // Include the original data
        stations, // Update only the stations array with the new statuses
      };
      await axios.put(`http://localhost:8000/data/${marker.marker.id}`, updatedData);
      console.log("Station statuses updated successfully!");
      closeModal();
    } catch (error) {
      console.error("Error updating station statuses:", error);
    }
  };

  return (
    <div>
      {/* Button to open the modal */}
      <button
        onClick={openModal}
        style={{
          backgroundColor: "#007bff",
          color: "#fff",
          border: "none",
          padding: "0.5rem 1rem",
          borderRadius: "4px",
          cursor: "pointer",
          fontWeight: "bold",
          fontSize: "0.9rem",
        }}>
        Report
      </button>

      {/* Modal */}
      {isModalOpen && (
        <div style={modalStyles.overlay}>
          <div style={modalStyles.modal}>
            <h2 style={{ marginBottom: "20px" }}>Update Charger Status</h2>
            <form onSubmit={handleSubmit}>
              {stations.map((station) => (
                <div key={station.id} style={{ marginBottom: "15px", textAlign: "left" }}>
                  <label>
                    <strong>{station.name}</strong>
                  </label>
                  <select
                    value={station.status}
                    onChange={(e) => handleStatusChange(station.id, e.target.value)}
                    style={{
                      marginLeft: "10px",
                      padding: "0.3rem",
                      borderRadius: "4px",
                      border: "1px solid #ddd",
                    }}>
                    <option value="Available">Available</option>
                    <option value="In-Use">In-Use</option>
                    <option value="Degraded">Degraded</option>
                    <option value="Unknown">Unknown</option>
                  </select>
                </div>
              ))}
              <button
                type="submit"
                style={{
                  backgroundColor: "#28a745",
                  color: "#fff",
                  border: "none",
                  padding: "0.5rem 1rem",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontWeight: "bold",
                  marginTop: "10px",
                  marginRight: "10px",
                }}>
                Submit
              </button>
              <button
                type="button"
                onClick={closeModal}
                style={{
                  backgroundColor: "#dc3545",
                  color: "#fff",
                  border: "none",
                  padding: "0.5rem 1rem",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontWeight: "bold",
                }}>
                Close
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

const modalStyles = {
  overlay: {
    position: "fixed",
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 1000,
  },
  modal: {
    backgroundColor: "#fff",
    padding: "20px",
    borderRadius: "8px",
    boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
    textAlign: "center",
    maxWidth: "500px",
    width: "100%",
  },
};

export default ModalExample;

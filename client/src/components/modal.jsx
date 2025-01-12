import React, { useState, useEffect } from "react";
import axios from "axios";

const ModalExample = (marker) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [stations, setStations] = useState([]);
  const [fullData, setFullData] = useState({});

  const openModal = () => {
    setIsModalOpen(true);
    fetchStations();
  };

  const closeModal = () => setIsModalOpen(false);

  const fetchStations = async () => {
    try {
      const response = await axios.get(`http://localhost:8000/data/${marker.marker.id}`);
      setStations(response.data.stations);
      setFullData(response.data); // Store the entire object for the PUT request
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
        stations, // Update the stations array with the new statuses
      };
      await axios.put(`http://localhost:8000/data/${marker.marker.id}`, updatedData);
      console.log("Status updated successfully");
      closeModal();
    } catch (error) {
      console.error("Error updating status:", error);
    }
  };

  return (
      <div>
        {/* Button to open the modal */}
        <button onClick={openModal}>Open Modal</button>
        {isModalOpen && (
            <form onSubmit={handleSubmit}>
              <div style={modalStyles.overlay}>
                <div style={modalStyles.modal}>
                  <h2>Submit Charging Information</h2>
                  <div>
                    {stations.map((station) => (
                        <div key={station.id} style={{ marginBottom: "10px" }}>
                          <span>{station.name}</span>
                          <select
                              value={station.status}
                              onChange={(e) =>
                                  handleStatusChange(station.id, e.target.value)
                              }
                              style={{ marginLeft: "10px" }}>
                            <option value="Available">Available</option>
                            <option value="In-Use">In-Use</option>
                            <option value="Degraded">Degraded</option>
                          </select>
                        </div>
                    ))}
                  </div>
                  <button type="submit">Submit</button>
                  <button type="button" onClick={closeModal}>
                    Close
                  </button>
                </div>
              </div>
            </form>
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
    maxWidth: "400px",
    width: "100%",
  },
};

export default ModalExample;

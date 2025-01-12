import React, { useState } from "react";
import axios from "axios";
const ModalExample = (marker) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const openModal = () => setIsModalOpen(true);
  const closeModal = () => setIsModalOpen(false);

  return (
    <div>
      {/* Button to open the modal */}
      <button onClick={openModal}>Open Modal</button>
      {isModalOpen && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            axios
              .get("http://localhost:8000/data/" + marker.marker.id)
              .then((response) => {
                console.log(response.data);
              });

            closeModal();
          }}>
          <div style={modalStyles.overlay}>
            <div style={modalStyles.modal}>
              <h2>Submit Charging Information</h2>
              <div></div>
              <button type="submit">Submit</button>

              <button
                type="button"
                onClick={closeModal}>
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
  },
};

export default ModalExample;

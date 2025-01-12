import React from "react";
import "./LoyaltyProgram.css";

const LoyaltyProgram = () => {
  return (
    <div className="loyalty-program-container">
      <h1 className="title">Reward & Loyalty Program</h1>
      <p className="description">
        Join our Reward & Loyalty Program to earn exciting rewards as you review,
        update, and charge at our EV stations! Climb the tiers and enjoy
        exclusive benefits.
      </p>

      <div className="tiers-container">
        {/* Bronze Tier */}
        <div className="tier bronze">
          <div className="tier-header">
            <h2>Bronze</h2>
          </div>
          <p><strong>Starting Tier</strong></p>
          <ul>
            <li>1 Air Mile for every 10 reviews or status updates</li>
          </ul>
        </div>

        {/* Silver Tier */}
        <div className="tier silver">
          <div className="tier-header">
            <h2>Silver</h2>
          </div>
          <p><strong>Requirement:</strong> 100 reviews</p>
          <ul>
            <li>1 Air Mile for every 5 reviews or status updates</li>
            <li>10% off every 10 charges</li>
          </ul>
        </div>

        {/* Gold Tier */}
        <div className="tier gold">
          <div className="tier-header">
            <h2>Gold</h2>
          </div>
          <p><strong>Requirement:</strong> 250 reviews</p>
          <ul>
            <li>1 Air Mile for every 3 reviews or status updates</li>
            <li>10% off every 10 charges</li>
            <li>100 Scene Points every other use</li>
          </ul>
        </div>

        {/* Platinum Tier */}
        <div className="tier platinum">
          <div className="tier-header">
            <h2>Platinum</h2>
          </div>
          <p><strong>Requirement:</strong> 500 reviews</p>
          <ul>
            <li>1 Air Mile for every review</li>
            <li>200 Scene Points every other use</li>
            <li>1 Free Full Charge every 15 reviews</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default LoyaltyProgram;


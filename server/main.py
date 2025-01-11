from fastapi import FastAPI, HTTPException
from geopy.distance import geodesic
import json
import os

app = FastAPI()


json_file_path = os.path.join(os.path.dirname(__file__), "unique_parks.json")
with open(json_file_path, "r") as file:
    charging_data = json.load(file)


@app.get("/")
async def root():
    """
    Root endpoint providing API details.
    """
    return {
        "message": "Welcome to the EV Charging Station Finder API!",
        "endpoints": {
            "/stations": "Get stations within a given radius (params: lat, lon, radius_km)",
            "/station/{station_id}": "Get details for a specific station by ID",
        },
    }


@app.get("/stations")
async def get_stations_within_radius(lat: float, lon: float, radius_km: float = 5.0):
    """
    Get charging stations within a given radius (default: 5km) of provided coordinates.
    """
    user_location = (lat, lon)
    stations_within_radius = []

    for park in charging_data:
        park_location = (
            park["geoCoordinates"]["latitude"],
            park["geoCoordinates"]["longitude"],
        )
        distance = geodesic(user_location, park_location).km
        if distance <= radius_km:
            park_info = {
                "id": park["id"],
                "name": park["name"],
                "geoCoordinates": park["geoCoordinates"],
                "distance_km": round(distance, 2),
                "stations": [
                    {
                        "id": station["id"],
                        "name": station["name"],
                        "status": station["status"],
                        "level": station["level"],
                        "freeOfCharge": station["freeOfCharge"],
                    }
                    for station in park["stations"]
                ],
            }
            stations_within_radius.append(park_info)

    if not stations_within_radius:
        raise HTTPException(
            status_code=404,
            detail="No charging stations found within the given radius.",
        )

    return {"stations": stations_within_radius}


@app.get("/station/{station_id}")
async def get_station_details(station_id: str):
    """
    Get details of a specific charging station by its ID.
    """
    for park in charging_data:
        for station in park["stations"]:
            if station["id"] == station_id:
                station_details = {
                    "park_id": park["id"],
                    "park_name": park["name"],
                    "geoCoordinates": park["geoCoordinates"],
                    "station": {
                        "id": station["id"],
                        "name": station["name"],
                        "status": station["status"],
                        "level": station["level"],
                        "freeOfCharge": station["freeOfCharge"],
                        "connectors": station["connectors"],
                        "chargingSpeed": station["chargingSpeed"],
                    },
                }
                return {"station_details": station_details}

    raise HTTPException(status_code=404, detail="Charging station not found.")

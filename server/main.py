from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import httpx
import json
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from calculus import get_bounds_zoom_level
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_DB_USER = os.getenv("MONGO_DB_USER")
MONGO_DB_PASSWORD = os.getenv("MONGO_DB_PASSWORD")
MONGO_DB_URI = os.getenv("MONGO_DB_URI")


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_URL = "https://emobility.flo.ca/v3.0/map/markers/search"
uri = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASSWORD}@{MONGO_DB_URI}"

# MongoDB Client Setup
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['betabase']  # Accessing the existing database 'betabase'
stations_collection = db['stations']  # Accessing the 'stations' collection


@app.post("/find_parks")
async def find_parks(input_data: dict):
    """
    Zoom into each cluster until parks are found and store all unique parks in a file.
    """
    bounds = input_data["bounds"]
    unique_parks = set()  # Use a set to store unique parks by ID or unique identifier
    zoom_level = get_bounds_zoom_level(bounds, {"height": 800, "width": 800})
    print(f"Zoom level: {zoom_level}")

    async def zoom_into_cluster(cluster_bounds, zoom_level=zoom_level, max_zoom=19):
        """
        Recursively zoom into clusters and collect parks.
        """
        while zoom_level <= max_zoom:
            # Prepare the request payload
            payload = {
                "zoomLevel": zoom_level,
                "bounds": {
                    "southWest": {
                        "latitude": cluster_bounds["SouthWest"]["Latitude"],
                        "longitude": cluster_bounds["SouthWest"]["Longitude"]
                    },
                    "northEast": {
                        "latitude": cluster_bounds["NorthEast"]["Latitude"],
                        "longitude": cluster_bounds["NorthEast"]["Longitude"]
                    }
                },
                "filter": {
                    "networkIds": [],
                    "connectors": None,
                    "levels": [],
                    "rates": [],
                    "statuses": [],
                    "minChargingSpeed": None,
                    "maxChargingSpeed": None
                }
            }

            # Query the API
            async with httpx.AsyncClient() as client:
                response = await client.post(API_URL, json=payload)
                data = response.json()

            # Parse response
            parks = data.get("parks", [])
            clusters = data.get("clusters", [])

            # If parks are found, add them to the set
            for park in parks:
                unique_parks.add(json.dumps(park))  # Serialize to avoid duplication

            # If no clusters remain, return
            if not clusters:
                return

            # Otherwise, zoom into each cluster
            for cluster in clusters:
                cluster_lat = cluster["geoCoordinates"]["latitude"]
                cluster_lon = cluster["geoCoordinates"]["longitude"]

                # Define smaller bounds around the cluster's geoCoordinates
                delta = 0.2  # Adjust this to control the zoom-in granularity
                new_bounds = {
                    "SouthWest": {
                        "Latitude": cluster_lat - delta,
                        "Longitude": cluster_lon - delta
                    },
                    "NorthEast": {
                        "Latitude": cluster_lat + delta,
                        "Longitude": cluster_lon + delta
                    }
                }

                # Recursively zoom into the cluster
                await zoom_into_cluster(new_bounds, zoom_level + 1, max_zoom)

            # Break out of the loop once recursion handles all clusters
            break

    # Start with the initial bounds
    await zoom_into_cluster(bounds)

    # Insert unique parks into the MongoDB time-series collection
    for park_json in unique_parks:
        park = json.loads(park_json)
        park['timestamp'] = datetime.utcnow()  # Add a timestamp for the time-series
        park['metadata'] = {"location": park.get("name", "Unknown")}  # Add metadata (e.g., location name)

        # Insert the park data into the time-series collection
        stations_collection.insert_one(park)
        print(park)


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

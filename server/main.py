from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
import httpx
import json
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from calculus import get_bounds_zoom_level
from dotenv import load_dotenv
from pydantic import BaseModel, RootModel
from typing import List, Dict, Optional
from datetime import datetime
from bson import ObjectId
from geopy.distance import geodesic
import requests
import os

load_dotenv()

MONGO_DB_USER = os.getenv("MONGO_DB_USER")
MONGO_DB_PASSWORD = os.getenv("MONGO_DB_PASSWORD")
MONGO_DB_URI = os.getenv("MONGO_DB_URI")

# Debugging: Print environment variables to verify they are loaded
print(f"MONGO_DB_USER: {MONGO_DB_USER}")
print(f"MONGO_DB_PASSWORD: {MONGO_DB_PASSWORD}")
print(f"MONGO_DB_URI: {MONGO_DB_URI}")

origins = ["*"]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Construct MongoDB URI
uri = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASSWORD}@{MONGO_DB_URI}"
API_URL = "https://emobility.flo.ca/v3.0/map/markers/search"
uri = "mongodb+srv://deltaback:aoqQZ9PfaKZTCFxA@electricbuddy.0qhs8.mongodb.net/?retryWrites=true&w=majority&appName=electricbuddy"


# Pydantic models for request validation
class StationDetails(BaseModel):
    id: str
    connectors: List[str]
    status: str
    level: str
    freeOfCharge: bool
    name: str
    chargingSpeed: int


class GeoCoordinates(BaseModel):
    latitude: float
    longitude: float


class Metadata(BaseModel):
    location: str


class Schema(BaseModel):
    name: str
    stations: List[StationDetails]
    geoCoordinates: GeoCoordinates
    id: str
    networkId: int
    metadata: Metadata
    address: str  # New field for address


class Station(BaseModel):
    id: str
    connectors: List[str]
    status: str
    level: str
    freeOfCharge: bool
    name: str
    chargingSpeed: int


class DataModel(BaseModel):
    id: str
    address: str
    geoCoordinates: GeoCoordinates
    metadata: dict
    name: str
    networkId: int
    stations: List[Station]
    timestamp: Optional[int]

    # Custom method to serialize datetime to integer timestamp
    @classmethod
    def from_mongo(cls, data: dict):
        # Convert datetime to timestamp
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = int(data["timestamp"].timestamp() * 1000)  # Convert to milliseconds
        return cls(**data)

    def to_mongo(self):
        # Optionally, convert timestamp back to datetime when saving (if necessary)
        return self.dict()


def mongo_connect(collection="stations"):
    # MongoDB connection setup
    try:
        client = MongoClient(uri, server_api=ServerApi("1"))
        db = client["betabase"]  # Access the database
        stations_collection = db[collection]  # Access the stations collection
        print("MongoDB connection successful!")
        return stations_collection
    except Exception as e:
        raise Exception(f"Failed to connect to MongoDB: {e}")


def upsert_schema_in_db(park_data):
    """
    Insert park data if its ID does not exist in the collection.
    If the ID already exists, do nothing.
    Fetch the address using the station ID from the first station in the park's 'stations' list.
    Adds the current timestamp as 'lastUpdated'.
    """
    stations_collection = mongo_connect("baobao")

    # Add the current timestamp as 'lastUpdated'
    park_data["lastUpdated"] = int(datetime.utcnow().timestamp() * 1000)  # Use milliseconds for consistency

    # Get the park's ID
    park_id = park_data.get("id")

    # If the park does not have an ID, raise an error
    if not park_id:
        raise ValueError("Park data must have an 'id' field")

    # Check if a document with the same ID already exists
    existing_park = stations_collection.find_one({"id": park_id})

    if existing_park:
        print(f"Park with ID: {park_id} already exists. Skipping insert.")
        return  # Do nothing if the park already exists

    # Extract the first station's ID for querying the address
    stations = park_data.get("stations", [])
    if not stations:
        raise ValueError(f"Park data with ID {park_id} must have at least one station")

    # Use the ID of the first station in the list
    station_id = stations[0]["id"]

    # Fetch the address using the station ID if 'address' is not provided in the data
    if "address" not in park_data or not park_data["address"]:
        park_data["address"] = fetch_address_from_api(station_id)

    # Perform the insertion if no document with the same ID exists
    stations_collection.insert_one(park_data)
    print(f"Inserted new park with ID: {park_id}")


def fetch_address_from_api(station_id):
    """
    Fetch the address of a station using its ID from the FLO API.
    """
    api_url = f"https://emobility.flo.ca/v3.0/parks/station/{station_id}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an error for HTTP codes 4xx/5xx
        data = response.json()

        # Extract the address from the response
        return data.get("address", "Unknown address")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching address for station_id {station_id}: {e}")
        return "Unknown address"

# Function to process and store parks data
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

    number_of_parks = 0

    # Upsert unique parks into the MongoDB time-series collection
    for park_json in unique_parks:
        park = json.loads(park_json)
        park['timestamp'] = datetime.utcnow()  # Add a timestamp for the time-series
        park['metadata'] = {"location": park.get("name", "Unknown")}  # Add metadata (e.g., location name)

        # Upsert the park data into the time-series collection
        upsert_schema_in_db(park)
        number_of_parks += 1

    return {"message": f"Found and stored {number_of_parks} unique parks."}


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
    stations_collection = mongo_connect()
    user_location = (lat, lon)
    stations_within_radius = []

    # Retrieve all stations from the database
    try:
        stations = stations_collection.find()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying database: {e}")

    for station in stations:
        station_location = (
            station["geoCoordinates"]["latitude"],
            station["geoCoordinates"]["longitude"],
        )
        distance = geodesic(user_location, station_location).km
        print(f"Station ID: {station['id']}, Distance: {distance:.2f} km")  # Debugging line
        if distance <= radius_km:
            station_info = {
                "id": station["id"],
                "name": station["name"],
                "geoCoordinates": station["geoCoordinates"],
                "distance_km": round(distance, 2),
                "stations": [
                    {
                        "id": substation["id"],
                        "name": substation["name"],
                        "status": substation["status"],
                        "level": substation["level"],
                        "freeOfCharge": substation["freeOfCharge"],
                    }
                    for substation in station["stations"]
                ],
            }
            stations_within_radius.append(station_info)

    if not stations_within_radius:
        raise HTTPException(
            status_code=404,
            detail="No charging stations found within the given radius.",
        )

    return {"stations": stations_within_radius}


@app.get("/station/{station_id}")
async def get_station_details(station_id: str):
    """
    Get details of a specific charging station by its ID, including nested stations.
    """
    stations_collection = mongo_connect()
    try:
        # Iterate over all parent stations
        for parent_station in stations_collection.find():
            # Check each substation in the "stations" array
            for substation in parent_station.get("stations", []):
                if substation["id"] == station_id:
                    # Return the matching substation with its parent details
                    return {
                        "parent_id": parent_station["id"],
                        "parent_name": parent_station["name"],
                        "geoCoordinates": parent_station["geoCoordinates"],
                        "station": substation,
                    }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying database: {e}")

    # If no match is found
    raise HTTPException(status_code=404, detail="Charging station not found.")


# Convert MongoDB ObjectId to string
def mongo_obj_id(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    return obj


# Modify your endpoint to use the custom from_mongo method
@app.get("/data/{id}", response_model=DataModel)
async def get_data(id: str):
    collection = mongo_connect("baobao")
    data = collection.find_one({"id": id})
    if not data:
        raise HTTPException(status_code=404, detail="Data not found")

    # Convert MongoDB data to DataModel and handle timestamp serialization
    data["_id"] = mongo_obj_id(data["_id"])  # Convert Mongo _id to string
    return DataModel.from_mongo(data)


@app.put("/data/{id}", response_model=DataModel)
async def overwrite_data(id: str, data: DataModel):
    collection = mongo_connect("baobao")
    # Find the document by its "id"
    existing_data = collection.find_one({"id": id})

    if not existing_data:
        raise HTTPException(status_code=404, detail="Data not found")

    # Overwrite the document with the new data
    update_result = collection.replace_one(
        {"id": id},  # Filter to find the document by its "id"
        data.dict()  # Replace the document with the new data (converted to a dictionary)
    )

    if update_result.modified_count > 0:
        return data  # Return the full updated data
    else:
        raise HTTPException(status_code=400, detail="Failed to overwrite data")

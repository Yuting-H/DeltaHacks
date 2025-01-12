
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import httpx
import json
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from calculus import get_bounds_zoom_level
from dotenv import load_dotenv
from pydantic import BaseModel, RootModel
from typing import List, Dict, Optional
from datetime import datetime
from bson import ObjectId
import os
from geopy.distance import geodesic
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

API_URL = "https://emobility.flo.ca/v3.0/map/markers/search"
uri = "mongodb+srv://deltaback:aoqQZ9PfaKZTCFxA@electricbuddy.0qhs8.mongodb.net/?retryWrites=true&w=majority&appName=electricbuddy"

print(uri)

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


# Construct MongoDB URI
uri = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASSWORD}@{MONGO_DB_URI}"

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

app = FastAPI()

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



# Pydantic models for request validation
class TariffDescription(BaseModel):
    fr: str
    en: str

class Tariff(BaseModel):
    id: str
    description: TariffDescription

class Connector(BaseModel):
    type: str
    powerType: str
    power: int

class StationDetails(BaseModel):
    status: str
    level: str
    lastCheckIn: str
    id: str
    connectors: List[Connector]
    tariff: Tariff

# Each station in the list is a dictionary with a single key-value pair
class Station(RootModel[Dict[str, StationDetails]]):
    pass

class Schema(BaseModel):
    pewpew_id: str
    address: str
    stations: List[Station]

# Independent function for upserting a schema
def upsert_schema_in_db(schema: Schema):
    """
    Create or update a document in MongoDB.

    :param schema: The schema to be upserted.
    :return: A message indicating whether the document was created or updated.
    """
    collection = mongo_connect("uxpropertegypt")
    schema_dict = schema.dict(by_alias=True)
    existing_document = collection.find_one({"pewpew_id": schema.pewpew_id})

    if existing_document:
        # Update the existing document
        collection.update_one(
            {"pewpew_id": schema.pewpew_id},
            {"$set": schema_dict}
        )
        return "Document updated successfully."
    else:
        # Insert a new document
        collection.insert_one(schema_dict)
        return "Document created successfully."

# FastAPI endpoint using the independent function
@app.post("/update-schema/")
async def upsert_schema_endpoint(schema: Schema):
    try:
        result_message = upsert_schema_in_db(schema)
        return {"message": result_message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
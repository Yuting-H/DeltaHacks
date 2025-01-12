import logging
from fastapi import FastAPI, HTTPException
from geopy.distance import geodesic
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os
import googlemaps
import polyline
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
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
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# MongoDB connection setup
uri = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASSWORD}@{MONGO_DB_URI}/?retryWrites=true&w=majority"

gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

app = FastAPI()
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

class Address(BaseModel):
    address1: str
    address2: str
    city: str
    country: str
    province: str
    postalCode: str

class DataModel(BaseModel):
    id: str
    address: Address
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


# 1. Welcome Endpoint
@app.get("/")
async def root():
    """
    Welcome endpoint for the EV Charging Finder API.
    """
    return {
        "message": "Welcome to the EV Charging Station Finder API!",
        "endpoints": {
            "/chargers-on-route": "Find chargers along a route (params: origin, destination, max_distance)",
            "/stations": "Get stations within a radius (params: lat, lon, radius_km)",
            "/station/{station_id}": "Get details for a specific station by ID",
            "/parent-stations": "Get all parent stations with their chargers",
        },
    }

# 2. Validate Address using Geocoding API
def validate_address(address):
    """
    Validate an address using the Geocoding API and return lat/lng coordinates.
    If the input is already in lat/lng format, bypass validation.
    """
    lat_lng_pattern = re.compile(r'^-?\d+(\.\d+)?,-?\d+(\.\d+)?$')
    if lat_lng_pattern.match(address):
        lat, lng = map(float, address.split(','))
        return {"lat": lat, "lng": lng}
    geocode_result = gmaps.geocode(address)
    if not geocode_result:
        raise HTTPException(status_code=400, detail=f"Invalid address: {address}")
    location = geocode_result[0]["geometry"]["location"]
    return {"lat": location["lat"], "lng": location["lng"]}

# 3. Get Route Between Two Locations
def get_route_googlemaps(origin, destination):
    """
    Fetch a driving route between two locations using Google Maps Directions API.
    """
    try:
        directions = gmaps.directions(origin, destination, mode="driving")
        if not directions or "overview_polyline" not in directions[0]:
            raise ValueError("No route found in Google Maps response.")
        encoded_polyline = directions[0]["overview_polyline"]["points"]
        route_coords = polyline.decode(encoded_polyline)
        logging.debug(f"Decoded route coordinates: {route_coords}")
        return route_coords
    except Exception as e:
        logging.error(f"Error fetching route from Google Maps: {e}")
        raise HTTPException(status_code=500, detail="Error fetching route from Google Maps API.")

# 4. Check if Charger is Near Route
def is_near_route(charger_coords, route_coords, max_distance=0.5):
    """
    Determine if a charger is within the specified distance of the route.
    """
    for route_point in route_coords:
        distance = geodesic(
            (charger_coords["latitude"], charger_coords["longitude"]),
            (route_point[0], route_point[1])
        ).km
        if distance <= max_distance:
            return True
    return False

# 5. Chargers Along Route Endpoint
@app.get("/chargers-on-route")
async def get_chargers_on_route(origin: str, destination: str, max_distance: float = 0.5):
    stations_collection = mongo_connect("uxpropertegypt")
    try:
        origin_coords = validate_address(origin)
        destination_coords = validate_address(destination)
        route_coords = get_route_googlemaps(origin, destination)
        chargers = list(stations_collection.find())
        chargers_near_route = []

        for charger in chargers:
            if "geoCoordinates" not in charger or not isinstance(charger["geoCoordinates"], dict):
                continue
            if is_near_route(charger["geoCoordinates"], route_coords, max_distance):
                # Summarize the data for this parent station
                total_chargers = len(charger.get("stations", []))
                available_chargers = sum(
                    1 for station in charger.get("stations", []) if station.get("status") == "Available"
                )
                average_speed = (
                    sum(station.get("chargingSpeed", 0) for station in charger.get("stations", [])) / total_chargers
                    if total_chargers > 0
                    else 0
                )
                chargers_near_route.append({
                    "id": charger["id"],
                    "name": charger["name"],
                    "geoCoordinates": charger["geoCoordinates"],
                    "totalChargers": total_chargers,
                    "availableChargers": available_chargers,
                    "averageChargingSpeed": round(average_speed, 2) if total_chargers > 0 else "Unknown"
                })

        if not chargers_near_route:
            raise HTTPException(status_code=404, detail="No chargers found along the route.")

        return {
            "route": route_coords,
            "chargers": chargers_near_route
        }

except Exception as e:
        logging.error(f"Error in /chargers-on-route: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 6. Get Stations Within Radius
@app.get("/stations")
async def get_stations_within_radius(lat: float = 43.252862718786815, lon: float = -79.93455302667238, radius_km: float = 20):
    """
    Get charging stations within a given radius (default: 5km) of provided coordinates.
    """
    stations_collection = mongo_connect("baobao")
    user_location = (lat, lon)
    stations_within_radius = []

    try:
        stations = stations_collection.find()
        logging.debug("Fetched stations from MongoDB.")
    except Exception as e:
        logging.error(f"Error querying database: {e}")
        raise HTTPException(status_code=500, detail=f"Error querying database: {e}")

    for station in stations:
        station_location = (
            station["geoCoordinates"]["latitude"],
            station["geoCoordinates"]["longitude"],
        )
        distance = geodesic(user_location, station_location).km
        if distance <= radius_km:
            address = f"{station['address']['address1']} {station['address']['address2']}, {station['address']['city']}, {station['address']['province']} {station['address']['postalCode']}, {station['address']['country']}".strip()
            stations_within_radius.append({
                "id": station["id"],
                "name": station["name"],
                "geoCoordinates": station["geoCoordinates"],
                "distance_km": round(distance, 2),
                "stations": station["stations"],
                "address": address
            })

    if not stations_within_radius:
        logging.warning("No charging stations found within the given radius.")
        raise HTTPException(
            status_code=404,
            detail="No charging stations found within the given radius.",
        )

    return {"stations": stations_within_radius}

# 7. Get Parent Stations
@app.get("/parent-stations")
async def get_parent_stations():
    """
    Get a list of parent charging stations with all their chargers included.
    """
    stations_collection = mongo_connect("baobao")
    try:
        parent_stations = stations_collection.find()
        results = []

        for parent_station in parent_stations:
            results.append({
                "id": parent_station["id"],
                "name": parent_station["name"],
                "geoCoordinates": parent_station["geoCoordinates"],
                "stations": parent_station.get("stations", []),
            })

        if not results:
            logging.warning("No parent stations found.")
            raise HTTPException(
                status_code=404,
                detail="No parent stations found.",
            )

        return {"parentStations": results}

    except Exception as e:
        logging.error(f"Error retrieving parent stations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving parent stations: {e}",
        )

# 8. Get Station Details by ID
@app.get("/station/{station_id}")
async def get_station_details(station_id: str):
    """
    Get details of a specific charging station by its ID, including nested stations.
    """
    stations_collection = mongo_connect("baobao")
    try:
        for parent_station in stations_collection.find():
            for substation in parent_station.get("stations", []):
                if substation["id"] == station_id:
                    return {
                        "parent_id": parent_station["id"],
                        "parent_name": parent_station["name"],
                        "geoCoordinates": parent_station["geoCoordinates"],
                        "station": substation,
                    }
    except Exception as e:
        logging.error(f"Error querying database: {e}")
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

import logging
from fastapi import FastAPI, HTTPException
from geopy.distance import geodesic
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os
import requests
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
load_dotenv(dotenv_path="C:\\Users\\mckayz\\Documents\\DeltaHacks\\server\\.env")

MONGO_DB_USER = os.getenv("MONGO_DB_USER")
MONGO_DB_PASSWORD = os.getenv("MONGO_DB_PASSWORD")
MONGO_DB_URI = os.getenv("MONGO_DB_URI")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# MongoDB connection setup
uri = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASSWORD}@{MONGO_DB_URI}/?retryWrites=true&w=majority"
# try:
#     client = MongoClient(uri, server_api=ServerApi("1"))
#     db = client["betabase"]
#     stations_collection = db["stations"]
#     logging.info("Connected to MongoDB successfully.")
# except Exception as e:
#     logging.error(f"Failed to connect to MongoDB: {e}")
#     raise e

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
        },
    }

# 2. Validate Address using Geocoding API
def validate_address(address):
    """
    Validate an address using the Geocoding API and return lat/lng coordinates.
    If the input is already in lat/lng format, bypass validation.
    """
    # Check if the input is already latitude/longitude
    lat_lng_pattern = re.compile(r'^-?\d+(\.\d+)?,-?\d+(\.\d+)?$')
    if lat_lng_pattern.match(address):
        lat, lng = map(float, address.split(','))
        return {"lat": lat, "lng": lng}

    # Use Geocoding API for address validation
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": GOOGLE_MAPS_API_KEY}
    response = requests.get(url, params=params)
    data = response.json()
    
    logging.debug(f"Geocoding API response for {address}: {data}")

    if data.get("status") != "OK":
        error_message = data.get("error_message", "Unknown error")
        logging.error(f"Geocoding API error: {data['status']} - {error_message}")
        raise HTTPException(status_code=400, detail=f"400: Invalid address: {address}")
    
    return data["results"][0]["geometry"]["location"]

# 3. Get Route Between Two Locations
def get_route(origin, destination):
    """
    Get the route coordinates between an origin and destination.
    """
    # Validate origin and destination
    origin_coords = validate_address(origin)
    destination_coords = validate_address(destination)

    # Call Directions API
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin_coords['lat']},{origin_coords['lng']}",
        "destination": f"{destination_coords['lat']},{destination_coords['lng']}",
        "key": GOOGLE_MAPS_API_KEY,
    }
    response = requests.get(url, params=params)
    data = response.json()

    logging.debug(f"Google Maps Directions API response: {data}")

    if data.get("status") != "OK":
        error_message = data.get("error_message", "Unknown error")
        logging.error(f"Failed to retrieve route: {data['status']} - {error_message}")
        raise HTTPException(status_code=500, detail=f"Google Maps API error: {error_message}")

    try:
        return [
            step["end_location"]
            for route in data["routes"]
            for leg in route["legs"]
            for step in leg["steps"]
        ]
    except KeyError as e:
        logging.error(f"Error parsing Google Maps API response: {e}")
        raise HTTPException(status_code=500, detail="Error parsing route data.")


# 4. Check if Charger is Near Route
def is_near_route(charger_coords, route_coords, max_distance=0.1):
    """
    Determine if a charger is within the specified distance of the route.
    """
    for route_point in route_coords:
        distance = geodesic(
            (charger_coords["latitude"], charger_coords["longitude"]),
            (route_point["lat"], route_point["lng"])
        ).km
        logging.debug(f"Distance from charger ({charger_coords}) to route point ({route_point}): {distance:.2f} km")
        if distance <= max_distance:
            return True
    return False


# 5. Chargers Along Route Endpoint
@app.get("/chargers-on-route")
async def get_chargers_on_route(origin: str, destination: str, max_distance: float = 0.1):
    """
    Find EV chargers along a route between origin and destination.
    """
    stations_collection = mongo_connect("uxpropertegypt")
    try:
        logging.info(f"Received request: origin={origin}, destination={destination}, max_distance={max_distance}")

        # Step 1: Get the route coordinates
        route_coords = get_route(origin, destination)
        logging.debug(f"Route coordinates: {route_coords}")

        # Step 2: Fetch all chargers from MongoDB
        chargers = list(stations_collection.find())  # Convert cursor to list
        logging.debug(f"Fetched chargers: {chargers}")

        # Step 3: Filter chargers near the route
        chargers_near_route = []
        for charger in chargers:
            if is_near_route(charger["geoCoordinates"], route_coords, max_distance):
                chargers_near_route.append({
                    "id": charger["id"],
                    "name": charger["name"],
                    "geoCoordinates": charger["geoCoordinates"]
                })

        logging.debug(f"Filtered chargers near route: {chargers_near_route}")

        if not chargers_near_route:
            logging.warning("No chargers found along the route.")
            raise HTTPException(status_code=404, detail="404: No chargers found along the route.")

        return {
            "route": route_coords,
            "chargers": chargers_near_route
        }

    except Exception as e:
        logging.error(f"Error in /chargers-on-route: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 5. Get Stations Within Radius
@app.get("/stations")
async def get_stations_within_radius(lat: float, lon: float, radius_km: float = 0.5):
    """
    Get charging stations within a given radius (default: 5km) of provided coordinates.
    """
    stations_collection = mongo_connect()
    user_location = (lat, lon)
    stations_within_radius = []

    try:
        # Retrieve all stations from the database
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
            stations_within_radius.append({
                "id": station["id"],
                "name": station["name"],
                "geoCoordinates": station["geoCoordinates"],
                "distance_km": round(distance, 2),
                "stations": station["stations"],
            })

    if not stations_within_radius:
        logging.warning("No charging stations found within the given radius.")
        raise HTTPException(
            status_code=404,
            detail="No charging stations found within the given radius.",
        )

    return {"stations": stations_within_radius}

# 6. Get Station Details by ID
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
        logging.error(f"Error querying database: {e}")
        raise HTTPException(status_code=500, detail=f"Error querying database: {e}")

    # If no match is found
    logging.warning("Charging station not found.")
    raise HTTPException(status_code=404, detail="Charging station not found.")

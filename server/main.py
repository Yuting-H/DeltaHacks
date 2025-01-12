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
load_dotenv()

MONGO_DB_USER = os.getenv("MONGO_DB_USER")
MONGO_DB_PASSWORD = os.getenv("MONGO_DB_PASSWORD")
MONGO_DB_URI = os.getenv("MONGO_DB_URI")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# MongoDB connection setup
uri = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASSWORD}@{MONGO_DB_URI}/?retryWrites=true&w=majority"

gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

def mongo_connect(collection="stations"):
    """
    Connect to MongoDB and return the specified collection.
    """
    try:
        client = MongoClient(uri, server_api=ServerApi("1"))
        db = client["betabase"]  # Access the database
        stations_collection = db[collection]  # Access the specified collection
        logging.info("MongoDB connection successful!")
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
                chargers_near_route.append({
                    "id": charger["id"],
                    "name": charger["name"],
                    "geoCoordinates": charger["geoCoordinates"]
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
    stations_collection = mongo_connect("uxpropertegypt")
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

# 7. Get Parent Stations
@app.get("/parent-stations")
async def get_parent_stations():
    """
    Get a list of parent charging stations with all their chargers included.
    """
    stations_collection = mongo_connect("uxpropertegypt")
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
    stations_collection = mongo_connect("uxpropertegypt")
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

    logging.warning("Charging station not found.")
    raise HTTPException(status_code=404, detail="Charging station not found.")
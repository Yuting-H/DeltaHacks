from fastapi import FastAPI
import httpx
from calculus import get_bounds_zoom_level

app = FastAPI()

API_URL = "https://emobility.flo.ca/v3.0/map/markers/search"

@app.post("/find_parks")
async def find_parks(input_data: dict):
    """
    Increment zoomLevel until clusters disappear and only parks are returned.
    """
    zoom_level = 12  # Starting zoom level
    max_zoom = 20  # Define a maximum zoom level to prevent infinite loops
    bounds = input_data["bounds"]

    map_dim = {"height": 800, "width": 600}
    print(get_bounds_zoom_level(bounds, map_dim))

    while zoom_level <= max_zoom:
        # Prepare the request payload
        payload = {
            "zoomLevel": zoom_level,
            "bounds": {
                "southWest": {
                    "latitude": bounds["SouthWest"]["Latitude"],
                    "longitude": bounds["SouthWest"]["Longitude"]
                },
                "northEast": {
                    "latitude": bounds["NorthEast"]["Latitude"],
                    "longitude": bounds["NorthEast"]["Longitude"]
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

        print(f"Response: {data}")
        # Parse the response
        parks = data.get("parks", [])
        clusters = data.get("clusters", [])
        print(f"Zoom level: {zoom_level}, Parks: {len(parks)}, Clusters: {len(clusters)}")

        # If no clusters are present, return parks
        if not clusters:
            return {
                "zoomLevel": zoom_level,
                "parks": parks
            }

        # Increase zoom level
        zoom_level += 1

    # If the maximum zoom level is reached without finding only parks
    return {
        "error": "Unable to find only parks within the maximum zoom level.",
        "last_response": {
            "zoomLevel": zoom_level - 1,
            "parks": parks,
            "clusters": clusters
        }
    }

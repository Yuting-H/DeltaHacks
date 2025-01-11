import requests
import json
from geopy.distance import geodesic
import folium

# 1. Extract Charger Data from JSON
def extract_chargers_from_json(data):
    chargers = []
    for location in data:
        for station in location.get("stations", []):  # Extract from "stations"
            charger = {
                "geoCoordinates": location["geoCoordinates"],
                "name": station.get("name"),
                "chargingSpeed": station.get("chargingSpeed", 0),  # Default to 0 if missing
                "level": station.get("level", "L2"),  # Default to L2 if missing
                "status": station.get("status", "Unknown"),
                "networkId": location.get("networkId", 0),  # Optional field
            }
            chargers.append(charger)
    return chargers

# 2. Get Route Between Two Locations
def get_route(origin, destination, api_key):
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "key": api_key,
    }
    response = requests.get(url, params=params)
    data = response.json()

    if data["status"] == "OK":
        return [
            step["end_location"]
            for route in data["routes"]
            for leg in route["legs"]
            for step in leg["steps"]
        ]
    else:
        raise Exception(f"Route could not be retrieved: {data['status']}")

# 3. Find Chargers Along the Route
def is_near_route(charger_coords, route_coords, max_distance=5):
    for route_point in route_coords:
        distance = geodesic(
            (charger_coords["latitude"], charger_coords["longitude"]),
            (route_point["lat"], route_point["lng"])
        ).km
        if distance <= max_distance:
            return True
    return False

def find_chargers_along_route(route_coords, chargers, max_distance=5):
    return [
        charger for charger in chargers
        if is_near_route(charger["geoCoordinates"], route_coords, max_distance)
    ]

# 4. Filtering Criteria
def filter_by_speed(chargers, min_speed):
    return [charger for charger in chargers if charger["chargingSpeed"] >= min_speed]

def calculate_battery_damage(charger):
    if charger["level"] == "L3":
        return charger["chargingSpeed"] * 0.2
    else:  # L2 chargers
        return charger["chargingSpeed"] * 0.1

def filter_by_battery_damage(chargers, max_damage):
    for charger in chargers:
        charger["batteryDamage"] = calculate_battery_damage(charger)
    return [charger for charger in chargers if charger["batteryDamage"] <= max_damage]

def calculate_environmental_score(charger):
    if charger["networkId"] in [1, 10]:  # Example green networks
        return 8
    return 5

def filter_by_environmental_score(chargers, min_score):
    for charger in chargers:
        charger["environmentalScore"] = calculate_environmental_score(charger)
    return [charger for charger in chargers if charger["environmentalScore"] >= min_score]

# 5. Combine Route and Filtering
def get_filtered_chargers(origin, destination, api_key, chargers, speed, damage, score):
    # Step 1: Get the route
    route_coords = get_route(origin, destination, api_key)

    # Step 2: Find chargers near the route
    chargers_near_route = find_chargers_along_route(route_coords, chargers)

    # Step 3: Apply filters
    chargers_by_speed = filter_by_speed(chargers_near_route, speed)
    chargers_by_damage = filter_by_battery_damage(chargers_by_speed, damage)
    chargers_by_environmental_score = filter_by_environmental_score(chargers_by_damage, score)

    return route_coords, chargers_by_environmental_score

# 6. Visualize Route and Chargers on Map
def visualize_route_and_chargers(route_coords, chargers):
    # Create a map centered at the midpoint of the route
    center_lat = sum(point['lat'] for point in route_coords) / len(route_coords)
    center_lng = sum(point['lng'] for point in route_coords) / len(route_coords)
    mymap = folium.Map(location=[center_lat, center_lng], zoom_start=12)

    # Add the route to the map
    route_points = [(point['lat'], point['lng']) for point in route_coords]
    folium.PolyLine(route_points, color="blue", weight=5, opacity=0.8).add_to(mymap)

    # Add chargers to the map
    for charger in chargers:
        coords = (charger["geoCoordinates"]["latitude"], charger["geoCoordinates"]["longitude"])
        folium.Marker(
            location=coords,
            popup=f"{charger['name']}<br>Speed: {charger['chargingSpeed']} kW<br>Battery Damage: {charger['batteryDamage']:.2f}<br>Environmental Score: {charger['environmentalScore']}",
            icon=folium.Icon(color="green" if charger['batteryDamage'] <= 10 else "red"),
        ).add_to(mymap)

    # Save the map
    mymap.save("route_with_chargers.html")
    print("Map saved as 'route_with_chargers.html'")

# Main Function
if __name__ == "__main__":
    # Input details
    origin = "590 Harvest Rd, Dundas, ON L9H 5K7"
    destination = "75 Centennial Pkwy N, Hamilton, ON L8E 2P2"
    api_key = "AIzaSyCLr_VRSKs0ltWY53xzFarVTDxmpn7TQ6Y"  # Replace with your API key
    min_speed = 50  # Minimum charger speed in kW
    max_damage = 10  # Maximum allowed battery damage
    min_score = 7  # Minimum environmental score

    # Load charger data
    with open("unique_parks.json") as f:
        raw_data = json.load(f)
    charger_data = extract_chargers_from_json(raw_data)

    # Get filtered chargers
    try:
        route_coords, filtered_chargers = get_filtered_chargers(
            origin, destination, api_key, charger_data, min_speed, max_damage, min_score
        )
        print(f"Filtered Chargers: {filtered_chargers}")

        # Visualize the results
        visualize_route_and_chargers(route_coords, filtered_chargers)
    except Exception as e:
        print(f"Error: {e}")

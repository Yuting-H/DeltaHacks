from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_DB_USER = os.getenv("MONGO_DB_USER")
MONGO_DB_PASSWORD = os.getenv("MONGO_DB_PASSWORD")
MONGO_DB_URI = os.getenv("MONGO_DB_URI")

uri = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASSWORD}@{MONGO_DB_URI}"

# MongoDB Client Setup
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['betabase']  # Accessing the existing database 'betabase'
stations_collection = db['stations']  # Accessing the 'stations' collection

# station_ids = [
#     "4fba949c-cb8b-4bec-a5b0-9b26164d23c6",
#     "d5265e8e-f655-b20b-ef60-c08155defba5",
# ]

station_ids = [
    "4fba949c-cb8b-4bec-a5b0-9b26164d23c6",
]

stations = stations_collection.find({"id": {"$in": station_ids}})

# Print each station
for station in stations:
    print(station)

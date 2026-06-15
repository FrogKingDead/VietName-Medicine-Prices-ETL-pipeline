import os
import sys
from pymongo import MongoClient

# Extract context tokens securely from environment variables
MONGO_URI = os.environ.get("MONGO_URI")
DB_NAME = os.environ.get("DB_NAME", "vietnam_pharma_raw")
API_URL = os.environ.get("SOURCE_URL")
RAW_COLLECTION_NAME = os.environ.get("RAW_COLLECTION_NAME", "pulic_vietnam_med_price")
CLEAN_COLLECTION_NAME = os.environ.get("CLEAN_COLLECTION_NAME", "cleaned_vietnam_med_price")
OUTPUT_FILE_PATH = os.environ.get("OUTPUT_FILE_PATH", "/output/cleaned_vietnam_med_price.json")

if not MONGO_URI or not API_URL:
    print("[CRITICAL] Environment configuration strings missing. Halting pipeline execution.")
    sys.exit(1)

# Initialize Cluster connection pooling
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collections
raw_collection = db[RAW_COLLECTION_NAME]
clean_collection = db[CLEAN_COLLECTION_NAME]

# Create unique indexes to block duplication
raw_collection.create_index("id", unique=True)
clean_collection.create_index("id", unique=True)

print(f"📦 Pipeline Data Interface Target Database: '{DB_NAME}'")
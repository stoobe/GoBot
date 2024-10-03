from __future__ import annotations

from pymongo import InsertOne, MongoClient, UpdateOne
from pymongo.errors import PyMongoError

from config import _config

# MongoDB Stuff
connection_string = (
    f"mongodb+srv://{_config.mongo_user}:{_config.mongo_pass}@{_config.mongo_host}"
    + f"/?retryWrites=true&w=majority&appName=go"
)

mongo_client = MongoClient(connection_string)
db = mongo_client[_config.mongo_db_name]


def run_bulk_operations(bulk_operations, collection_name):
    print(f"Bulk Operations To Run: {len(bulk_operations)}")
    collection = db[collection_name]
    if bulk_operations:
        result = collection.bulk_write(bulk_operations)
        print(f" - Matched:  {result.matched_count}")
        print(f" - Modified: {result.modified_count}")
        print(f" - Inserted: {result.inserted_count}")


def run_bulk_updates(records, collection_name):
    bulk_ops = [UpdateOne({"_id": r["_id"]}, {"$set": r}) for r in records]
    run_bulk_operations(bulk_ops, collection_name)


def load_active_seasons():
    seasons_collection = db["seasons"]
    seasons = list(seasons_collection.find({"active": True}))
    print(f"loaded {len(seasons)} active seasons")
    return seasons


def insert_many_to_mongo(nested_dicts, collection_name):
    collection = db[collection_name]
    result = collection.insert_many(nested_dicts)
    print(f"Acknowledged: {result.acknowledged}")
    print(f"Inserted count: {len(result.inserted_ids)}")

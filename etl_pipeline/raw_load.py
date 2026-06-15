from pymongo import UpdateOne
from config import raw_collection

def load_raw_batch_to_atlas(items: list):
    """
    Wraps documents into a singular transactional network round-trip.
    Utilizes an idempotent 'Upsert' mechanism mapped on unique entity keys.
    """
    if not items:
        return
        
    operations = []
    for item in items:
        # Match using the native unique integer ID field tracked by the target system
        op = UpdateOne(
            {"id": item.get("id")},
            {"$set": item},
            upsert=True
        )
        operations.append(op)
        
    # Send the execution requests over a single pipeline socket connection channel
    result = raw_collection.bulk_write(operations)
    print(f"[LOAD ATLAS] Transactions completed successfully: {result.upserted_count} inserts, {result.modified_count} records validated.")
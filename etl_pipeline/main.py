import sys
from config import raw_collection
from raw_extract import extract_raw_api_batches
from raw_load import load_raw_batch_to_atlas
from etl_clean import execute_transformation_pipeline

def main():
    print("Initiating Data Orchestration Lifecycle...")
    
    raw_count = raw_collection.count_documents({})
    print(f"Current raw landing zone state: {raw_count:,} records found.")
    
    if raw_count == 0:
        print("Landing zone is empty. Launching API Extraction Sequence...")
        try:
            # Invokes extraction with default batch sizes, removing hardcoded record caps
            for batch in extract_raw_api_batches(batch_size=100):
                load_raw_batch_to_atlas(batch)
            print("Phase 1 Complete: Raw API metrics successfully staged.")
        except Exception as e:
            print(f"Phase 1 Critical Failure during API extraction: {e}")
            sys.exit(1)
    else:
        print("Skipping API Extraction: Utilizing existing raw database staging assets.")

    print("\nLaunching Phase 2: Dual-Layer Quality Gate Transformation...")
    try:
        execute_transformation_pipeline()
        print("Phase 2 Complete: Clean target collection populated.")
    except Exception as e:
        print(f"Phase 2 Critical Failure during text normalization: {e}")
        sys.exit(1)

    print("\nComplete End-to-End Ingestion Engine Run Finished Successfully!")

if __name__ == "__main__":
    main()
    sys.exit(0)
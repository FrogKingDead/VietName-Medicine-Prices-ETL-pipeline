import requests
import time
from config import API_URL

def extract_raw_api_batches(batch_size: int = 100):
    skip_count = 0
    total_records = None
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    while total_records is None or skip_count < total_records:
        print(f"[EXTRACT] Requesting API records from offset skipCount={skip_count}...")
        
        payload = {
            "CongBoGiaThuoc": {}, 
            "KichHoat": True, 
            "skipCount": skip_count, 
            "maxResultCount": batch_size, 
            "sorting": None
        }
        
        try:
            response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"[WARNING] API error {response.status_code}. Retrying in 5s...")
                time.sleep(5)
                continue
                
            data = response.json()
            result_node = data.get("result", {})
            items = result_node.get("items", [])
            
            # Dynamically capture total records from API metadata on first successful hit
            if total_records is None:
                total_records = result_node.get("totalCount", 27000)
                print(f"[EXTRACT] Dynamic total discovered from API metadata: {total_records} records.")
            
            if not items:
                print("[EXTRACT] Ingestion complete: No more items returned.")
                break
                
            yield items
            skip_count += batch_size
            time.sleep(1.0)
            
        except Exception as e:
            print(f"[API ERROR] Failed at offset {skip_count}: {e}")
            time.sleep(5)
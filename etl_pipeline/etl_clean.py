import json
import re
from datetime import datetime
from config import raw_collection, clean_collection, OUTPUT_FILE_PATH

def get_text_outside_parentheses(text: str) -> str:
    """
    Removes parenthetical blocks to isolate the primary substance name.
    Example: "Piracetam (6.000mg/60ml)" -> "Piracetam "
    """
    return re.sub(r"\(.*?\)", "", text)


def is_layer_1_pristine(hoat_chat: str, ham_luong: str) -> bool:
    """
    Data Quality Gate Layer 1 Validation:
    Evaluates if columns have been correctly split at the database source.
    Returns True if hoatChat contains only text and hamLuong contains numbers.
    """
    hc = hoat_chat.strip() if hoat_chat else ""
    hl = ham_luong.strip() if ham_luong else ""

    if not hc or not hl or hc == "-" or hl == "-":
        return False
        
    # Isolate text by ignoring parenthetical metrics before validation checks
    hc_visible_text = get_text_outside_parentheses(hc)
    
    # If digits exist outside brackets, it is a complex Layer 2 compound record
    if re.search(r"\d", hc_visible_text):
        return False 
        
    if not re.search(r"\d", hl):
        return False
        
    return True


def safe_normalize_splitters(text: str) -> str:
    """
    Tokenizes delimiters (+, ,, ;, |) into uniform semicolons (;).
    Ignores delimiters nested inside parenthesis to protect raw metric formatting.
    """
    result = []
    depth = 0
    for char in (text or ""):
        if char == '(':
            depth += 1
            result.append(char)
        elif char == ')':
            depth -= 1
            result.append(char)
        # Only normalize splitters when depth is 0 (outside parenthetical blocks)
        elif char in '+,;|' and depth == 0:
            result.append(';')
        else:
            result.append(char)
    return ''.join(result)


def parse_clean_record(hoat_chat: str, ham_luong: str) -> list[dict]:
    """
    Parses Layer 1 standard records.
    Masks parenthetical strings to protect them from split operations,
    aligns substance tokens to dosage values, and extracts numeric concentrations.
    """
    # Isolate and extract parenthetical content early to prevent tokenizer corruption
    bracket_matches = re.findall(r"\(.*?\)", hoat_chat)
    hc_placeholder = hoat_chat
    for idx, match in enumerate(bracket_matches):
        hc_placeholder = hc_placeholder.replace(match, f"__BRACKET_{idx}__")
        
    # Standardize delimiters safely across isolated text blocks
    hc_norm = safe_normalize_splitters(hc_placeholder)
    hl_clean = re.sub(r'(\d+),(\d+)', r'\1.\2', ham_luong.strip())
    hl_norm = safe_normalize_splitters(hl_clean)
    
    name_tokens = [t.strip() for t in hc_norm.split(';') if t.strip()]
    dose_tokens = [t.strip() for t in hl_norm.split(';') if t.strip()]

    ingredients = []
    for i, name in enumerate(name_tokens):
        # Handle single dosage mappings applied to multiple active substances
        dose_str = dose_tokens[0] if len(dose_tokens) == 1 else (dose_tokens[i] if i < len(dose_tokens) else None)
        concentration, unit = None, None

        # Re-inject the protected parenthetical blocks back into matching text nodes
        for idx, bracket_text in enumerate(bracket_matches):
            name = name.replace(f"__BRACKET_{idx}__", bracket_text)

        if dose_str:
            dose_str = dose_str.strip()
            # Standardize thousands separator anomalies (e.g., converting 6.000 to 6000)
            if dose_str.count('.') > 1:
                dose_str = dose_str.replace('.', '')
            elif dose_str.count('.') == 1 and re.search(r'\.\d{3}(?!\d)', dose_str):
                if dose_str.endswith('.000') or 'IU' in dose_str.upper():
                    dose_str = dose_str.replace('.', '')

            # Extract floating-point concentrations from alphanumeric units
            num_match = re.match(r"^([\d\.]+)", dose_str)
            if num_match:
                try: 
                    concentration = float(num_match.group(1))
                except ValueError: 
                    pass
                unit_str = dose_str[num_match.end():].strip()
                if unit_str: 
                    unit = unit_str
            else:
                unit = dose_str

        ingredients.append({
            "name": name.strip(),
            "concentration": concentration,
            "unit": unit
        })
    return ingredients


def parse_layer_2_embedded_record(hoat_chat: str) -> list[dict] or None:
    """
    Data Quality Gate Layer 2 Recovery Fallback:
    Parses complex strings where substance names and concentrations are entirely merged.
    Utilizes localized lookahead regex bounds to extract fluid metrics and text tokens.
    """
    hc_raw = hoat_chat.strip() if hoat_chat else ""
    hc_raw = re.sub(r'(\d+),(\d+)', r'\1.\2', hc_raw)
    
    hc_norm = safe_normalize_splitters(hc_raw)
    raw_segments = [s.strip() for s in hc_norm.split(';') if s.strip()]
    
    ingredients = []
    for segment in raw_segments:
        segment_clean = segment.strip()

        # Complex Fluid Ratio Parsing Rule (e.g., "125mg/5ml", "125mg/ml")
        if "/" in segment_clean:
            ratio_match = re.search(r"(\d+(?:\.\d+)?)\s*([a-zA-Zμµ_]+)\s*/\s*(\d*(?:\.\d+)?)\s*([a-zA-Zμµ_]+)$", segment_clean)
            if ratio_match:
                raw_num = ratio_match.group(1)       
                weight_unit = ratio_match.group(2)   
                volume_num = ratio_match.group(3)    
                volume_unit = ratio_match.group(4)   
                
                # Consolidate values into standard relational metric string units
                unit_str = f"{weight_unit}/{volume_num}{volume_unit}" if volume_num else f"{weight_unit}/{volume_unit}"
                name_str = segment_clean[:ratio_match.start()].strip()
                name_str = name_str.rstrip("(: /").strip()
                
                if not name_str:
                    return None
                    
                if raw_num.count('.') > 1 or (raw_num.count('.') == 1 and raw_num.endswith('.000')):
                    raw_num = raw_num.replace('.', '')
                    
                try:
                    ingredients.append({
                        "name": name_str,
                        "concentration": float(raw_num),
                        "unit": unit_str
                    })
                    continue 
                except ValueError:
                    return None

        # Standard Embedded Alphanumeric Unit Slicing Rule
        match = re.search(r"(\d+(?:\.\d+)?)\s*([a-zA-Z/%%μµ_]+)$", segment_clean)
        if not match:
            return None
            
        raw_num = match.group(1)
        unit_str = match.group(2).strip()
        name_str = segment_clean[:match.start()].strip()
        
        if not name_str or raw_num.count('.') > 1 or (raw_num.count('.') == 1 and raw_num.endswith('.000')):
            raw_num = raw_num.replace('.', '')

        try:
            concentration = float(raw_num)
        except ValueError:
            return None

        ingredients.append({
            "name": name_str,
            "concentration": concentration,
            "unit": unit_str
        })
        
    return ingredients


def date_converter(raw_time: str) -> str:
    """
    Standardizes raw datetime inputs into BSON-compliant ISO date strings (YYYY-MM-DD).
    Ensures structural data weight optimization for rapid timeline trend querying.
    """
    if raw_time:
        try:
            date = str(datetime.fromisoformat(raw_time).date())
        except ValueError:
            date = None    
    else:
        date = None
    return date


def get_clean_status(raw_status: str) -> str:
    """
    Slices raw operational status strings containing inline HTML elements.
    Utilizes deterministic boundaries (.find, .rfind) to extract the plain-text status.
    """
    if not raw_status:
        return "Unknown"
    
    start_idx = raw_status.find(">")
    end_idx = raw_status.rfind("<")
    
    # Slices text enclosed between HTML tag brackets securely across whitespace anomalies
    if start_idx != -1 and end_idx != -1:
        return raw_status[start_idx + 1 : end_idx].strip()
    
    return str(raw_status).strip()
    
    
def execute_transformation_pipeline():
    """
    Main transformation workflow loop. Scan raw collections, execute quality gates,
    build schema-compliant records using exact camelCase projections, and execute 
    idempotent document persistence.
    """
    print("Launching Dual-Layer Strict Quality Gate...")
    
    # Scans the entire raw landing zone collection for data aggregation
    raw_cursor = raw_collection.find({})
    total_records = raw_collection.count_documents({})
    
    clean_export_list = []
    skipped_count = 0
    l1_count, l2_count = 0, 0
    
    for doc in raw_cursor:
        raw_id = doc.get("id")
        raw_hoat_chat = doc.get("hoatChat", "")
        raw_ham_luong = doc.get("hamLuong", "")
        raw_time = doc.get("ngayTiepNhan") or doc.get("creationTime")
        price_per_unit = doc.get("giaBanBuonDuKien", 0) or doc.get("giaBanBuon", 0) or 0
        
        ingredients_list = []
        parsed_successfully = False

        # Ingestion Routing Logic Layer 1
        if is_layer_1_pristine(raw_hoat_chat, raw_ham_luong):
            ingredients_list = parse_clean_record(raw_hoat_chat, raw_ham_luong)
            l1_count += 1
            parsed_successfully = True
            
        # Ingestion Routing Logic Layer 2 Recovery Suite
        elif raw_hoat_chat and re.search(r"\d", raw_hoat_chat):
            layer_2_result = parse_layer_2_embedded_record(raw_hoat_chat)
            if layer_2_result is not None:
                ingredients_list = layer_2_result
                l2_count += 1
                parsed_successfully = True

        # Mapping Production Schema Layouts
        if parsed_successfully:
            clean_document = {
                "id": raw_id,
                "name": doc.get("tenThuoc"),
                "ingredients": ingredients_list,
                "manufacturer": doc.get("doanhNghiepSanXuat"),
                "registrant": doc.get("donViKeKhai"),
                "countryOfOrigin": doc.get("nuocSanXuat"),
                "dosageForm": doc.get("dangBaoChe"),
                "packaging": doc.get("quyCachDongGoi"),
                "pricePerUnit": price_per_unit,
                "priceType": doc.get("loaiGia"),
                "publicationDate": date_converter(raw_time),
                "status": get_clean_status(doc.get("trangThaiCongBo"))
            }
            
            # Persist via server-side atomic upsert queries to prevent double collection staging
            clean_collection.update_one({"id": raw_id}, {"$set": clean_document}, upsert=True)
            clean_document.pop("_id", None)
            clean_export_list.append(clean_document)
        else:
            skipped_count += 1

    # Persist flat file data inside the active volume mount portal path
    with open(OUTPUT_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(clean_export_list, f, ensure_ascii=False, indent=4)
        
    print("Ingestion complete.")
    print(f"Layer 1 Pass: {l1_count} | Layer 2 Pass: {l2_count} | Dropped Rows: {skipped_count}")
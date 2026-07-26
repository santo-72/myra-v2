import os
import json
import csv
import sys
from app.memory.database import LocalDatabase

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def parse_vcf(filepath):
    contacts = []
    current_name = None
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line_clean = line.strip()
            if line_clean.startswith("FN:"):
                current_name = line_clean[3:].strip()
            elif line_clean.startswith("N:") and not current_name:
                parts = line_clean[2:].split(";")
                current_name = " ".join([p for p in parts[:2] if p]).strip()
            elif line_clean.startswith("TEL") or "TEL;" in line_clean or "TEL:" in line_clean:
                phone = line_clean.split(":")[-1].strip()
                if current_name and phone:
                    contacts.append({"name": current_name, "app": "whatsapp", "identifier": phone})
            elif line_clean == "END:VCARD":
                current_name = None
    return contacts

def parse_csv(filepath):
    contacts = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name") or row.get("name") or row.get("First Name") or row.get("Full Name", "")
            phone = row.get("Phone 1 - Value") or row.get("Phone") or row.get("phone") or row.get("Identifier") or row.get("identifier", "")
            app = row.get("App") or row.get("app") or "whatsapp"
            if name and phone:
                contacts.append({"name": name.strip(), "app": app.strip().lower(), "identifier": phone.strip()})
    return contacts

def parse_json(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "contacts" in data:
            return data["contacts"]
    return []

def run_import():
    db_path = "data/myra_local.db"
    if not os.path.exists("data"):
        os.makedirs("data", exist_ok=True)
        
    db = LocalDatabase(db_path)
    contacts_dir = "contacts"
    if not os.path.exists(contacts_dir):
        os.makedirs(contacts_dir, exist_ok=True)
        
    all_files = os.listdir(contacts_dir)
    if not all_files:
        print("[X] contacts/ ফোল্ডারে কোনো JSON, CSV বা VCF (vCard) ফাইল পাওয়া যায়নি।")
        return

    total_imported = 0
    total_files_processed = 0
    
    print("=" * 60)
    print(">>> M.Y.R.A (Myra) AI v2 - Bulk Contact & Phone Number Importer <<<")
    print("=" * 60)
    
    for filename in all_files:
        fpath = os.path.join(contacts_dir, filename)
        if os.path.isdir(fpath):
            continue
            
        ext = os.path.splitext(filename)[-1].lower()
        items = []
        try:
            if ext == ".vcf":
                items = parse_vcf(fpath)
            elif ext == ".csv":
                items = parse_csv(fpath)
            elif ext == ".json":
                items = parse_json(fpath)
            else:
                continue
                
            total_files_processed += 1
            file_count = 0
            for item in items:
                name = item.get("name", "").strip()
                app = item.get("app", "whatsapp").strip().lower()
                identifier = item.get("identifier", "").strip()
                if name and identifier:
                    db.add_contact(name, app, identifier)
                    file_count += 1
                    total_imported += 1
            print(f"[OK] ফাইল '{filename}' থেকে {file_count} টি কন্টাক্ট M.Y.R.A ডাটাবেসে ইমপোর্ট করা হয়েছে!")
        except Exception as e:
            print(f"[!] '{filename}' প্রক্রিয়াকরণ করার সময় ত্রুটি: {e}")
            
    # Also record import summary in imported_data table
    db.import_data("contacts_bulk_import", f"contacts/ ({total_files_processed} files)", f"Imported {total_imported} contacts successfully")
    
    all_saved = db.get_all_contacts()
    
    print("\n" + "=" * 60)
    print(f"[SUCCESS] এই সেশনে মোট {total_imported} টি নতুন কন্টাক্ট নম্বর ডাটাবেসে যুক্ত হয়েছে!")
    print(f"[DATABASE] বর্তমানে M.Y.R.A ডাটাবেসে ({db_path}) সর্বমোট {len(all_saved)} টি কন্টাক্ট সংরক্ষিত রয়েছে।")
    print("[NOTE] আপনার ফোন বা Google Contacts থেকে যেকোনো .vcf বা .csv ফাইল 'contacts' ফোল্ডারে রেখে এই স্ক্রিপ্টটি চালালে হাজার হাজার নাম্বার এক ক্লিকে অ্যাড হয়ে যাবে!")
    print("=" * 60)

if __name__ == "__main__":
    run_import()

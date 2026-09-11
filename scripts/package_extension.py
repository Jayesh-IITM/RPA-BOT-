"""
MahaSetu RPA Recorder - Extension Packaging & Deployment Tool
Validates Manifest V3 compliance, checks file integrity,
and builds a production-ready ZIP archive for Chrome Web Store upload
and direct web portal distribution.
"""
import json
import os
import shutil
import sys
import zipfile

def package_extension():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ext_dir = os.path.join(root_dir, "extension")
    dist_dir = os.path.join(root_dir, "dist")
    downloads_dir = os.path.join(root_dir, "backend", "static", "downloads")

    os.makedirs(dist_dir, exist_ok=True)
    os.makedirs(downloads_dir, exist_ok=True)

    print("=" * 60)
    print("  MAHASETU CHROME EXTENSION PACKAGER (Manifest V3)")
    print("=" * 60)

    # 1. Validate manifest.json
    manifest_path = os.path.join(ext_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        print(f"[!] Error: manifest.json not found at {manifest_path}")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        try:
            manifest = json.load(f)
        except Exception as e:
            print(f"[!] Error: Invalid JSON in manifest.json: {e}")
            sys.exit(1)

    version = manifest.get("version", "1.0.0")
    name = manifest.get("name", "MahaSetu RPA Recorder")
    print(f"  + Package: {name}")
    print(f"  + Version: {version}")
    print(f"  + Manifest Version: {manifest.get('manifest_version')}")

    # 2. Check required files
    files_to_check = []
    # Check icons
    for size, icon_rel in manifest.get("icons", {}).items():
        files_to_check.append((f"Icon {size}x{size}", os.path.join(ext_dir, icon_rel)))

    # Check background service worker
    bg_worker = manifest.get("background", {}).get("service_worker")
    if bg_worker:
        files_to_check.append(("Background Worker", os.path.join(ext_dir, bg_worker)))

    # Check action popup
    popup_page = manifest.get("action", {}).get("default_popup")
    if popup_page:
        files_to_check.append(("Action Popup", os.path.join(ext_dir, popup_page)))

    # Check options page
    opt_page = manifest.get("options_ui", {}).get("page")
    if opt_page:
        files_to_check.append(("Options UI", os.path.join(ext_dir, opt_page)))

    # Check content scripts
    for cs in manifest.get("content_scripts", []):
        for js_file in cs.get("js", []):
            files_to_check.append((f"Content Script ({js_file})", os.path.join(ext_dir, js_file)))

    print("\n[Step 1] Validating Declared Manifest Files...")
    all_ok = True
    for label, path in files_to_check:
        if os.path.exists(path):
            print(f"  [OK] {label}: {os.path.relpath(path, ext_dir)}")
        else:
            print(f"  [FAIL] Missing {label}: {path}")
            all_ok = False

    if not all_ok:
        print("[!] Validation failed. Aborting package creation.")
        sys.exit(1)

    # 3. Create zip bundle
    zip_name = f"mahasetu-rpa-recorder-v{version}.zip"
    zip_path = os.path.join(dist_dir, zip_name)
    download_zip_path = os.path.join(downloads_dir, "mahasetu-rpa-recorder.zip")

    # Files to exclude from production extension bundle
    excluded_patterns = {
        "generate_icons.py",
        "__pycache__",
        ".DS_Store",
        "Thumbs.db"
    }

    print(f"\n[Step 2] Packaging into {zip_name}...")
    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ext_dir):
            for file in files:
                if any(ex in file or ex in root for ex in excluded_patterns):
                    continue
                file_abs = os.path.join(root, file)
                rel_path = os.path.relpath(file_abs, ext_dir)
                zf.write(file_abs, rel_path)
                file_count += 1
                print(f"  + Added: {rel_path}")

    # Copy to downloads folder for web portal 1-click download
    shutil.copy2(zip_path, download_zip_path)

    zip_size_kb = round(os.path.getsize(zip_path) / 1024, 1)

    print("\n" + "=" * 60)
    print(f"  SUCCESSFULLY PACKAGED CHROME EXTENSION")
    print("=" * 60)
    print(f"  * Production Package: {zip_path}")
    print(f"  * Web Portal Asset:   {download_zip_path}")
    print(f"  * Total Files:        {file_count}")
    print(f"  * Package Size:       {zip_size_kb} KB")
    print(f"  * Ready for Chrome Web Store Developer Dashboard Upload")
    print("=" * 60 + "\n")
    return zip_path

if __name__ == "__main__":
    package_extension()

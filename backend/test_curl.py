import subprocess
import json
import time

API_URL = "http://127.0.0.1:8000/api/files"

def run_cmd(cmd):
    print(f"\n> {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        try:
            parsed = json.loads(result.stdout)
            print(json.dumps(parsed, indent=2))
            return parsed
        except:
            print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr}")
    return None

print("=== 1. Health Check ===")
run_cmd(["curl.exe", "-s", "-X", "GET", "http://127.0.0.1:8000/health"])

print("\n=== 2. Upload KML File ===")
upload_res = run_cmd(["curl.exe", "-s", "-X", "POST", "-F", "file=@sample.kml", f"{API_URL}/"])
file_id = upload_res.get("id") if upload_res else None

if not file_id:
    print("Upload failed, stopping.")
    exit(1)

print(f"\nWaiting for processing to complete...")
time.sleep(2)

print("\n=== 3. Get File Info ===")
run_cmd(["curl.exe", "-s", "-X", "GET", f"{API_URL}/{file_id}/"])

print("\n=== 4. Get Measurements ===")
run_cmd(["curl.exe", "-s", "-X", "GET", f"{API_URL}/{file_id}/measurements"])

print("\n=== 5. List Files ===")
run_cmd(["curl.exe", "-s", "-X", "GET", f"{API_URL}/"])

print("\n=== 6. Delete File ===")
run_cmd(["curl.exe", "-s", "-X", "DELETE", f"{API_URL}/{file_id}/"])
run_cmd(["curl.exe", "-s", "-X", "GET", f"{API_URL}/{file_id}/"])

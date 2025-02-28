import os
import hashlib
import hmac
import time
import json
import requests
import base64
from datetime import datetime

# Load API keys
with open("secrets/public_key.txt", "r") as f:
    public_key = f.read().strip()

with open("secrets/private_key.txt", "r") as f:
    private_key = f.read().strip()

# Endpoint
base_url = "https://api.fieldclimate.com/v2"
endpoint = "user/stations"  # List stations endpoint
method = "get"
path = f"/{endpoint}"
timestamp = int(time.time())

# Debug info
print(f"Public key: {public_key}")
print(f"Method: {method}")
print(f"Path: {path}")
print(f"Timestamp: {timestamp}")

# Create message for signature
message = f"{method}{path}{timestamp}"
print(f"Message to sign: {message!r}")

# Generate signature
signature = hmac.new(
    private_key.encode(),
    message.encode(),
    hashlib.sha256
).hexdigest()

print(f"Signature: {signature}")

# Create authorization header (method 1 - HMAC header format)
auth_header1 = f"hmac {public_key}:{signature}:{timestamp}"
print(f"Authorization header (Method 1): {auth_header1}")

# Make request with method 1
headers1 = {
    "Authorization": auth_header1,
    "Content-Type": "application/json"
}

print("\nTrying Method 1 (HMAC Authorization header)...")
response1 = requests.get(f"{base_url}/{endpoint}", headers=headers1)
print(f"Status Code: {response1.status_code}")
if response1.status_code == 200:
    print("Success!")
    station_count = len(response1.json())
    print(f"Found {station_count} stations")
else:
    print(f"Error: {response1.text}")

# Try Method 2 (separate headers)
print("\nTrying Method 2 (Separate headers)...")
headers2 = {
    "X-Public-Key": public_key,
    "X-Signature": signature,
    "X-Timestamp": str(timestamp),
    "Content-Type": "application/json"
}

response2 = requests.get(f"{base_url}/{endpoint}", headers=headers2)
print(f"Status Code: {response2.status_code}")
if response2.status_code == 200:
    print("Success!")
    station_count = len(response2.json())
    print(f"Found {station_count} stations")
else:
    print(f"Error: {response2.text}")

# Try Method 3 (Basic Auth)
print("\nTrying Method 3 (Basic Auth)...")
auth_str = f"{public_key}:{private_key}"
auth_bytes = auth_str.encode('ascii')
base64_auth = base64.b64encode(auth_bytes).decode('ascii')
headers3 = {
    "Authorization": f"Basic {base64_auth}",
    "Content-Type": "application/json"
}

response3 = requests.get(f"{base_url}/{endpoint}", headers=headers3)
print(f"Status Code: {response3.status_code}")
if response3.status_code == 200:
    print("Success!")
    station_count = len(response3.json())
    print(f"Found {station_count} stations")
else:
    print(f"Error: {response3.text}")

# Try Method 4 (API key as username with empty password)
print("\nTrying Method 4 (API key as username)...")
response4 = requests.get(f"{base_url}/{endpoint}", auth=(public_key, ""))
print(f"Status Code: {response4.status_code}")
if response4.status_code == 200:
    print("Success!")
    station_count = len(response4.json())
    print(f"Found {station_count} stations")
else:
    print(f"Error: {response4.text}")
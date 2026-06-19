"""
Simple script to test if backend is accessible and responding
"""

import requests
import sys

API_BASE = "http://localhost:8001"

def test_health():
    """Test basic health endpoint"""
    print("=" * 60)
    print("Testing Backend Connectivity")
    print("=" * 60)

    try:
        print(f"\n1. Testing root endpoint: {API_BASE}/")
        response = requests.get(f"{API_BASE}/", timeout=5)
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Response: {response.json()}")
    except requests.exceptions.ConnectionError:
        print(f"   ✗ ERROR: Cannot connect to {API_BASE}")
        print(f"   ✗ Is the backend running?")
        sys.exit(1)
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        sys.exit(1)

    try:
        print(f"\n2. Testing health endpoint: {API_BASE}/api/health")
        response = requests.get(f"{API_BASE}/api/health", timeout=5)
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Response: {response.json()}")
    except Exception as e:
        print(f"   ✗ ERROR: {e}")

    try:
        print(f"\n3. Testing supported formats: {API_BASE}/api/supported-formats")
        response = requests.get(f"{API_BASE}/api/supported-formats", timeout=5)
        print(f"   ✓ Status: {response.status_code}")
        formats = response.json()
        print(f"   ✓ Found {len(formats.get('formats', {}))} format categories")
    except Exception as e:
        print(f"   ✗ ERROR: {e}")

    print("\n" + "=" * 60)
    print("✓ Backend is accessible and responding!")
    print("=" * 60)
    print("\nNow try uploading from the frontend.")
    print("Check backend logs at: backend/logs/application.log")
    print("\nTo watch logs in real-time:")
    print("  tail -f backend/logs/application.log")

if __name__ == "__main__":
    test_health()

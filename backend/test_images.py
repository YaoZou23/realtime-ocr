#!/usr/bin/env python3
"""
Test script to test the OCR backend with images from the testdata folder.
"""
import os
import sys
import base64
import json
import requests
from pathlib import Path

# Add parent directory to path to import from backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def image_to_base64(image_path):
    """Convert image file to base64 string."""
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def test_ocr(image_path, server_url="http://localhost:5001/api/ocr"):
    """Test OCR on a single image."""
    print(f"\n{'='*60}")
    print(f"Testing: {os.path.basename(image_path)}")
    print(f"{'='*60}")
    
    try:
        # Convert image to base64
        print("Converting image to base64...")
        base64_image = image_to_base64(image_path)
        
        # Prepare request
        payload = {
            "image": base64_image
        }
        
        # Send request
        print(f"Sending request to {server_url}...")
        response = requests.post(server_url, json=payload, timeout=60)
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success!")
            print(f"Extracted text: {result.get('text', 'N/A')}")
            if 'confidence' in result:
                print(f"Confidence: {result['confidence']:.2f}" if result['confidence'] else "Confidence: N/A")
            if 'engine' in result:
                print(f"Engine: {result['engine']}")
        else:
            print(f"❌ Error: Status code {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: Could not connect to server at {server_url}")
        print("Make sure the backend server is running!")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Error: Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    return True

def main():
    # Get testdata directory
    backend_dir = Path(__file__).parent
    project_dir = backend_dir.parent
    testdata_dir = project_dir / "testdata"
    
    if not testdata_dir.exists():
        print(f"❌ Testdata directory not found: {testdata_dir}")
        return
    
    # Find all image files
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
    image_files = []
    for ext in image_extensions:
        image_files.extend(testdata_dir.glob(f"*{ext}"))
        image_files.extend(testdata_dir.glob(f"*{ext.upper()}"))
    
    if not image_files:
        print(f"❌ No image files found in {testdata_dir}")
        return
    
    print(f"Found {len(image_files)} image(s) to test:")
    for img in image_files:
        print(f"  - {img.name}")
    
    # Test server health first
    print(f"\n{'='*60}")
    print("Testing server health...")
    print(f"{'='*60}")
    try:
        health_url = "http://localhost:5001/api/health"
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and healthy!")
        else:
            print(f"⚠️  Server responded with status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running or not accessible!")
        print("\nPlease start the server first:")
        print("  cd backend")
        print("  python app.py")
        return
    except Exception as e:
        print(f"⚠️  Could not check server health: {e}")
    
    # Test each image
    print(f"\n{'='*60}")
    print("Starting OCR tests...")
    print(f"{'='*60}")
    
    results = []
    for image_file in sorted(image_files):
        success = test_ocr(image_file)
        results.append((image_file.name, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    print(f"\nTotal: {total}, Passed: {passed}, Failed: {total - passed}")

if __name__ == "__main__":
    main()


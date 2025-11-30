#!/usr/bin/env python3
"""
Test script to test the OCR backend with images from the testdata folder.
"""
import os
import sys
import base64
import json
import argparse
import requests
from pathlib import Path

# Add parent directory to path to import from backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def image_to_base64(image_path):
    """Convert image file to base64 string."""
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def call_translation_api(text, target_lang, server_url, timeout=30):
    """Low-level helper to call the translation endpoint."""
    payload = {"text": text, "target_lang": target_lang}
    try:
        response = requests.post(server_url, json=payload, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            translated = data.get("translated")
            if translated:
                return True, translated, None
            return False, None, json.dumps(data, ensure_ascii=False)
        return False, None, response.text
    except requests.exceptions.ConnectionError:
        return False, None, f"Could not reach translation endpoint at {server_url}"
    except requests.exceptions.Timeout:
        return False, None, "Translation request timed out"
    except Exception as e:
        return False, None, str(e)

def test_ocr(
    image_path,
    server_url="http://localhost:5003/api/ocr",
    auto_translate=False,
    target_lang="ZH",
    annotate_overlay=False,
    include_segments=False,
    overlay_boxes_only=False,
    overlay_output_dir=None
):
    """Test OCR on a single image and optionally translate and annotate the result."""
    print(f"\n{'='*60}")
    print(f"Testing: {os.path.basename(image_path)}")
    print(f"{'='*60}")
    
    translation_success = None
    translated_text = None
    annotated_path = None
    
    try:
        # Convert image to base64
        print("Converting image to base64...")
        base64_image = image_to_base64(image_path)
        
        # Prepare request
        payload = {"image": base64_image}
        if auto_translate and target_lang:
            payload["target_lang"] = target_lang
        if annotate_overlay:
            payload["return_overlay"] = True
            payload["include_segment_data"] = include_segments
            if overlay_boxes_only:
                payload["overlay_boxes_only"] = True
            elif target_lang:
                payload["target_lang"] = target_lang
        
        # Send request
        print(f"Sending request to {server_url}...")
        response = requests.post(server_url, json=payload, timeout=60)
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            print("✅ OCR succeeded")
            extracted_text = result.get('text', '').strip()
            print(f"Extracted text: {extracted_text or 'N/A'}")
            if 'confidence' in result:
                print(f"Confidence: {result['confidence']:.2f}" if result['confidence'] else "Confidence: N/A")
            if 'engine' in result:
                print(f"Engine: {result['engine']}")
            
            translated_text = result.get("translated_text")
            if translated_text:
                translation_success = True
                print(f"Translated text ({target_lang}): {translated_text}")
            elif auto_translate and target_lang and not overlay_boxes_only:
                print("⚠️  Backend did not return translated text despite target_lang request.")

            if include_segments and result.get("segments"):
                print("Segments:")
                for seg in result["segments"]:
                    print(f"  - {seg.get('text')} (conf: {seg.get('confidence')}) bbox: {seg.get('bbox')}")

            annotated_b64 = result.get("annotated_image")
            if annotated_b64 and annotate_overlay:
                if annotated_b64.startswith("data:image"):
                    annotated_b64 = annotated_b64.split(",")[1]
                if overlay_output_dir:
                    overlay_output_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"{Path(image_path).stem}_translated.png"
                    annotated_path = overlay_output_dir / filename
                    with open(annotated_path, "wb") as f:
                        f.write(base64.b64decode(annotated_b64))
                    print(f"Annotated image saved to: {annotated_path}")
        else:
            print(f"❌ Error: Status code {response.status_code}")
            print(f"Response: {response.text}")
            return {
                "ocr_success": False,
                "translation_success": translation_success,
                "translated_text": translated_text
            }
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: Could not connect to server at {server_url}")
        print("Make sure the backend server is running!")
        return {
            "ocr_success": False,
            "translation_success": translation_success,
            "translated_text": translated_text
        }
    except requests.exceptions.Timeout:
        print(f"❌ Error: Request timed out")
        return {
            "ocr_success": False,
            "translation_success": translation_success,
            "translated_text": translated_text
        }
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            "ocr_success": False,
            "translation_success": translation_success,
            "translated_text": translated_text
        }
    
    return {
        "ocr_success": True,
        "translation_success": translation_success,
        "translated_text": translated_text,
        "annotated_path": str(annotated_path) if annotated_path else None
    }

def test_translate(text, target_lang="ZH", server_url="http://localhost:5003/api/translate"):
    """Test the translation endpoint with arbitrary text."""
    print(f"\n{'='*60}")
    print("Testing translation endpoint")
    print(f"{'='*60}")
    print(f"Text: {text}")
    print(f"Target language: {target_lang}")
    print(f"Endpoint: {server_url}")

    success, translated, error = call_translation_api(text, target_lang, server_url)
    if success:
        print("✅ Translation succeeded")
        print(f"Translated text: {translated}")
        return True
    print(f"❌ Translation failed: {error}")
    print("Make sure the backend is running and DEEPL_API_KEY is configured in the server environment.")
    return False

def main():
    parser = argparse.ArgumentParser(description="Utility script to test OCR and translation APIs.")
    parser.add_argument(
        "--backend-url",
        default="http://localhost:5003",
        help="Base URL of the backend server (default: http://localhost:5003)",
    )
    parser.add_argument(
        "--translate-text",
        help="Optional text snippet to send to /api/translate for verification."
    )
    parser.add_argument(
        "--target-lang",
        default="ZH",
        help="Target language code for translation requests (default: ZH)."
    )
    parser.add_argument(
        "--translate-only",
        action="store_true",
        help="Run only translation tests (requires --translate-text)."
    )
    parser.add_argument(
        "--skip-translate-ocr",
        action="store_true",
        help="Skip translating OCR output (translation runs by default)."
    )
    parser.add_argument(
        "--annotate-ocr",
        action="store_true",
        help="Request backend to return original image annotated with translated text."
    )
    parser.add_argument(
        "--overlay-dir",
        default="annotated_results",
        help="Directory to save annotated OCR images (used with --annotate-ocr)."
    )
    parser.add_argument(
        "--include-segments",
        action="store_true",
        help="Print detailed segment metadata returned by the backend."
    )
    parser.add_argument(
        "--overlay-boxes-only",
        action="store_true",
        help="When annotating, draw only bounding boxes with no overlaid text."
    )
    
    args = parser.parse_args()

    if args.translate_only and not args.translate_text:
        parser.error("--translate-only requires --translate-text to be set.")
    
    base_url = args.backend_url.rstrip("/")
    auto_translate_ocr = not args.skip_translate_ocr
    health_url = f"{base_url}/api/health"
    ocr_url = f"{base_url}/api/ocr"
    translate_url = f"{base_url}/api/translate"
    overlay_dir = Path(args.overlay_dir) if args.annotate_ocr else None

    # Optional translation test
    if args.translate_text:
        translation_ok = test_translate(args.translate_text, args.target_lang, translate_url)
        if args.translate_only:
            return
    else:
        translation_ok = None
    
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
        ocr_result = test_ocr(
            image_file,
            server_url=ocr_url,
            auto_translate=auto_translate_ocr,
            target_lang=args.target_lang,
            annotate_overlay=args.annotate_ocr,
            include_segments=args.include_segments or args.annotate_ocr,
            overlay_boxes_only=args.overlay_boxes_only,
            overlay_output_dir=overlay_dir if args.annotate_ocr else None
        )
        results.append({
            "name": image_file.name,
            **ocr_result
        })
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    if translation_ok is not None:
        status = "✅ PASS" if translation_ok else "❌ FAIL"
        print(f"{status}: translation ({args.translate_text[:30]}{'...' if len(args.translate_text) > 30 else ''})")
    for entry in results:
        status = "✅ PASS" if entry["ocr_success"] else "❌ FAIL"
        line = f"{status}: {entry['name']}"
        if entry.get("translated_text"):
            preview = entry["translated_text"][:60]
            suffix = "..." if len(entry["translated_text"]) > 60 else ""
            line += f" | translated ({args.target_lang}): {preview}{suffix}"
        elif auto_translate_ocr and entry["ocr_success"]:
            line += " | translation unavailable"
        if entry.get("annotated_path"):
            line += f" | annotated image: {entry['annotated_path']}"
            if args.overlay_boxes_only:
                line += " (boxes only)"
        print(line)
    
    total = len(results)
    passed = sum(1 for entry in results if entry["ocr_success"])
    annotated = sum(1 for entry in results if entry.get("annotated_path"))
    print(f"\nTotal OCR Images: {total}, Passed: {passed}, Failed: {total - passed}")
    if args.annotate_ocr:
        extra = " (boxes only)" if args.overlay_boxes_only else ""
        print(f"Annotated images generated: {annotated}{extra}")

if __name__ == "__main__":
    main()


from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
import base64
import logging
import os
import cv2
import numpy as np
import easyocr
import threading
import time
import platform

# Fix for PIL.ANTIALIAS deprecation in EasyOCR
# Pillow 10.0.0+ removed ANTIALIAS, use LANCZOS instead
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize EasyOCR reader (lazy loading - will load on first use)
easyocr_reader = None

# Minimum confidence threshold for accepting OCR detections
MIN_CONFIDENCE = 0.2

def check_gpu_available():
    """Check if GPU acceleration is available (CUDA for NVIDIA, MPS for Apple Silicon)"""
    try:
        import torch
        system = platform.system()
        
        # Check for CUDA (NVIDIA GPUs)
        if torch.cuda.is_available():
            logger.info(f"CUDA available: {torch.cuda.get_device_name(0)}")
            return True
        
        # Check for Metal Performance Shaders (Apple Silicon Macs)
        elif system == "Darwin" and hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            logger.info("Metal Performance Shaders (MPS) available for Apple Silicon GPU")
            return True
        else:
            if system == "Darwin":
                logger.info("macOS detected but MPS not available, will use CPU")
            else:
                logger.info("CUDA not available, will use CPU")
            return False
    except ImportError:
        logger.info("PyTorch not found, will attempt GPU detection via EasyOCR")
        return None  # Let EasyOCR handle it
    except Exception as e:
        logger.warning(f"Error checking GPU availability: {e}, will use CPU")
        return False

def get_easyocr_reader():
    """Lazy load EasyOCR reader to avoid slow startup"""
    global easyocr_reader
    if easyocr_reader is None:
        logger.info("Initializing EasyOCR reader (first time, may take a moment)...")

        # Languages: English + Simplified Chinese
        # NOTE: EasyOCR's Traditional Chinese model (`ch_tra`) cannot be combined
        # with other Chinese languages in this version and was causing:
        # "Chinese_tra is only compatible with English, try lang_list=['ch_tra','en']"
        # To keep things stable, we use English + Simplified Chinese only here.
        languages = ['en', 'ch_sim']

        # Check GPU availability
        use_gpu = check_gpu_available()

        # Try GPU first if available, fallback to CPU
        if use_gpu is True:
            try:
                logger.info("Attempting to initialize EasyOCR with GPU (en + ch_sim)...")
                easyocr_reader = easyocr.Reader(languages, gpu=True)
                logger.info("EasyOCR reader initialized successfully with GPU (English + Simplified Chinese)")
            except Exception as e:
                logger.warning(f"Failed to initialize EasyOCR with GPU (en + ch_sim): {e}")
                logger.info("Falling back to CPU...")
                try:
                    easyocr_reader = easyocr.Reader(languages, gpu=False)
                    logger.info("EasyOCR reader initialized successfully with CPU (English + Simplified Chinese)")
                except Exception as e2:
                    logger.error(f"Failed to initialize EasyOCR with CPU: {e2}")
        elif use_gpu is None:
            # Try GPU first, let EasyOCR handle detection
            try:
                logger.info("Attempting to initialize EasyOCR with GPU (auto-detect, en + ch_sim)...")
                easyocr_reader = easyocr.Reader(languages, gpu=True)
                logger.info("EasyOCR reader initialized successfully (English + Simplified Chinese)")
            except Exception as e:
                logger.warning(f"Failed to initialize EasyOCR with GPU (auto-detect, en + ch_sim): {e}")
                logger.info("Falling back to CPU...")
                try:
                    easyocr_reader = easyocr.Reader(languages, gpu=False)
                    logger.info("EasyOCR reader initialized successfully with CPU (English + Simplified Chinese)")
                except Exception as e2:
                    logger.error(f"Failed to initialize EasyOCR with CPU: {e2}")
        else:
            # Use CPU
            try:
                easyocr_reader = easyocr.Reader(languages, gpu=False)
                logger.info("EasyOCR reader initialized successfully with CPU (English + Simplified + Traditional Chinese)")
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR with CPU (en + ch_sim): {e}")
    return easyocr_reader

def run_with_timeout(func, timeout_seconds=15, default_return=None):
    """Run a function with a timeout. Returns default_return if timeout."""
    result = [default_return]
    exception = [None]
    
    def target():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout_seconds)
    
    if thread.is_alive():
        logger.warning(f"Function {func.__name__ if hasattr(func, '__name__') else 'unknown'} timed out after {timeout_seconds}s")
        return default_return
    
    if exception[0]:
        raise exception[0]
    
    return result[0]

app = Flask(__name__)
# Configure CORS to allow all origins (for mobile app development)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "max_age": 3600
    }
})

# Add request logging middleware
@app.before_request
def log_request_info():
    try:
        logger.info(f"Request: {request.method} {request.path}")
        logger.info(f"Remote address: {request.remote_addr}")
    except Exception as e:
        logger.error(f"Error in request logging: {e}")

@app.route("/api/health", methods=["GET", "POST"])
def health():
    return jsonify({"status": "ok", "message": "Server is running"}), 200

def detect_text_regions(img_cv):
    """Detect text regions using contour detection"""
    try:
        # Use morphological operations to find text regions
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
        morph = cv2.morphologyEx(img_cv, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # Get bounding boxes
        boxes = [cv2.boundingRect(c) for c in contours]
        boxes = [b for b in boxes if b[2] * b[3] > 100]  # Filter small regions
        
        if not boxes:
            return None
        
        # Get combined bounding box
        x = min(b[0] for b in boxes)
        y = min(b[1] for b in boxes)
        w = max(b[0] + b[2] for b in boxes) - x
        h = max(b[1] + b[3] for b in boxes) - y
        
        # Add padding
        padding = 10
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(img_cv.shape[1] - x, w + 2 * padding)
        h = min(img_cv.shape[0] - y, h + 2 * padding)
        
        return (x, y, w, h)
    except Exception as e:
        logger.warning(f"Text region detection failed: {e}")
        return None

def deskew_image(img_cv):
    """Deskew image by detecting rotation angle"""
    try:
        # Convert to binary
        _, binary = cv2.threshold(img_cv, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find all non-zero points
        coords = np.column_stack(np.where(binary > 0))
        
        if len(coords) < 10:
            return img_cv
        
        # Get minimum area rectangle
        angle = cv2.minAreaRect(coords)[-1]
        
        # Correct angle
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # Only correct if angle is significant
        if abs(angle) < 0.5:
            return img_cv
        
        # Rotate image
        (h, w) = img_cv.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img_cv, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        logger.info(f"Deskewed image by {angle:.2f} degrees")
        return rotated
    except Exception as e:
        logger.warning(f"Deskew failed: {e}")
        return img_cv

def preprocess_image_advanced(img, apply_deskew=True):
    """
    Advanced image preprocessing pipeline:
    1. Convert to RGB if needed
    2. Resize if too large
    3. Convert to grayscale
    4. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    5. Denoise
    6. Adaptive thresholding/binarization
    7. Deskew (optional, only when apply_deskew=True)
    8. Crop to text regions (optional)
    """
    # Convert PIL to OpenCV format
    if isinstance(img, Image.Image):
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    else:
        img_cv = img.copy()
    
    # Convert to RGB if needed (handles RGBA, P, etc.)
    if len(img_cv.shape) == 3 and img_cv.shape[2] == 4:
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGRA2BGR)
    
    # Resize if image is too large (improves speed and sometimes accuracy)
    max_width = 2000
    if img_cv.shape[1] > max_width:
        ratio = max_width / img_cv.shape[1]
        new_height = int(img_cv.shape[0] * ratio)
        img_cv = cv2.resize(img_cv, (max_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        logger.info(f"Resized image to: {img_cv.shape[1]}x{img_cv.shape[0]}")
    
    # Convert to grayscale
    if len(img_cv.shape) == 3:
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    else:
        gray = img_cv.copy()
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    # Denoise using bilateral filter (preserves edges)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # Deskew the image if requested
    if apply_deskew:
        gray = deskew_image(gray)
    else:
        logger.info("Skipping deskew step because text was already detected")
    
    # Skip text region cropping - it often removes important text
    # text_region = detect_text_regions(gray)
    # if text_region:
    #     x, y, w, h = text_region
    #     gray = gray[y:y+h, x:x+w]
    #     logger.info(f"Cropped to text region: {w}x{h}")
    
    # Apply adaptive thresholding (binarization)
    # Try multiple methods and use the best one
    adaptive_thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Also try Otsu's thresholding
    _, otsu_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Return both versions - OCR can try both
    return {
        'adaptive': adaptive_thresh,
        'otsu': otsu_thresh,
        'grayscale': gray  # Also keep grayscale for some OCR engines
    }

def clean_ocr_text(text):
    """Clean OCR text by removing common artifacts and noise"""
    if not text:
        return ""
    
    # Remove common OCR artifacts
    import re
    # Remove excessive whitespace (but preserve single spaces)
    text = re.sub(r'\s+', ' ', text)
    # Remove trailing/leading special characters that are often OCR errors
    text = re.sub(r'^[<>\|`~]+', '', text)
    text = re.sub(r'[<>\|`~]+$', '', text)
    # Remove single character lines that are likely noise
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        # Keep lines that are meaningful (more than 1 char, or common single chars like 'a', 'I')
        if len(line) > 1 or line.lower() in ['a', 'i']:
            cleaned_lines.append(line)
    text = ' '.join(cleaned_lines)
    
    # Remove spaces in short words that might be OCR errors (e.g., "Jo e" -> "Joe")
    # Only for very short text (likely single words)
    if len(text) < 10:
        text = text.replace(' ', '')
    
    return text.strip()

def ocr_with_easyocr(img):
    """Perform OCR using EasyOCR (usually better for camera images)"""
    try:
        reader = get_easyocr_reader()
        if reader is None:
            return []
        
        # EasyOCR works best with original images, not heavily preprocessed ones
        # Convert PIL to numpy array
        if isinstance(img, Image.Image):
            # Ensure RGB mode
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_array = np.array(img)
        else:
            img_array = img
        
        # Ensure 3-channel RGB
        if len(img_array.shape) == 2:  # Grayscale
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
        elif img_array.shape[2] == 4:  # RGBA
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
        
        results = []
        
        # Try original image first (EasyOCR's strength)
        try:
            logger.info("Running EasyOCR on original image (timeout: 15s)...")
            detections = run_with_timeout(
                lambda: reader.readtext(img_array),
                timeout_seconds=15,
                default_return=[]
            )
            
            if detections:
                logger.info(f"EasyOCR detected {len(detections)} text regions")

                # Filter out low-confidence detections
                filtered = [det for det in detections if float(det[2]) >= MIN_CONFIDENCE]

                # Log all detections for debugging
                for i, det in enumerate(detections):
                    confidence = float(det[2])
                    kept = confidence >= MIN_CONFIDENCE
                    logger.info(
                        f"  Detection {i+1}: '{det[1]}' (confidence: {confidence:.3f}) "
                        f"{'(kept)' if kept else '(discarded < MIN_CONFIDENCE)'}"
                    )

                if not filtered:
                    logger.warning(
                        f"All EasyOCR detections on original image were below "
                        f"MIN_CONFIDENCE={MIN_CONFIDENCE}"
                    )

                # Combine only high-confidence text
                text_parts = [det[1] for det in filtered]
                text = ' '.join(text_parts).strip()
                text = clean_ocr_text(text)

                if text:
                    avg_confidence = (
                        sum(float(det[2]) for det in filtered) / max(1, len(filtered))
                    )
                    results.append({
                        'text': text,
                        'length': len(text),
                        'config': 'original_easyocr',
                        'engine': 'easyocr',
                        'confidence': avg_confidence
                    })
                # Do not return any text if everything is below MIN_CONFIDENCE
            else:
                logger.warning("EasyOCR on original image returned no results or timed out")
        except Exception as e:
            logger.warning(f"EasyOCR failed with original image: {e}")
        
        # Also try with light preprocessing (resize if too large)
        try:
            max_width = 2000
            if img_array.shape[1] > max_width:
                ratio = max_width / img_array.shape[1]
                new_height = int(img_array.shape[0] * ratio)
                img_resized = cv2.resize(img_array, (max_width, new_height), interpolation=cv2.INTER_LANCZOS4)
                logger.info(f"Resized image to {max_width}x{new_height}")
            else:
                img_resized = img_array
            
            logger.info("Running EasyOCR on resized image (timeout: 15s)...")
            detections = run_with_timeout(
                lambda: reader.readtext(img_resized),
                timeout_seconds=15,
                default_return=[]
            )
            
            if detections:
                logger.info(f"EasyOCR (resized) detected {len(detections)} text regions")

                # Filter out low-confidence detections
                filtered = [det for det in detections if float(det[2]) >= MIN_CONFIDENCE]

                # Log all detections for debugging
                for i, det in enumerate(detections):
                    confidence = float(det[2])
                    kept = confidence >= MIN_CONFIDENCE
                    logger.info(
                        f"  Detection {i+1}: '{det[1]}' (confidence: {confidence:.3f}) "
                        f"{'(kept)' if kept else '(discarded < MIN_CONFIDENCE)'}"
                    )

                if not filtered:
                    logger.warning(
                        f"All EasyOCR detections on resized image were below "
                        f"MIN_CONFIDENCE={MIN_CONFIDENCE}"
                    )

                # Combine only high-confidence text
                text_parts = [det[1] for det in filtered]
                text = ' '.join(text_parts).strip()
                text = clean_ocr_text(text)

                if text:
                    avg_confidence = (
                        sum(float(det[2]) for det in filtered) / max(1, len(filtered))
                    )
                    results.append({
                        'text': text,
                        'length': len(text),
                        'config': 'resized_easyocr',
                        'engine': 'easyocr',
                        'confidence': avg_confidence
                    })
                # Do not return any text if everything is below MIN_CONFIDENCE
            else:
                logger.warning("EasyOCR on resized image returned no results or timed out")
        except Exception as e:
            logger.warning(f"EasyOCR failed with resized image: {e}")
        
        return results
    except Exception as e:
        logger.error(f"EasyOCR error: {e}")
        return []

def ocr_with_preprocess_easyocr(img, apply_deskew=True):
    """
    Run OCR with OpenCV-preprocessed versions of the image.
    This dramatically increases accuracy on mobile camera captures.
    """
    reader = get_easyocr_reader()
    if reader is None:
        return []

    # Preprocess image with your advanced pipeline
    processed = preprocess_image_advanced(img, apply_deskew=apply_deskew)  # returns grayscale, adaptive, otsu

    candidates = []

    for name, proc_img in processed.items():
        try:
            # Convert grayscale/BW back to 3-channel RGB for EasyOCR
            if len(proc_img.shape) == 2:
                proc_rgb = cv2.cvtColor(proc_img, cv2.COLOR_GRAY2RGB)
            else:
                proc_rgb = proc_img

            logger.info(f"Running EasyOCR on preprocessed {name} (timeout: 15s)...")
            detections = run_with_timeout(
                lambda: reader.readtext(proc_rgb),
                timeout_seconds=15,
                default_return=[]
            )

            if detections:
                # Filter out low-confidence detections
                filtered = [d for d in detections if float(d[2]) >= MIN_CONFIDENCE]

                # Log all detections for debugging
                for i, d in enumerate(detections):
                    confidence = float(d[2])
                    kept = confidence >= MIN_CONFIDENCE
                    logger.info(
                        f"  [{name}] Detection {i+1}: '{d[1]}' (confidence: {confidence:.3f}) "
                        f"{'(kept)' if kept else '(discarded < MIN_CONFIDENCE)'}"
                    )

                if not filtered:
                    logger.warning(
                        f"[{name}] All EasyOCR detections were below MIN_CONFIDENCE={MIN_CONFIDENCE}"
                    )

                # Use only high-confidence detections
                text_parts = [d[1] for d in filtered]
                text = " ".join(text_parts).strip()
                text = clean_ocr_text(text)

                if text and filtered:
                    avg_conf = (
                        sum(float(d[2]) for d in filtered)
                        / max(1, len(filtered))
                    )
                    candidates.append({
                        "text": text,
                        "engine": "easyocr",
                        "config": f"preprocess_{name}",
                        "confidence": avg_conf,
                        "length": len(text)
                    })
                # Do not return any text if everything is below MIN_CONFIDENCE

                logger.info(f"[{name}] detections: {len(detections)}")
            else:
                logger.warning(f"[{name}] returned no results or timed out")

        except Exception as e:
            logger.warning(f"EasyOCR failed on {name}: {e}")

    return candidates

@app.route("/api/test", methods=["GET", "POST", "OPTIONS"])
def test():
    """Simple test endpoint to verify connectivity"""
    logger.info(f"Test endpoint called from {request.remote_addr}")
    
    # Pre-initialize EasyOCR on first test call to avoid timeout on first OCR request
    try:
        get_easyocr_reader()
    except Exception as e:
        logger.warning(f"Could not pre-initialize EasyOCR: {e}")
    
    return jsonify({
        "status": "ok", 
        "message": "Connection successful", 
        "ip": request.remote_addr,
        "server_ip": "172.16.134.182",
        "port": 5001,
        "easyocr_ready": easyocr_reader is not None
    }), 200

@app.route("/api/ocr", methods=["POST", "OPTIONS"])
def ocr():
    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    
    try:
        logger.info("Received OCR request")
        # Get the base64 image from request
        data = request.get_json()
        if not data or "image" not in data:
            logger.warning("No image provided in request")
            return jsonify({"error": "No image provided"}), 400
        
        base64_str = data["image"]
        logger.info(f"Image data length: {len(base64_str)}")
        
        # Remove data URL prefix if present
        if base64_str.startswith("data:image"):
            base64_str = base64_str.split(",")[1]
        
        # Decode base64 to image
        logger.info("Decoding base64 image...")
        img_bytes = base64.b64decode(base64_str)
        img = Image.open(io.BytesIO(img_bytes))
        logger.info(f"Image opened: {img.size}, mode: {img.mode}")
        
        # Original EasyOCR passes (with 15s timeout per pass)
        logger.info("Starting original EasyOCR passes...")
        easyocr_original = ocr_with_easyocr(img)
        logger.info(f"Original EasyOCR completed: {len(easyocr_original)} results")

        apply_deskew = len(easyocr_original) == 0
        if apply_deskew:
            logger.info("No text from original OCR; enabling deskew for preprocessing")
        else:
            logger.info("Text detected in original OCR; skipping deskew during preprocessing")

        # Preprocessed EasyOCR passes (OpenCV enhanced, with 15s timeout per pass)
        logger.info("Starting preprocessed EasyOCR passes...")
        easyocr_preprocessed = ocr_with_preprocess_easyocr(img, apply_deskew=apply_deskew)
        logger.info(f"Preprocessed EasyOCR completed: {len(easyocr_preprocessed)} results")

        # Combine all results
        all_results = easyocr_original + easyocr_preprocessed
        logger.info(f"Total results collected: {len(all_results)}")

        if not all_results:
            return jsonify({"text": "No text detected"})

        # Sort by confidence + text length
        def score(r):
            score = r["confidence"] * 100
            score += r["length"]
            return score

        all_results.sort(key=score, reverse=True)
        best = all_results[0]

        logger.info(f"Selected best OCR: {best['config']} conf={best['confidence']:.3f}")

        return jsonify({
            "text": best['text'],
            "confidence": best['confidence'],
            "engine": best['engine'],
            "mode": best['config']
        })
    
    except Exception as e:
        logger.error(f"Error processing OCR: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info("Starting Flask server on 0.0.0.0:5001 (accessible from network)")
    # Pre-initialize EasyOCR in background to avoid first-request timeout
    logger.info("Pre-initializing EasyOCR (this may take a moment)...")
    try:
        get_easyocr_reader()
        logger.info("EasyOCR pre-initialized successfully")
    except Exception as e:
        logger.warning(f"Could not pre-initialize EasyOCR: {e}. Will initialize on first use.")
    
    app.run(host="0.0.0.0", port=5001, threaded=True, debug=False)

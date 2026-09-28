#!/usr/bin/env python3
"""
Preprocess a portrait photo for ASCII conversion:
1. Remove background with rembg to isolate the subject.
2. Crop to subject bounding box with proportional padding.
3. Boost local contrast with OpenCV's CLAHE for distinct facial features and highlights.
4. Composite onto pure white (255) so background maps to spaces in ASCII ramp.
Outputs grayscale 'source-prepped.png'.
"""

import sys
import os
import cv2
import numpy as np
from PIL import Image
from rembg import remove

DEFAULT_INPUT = "source-photo.jpg"
DEFAULT_OUTPUT = "source-prepped.png"

def prep_photo(input_path: str = DEFAULT_INPUT, output_path: str = DEFAULT_OUTPUT):
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        sys.exit(1)
        
    print(f"Loading '{input_path}'...")
    with open(input_path, "rb") as f:
        input_data = f.read()
        
    print("Removing background with rembg...")
    cutout_data = remove(input_data)
    
    # Load into PIL Image (RGBA)
    import io
    pil_rgba = Image.open(io.BytesIO(cutout_data)).convert("RGBA")
    
    # Crop to bounding box of the non-transparent subject
    alpha = np.array(pil_rgba.split()[-1])
    coords = cv2.findNonZero((alpha > 20).astype(np.uint8))
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        # Add slight margin
        pad_x = int(w * 0.05)
        pad_y = int(h * 0.05)
        img_w, img_h = pil_rgba.size
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(img_w, x + w + pad_x)
        y2 = min(img_h, y + h + pad_y)
        pil_rgba = pil_rgba.crop((x1, y1, x2, y2))
        print(f"Cropped to subject bounding box: ({x1}, {y1}, {x2}, {y2})")

    np_rgba = np.array(pil_rgba)
    rgb = np_rgba[:, :, :3]
    alpha_mask = np_rgba[:, :, 3].astype(np.float32) / 255.0

    print("Converting to grayscale and applying CLAHE contrast enhancement...")
    # Convert RGB to grayscale
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    
    # CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8))
    enhanced_gray = clahe.apply(gray)
    
    # Composite onto pure white (255)
    # Background (alpha == 0) becomes 255 (white -> space glyph in ASCII ramp)
    white_bg = np.ones_like(enhanced_gray, dtype=np.float32) * 255.0
    composited = (enhanced_gray.astype(np.float32) * alpha_mask + white_bg * (1.0 - alpha_mask)).astype(np.uint8)
    
    # Save as grayscale PNG
    output_pil = Image.fromarray(composited, mode="L")
    output_pil.save(output_path)
    print(f"Prepped photo saved to '{output_path}' ({output_pil.size[0]}x{output_pil.size[1]})")

def main():
    inp = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    out = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT
    prep_photo(inp, out)

if __name__ == "__main__":
    main()

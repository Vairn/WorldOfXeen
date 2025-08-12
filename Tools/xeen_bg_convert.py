#!/usr/bin/env python3
"""
World of Xeen Background Converter

Converts raw background images to Amiga bitplane format.
Matches the C++ code exactly: f.read((byte *)getPixels(), SCREEN_WIDTH * SCREEN_HEIGHT)
"""

import argparse
import os
import struct
import logging
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_background(filepath: str, width: int = 320, height: int = 200) -> bytes:
    """Load background exactly like C++: f.read((byte *)getPixels(), SCREEN_WIDTH * SCREEN_HEIGHT)"""
    expected_size = width * height
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    if len(data) != expected_size:
        raise ValueError(f"Invalid image size: {len(data)} bytes, expected {expected_size}")
    
    logger.info(f"Loaded {width}x{height} background from {filepath}")
    return data

def load_palette(filepath: str) -> bytes:
    """Load palette exactly like C++: _tempPalette[i] = f.readByte() << 2"""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    if len(data) != 256 * 3:
        raise ValueError(f"Invalid palette size: {len(data)} bytes, expected {256 * 3}")
    
    # Apply 6-bit to 8-bit conversion: f.readByte() << 2
    palette = bytearray()
    for i in range(256):
        r = min(255, data[i*3] << 2)
        g = min(255, data[i*3+1] << 2)
        b = min(255, data[i*3+2] << 2)
        palette.extend([r, g, b])
    
    logger.info(f"Loaded palette from {filepath}")
    return bytes(palette)

def save_png_preview(pixel_data: bytes, palette_data: bytes, output_path: str, width: int = 320, height: int = 200):
    """Save PNG preview with correct colors"""
    try:
        from PIL import Image
        
        # Create image from raw pixel data (row-major order)
        img = Image.frombytes('P', (width, height), pixel_data)
        
        # Apply palette
        img.putpalette(palette_data)
        
        # Save
        img.save(output_path)
        logger.info(f"Saved preview to {output_path}")
        return True
        
    except ImportError:
        logger.warning("PIL not available, skipping PNG preview")
        return False
    except Exception as e:
        logger.error(f"Error creating preview: {e}")
        return False

def convert_to_bitplanes(pixel_data: bytes, width: int = 320, height: int = 200, num_planes: int = 8) -> list:
    """Convert to Amiga bitplanes"""
    # Convert to 2D array for easier processing
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            pixel = pixel_data[y * width + x]
            row.append(pixel)
        pixels.append(row)
    
    # Convert to bitplanes
    bitplanes = []
    for plane in range(num_planes):
        plane_data = bytearray()
        for y in range(height):
            for x in range(0, width, 8):
                byte_val = 0
                for bit in range(8):
                    if x + bit < width:
                        if (pixels[y][x + bit] >> plane) & 1:
                            byte_val |= (1 << bit)
                plane_data.append(byte_val)
        bitplanes.append(bytes(plane_data))
    
    logger.info(f"Converted to {num_planes} bitplanes")
    return bitplanes

def save_bitplanes(bitplanes: list, output_path: str, width: int = 320, height: int = 200):
    """Save bitplanes to file"""
    with open(output_path, 'wb') as f:
        # Write header: width, height, num_planes, data_size
        f.write(struct.pack('<IIII', width, height, len(bitplanes), len(bitplanes[0])))
        
        # Write each bitplane
        for plane_data in bitplanes:
            f.write(plane_data)
    
    logger.info(f"Saved bitplanes to {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Convert World of Xeen backgrounds to Amiga format')
    parser.add_argument('--input', '-i', required=True, help='Input raw image file')
    parser.add_argument('--output', '-o', required=True, help='Output directory')
    parser.add_argument('--width', type=int, default=320, help='Image width')
    parser.add_argument('--height', type=int, default=200, help='Image height')
    parser.add_argument('--bitplanes', type=int, default=8, help='Number of bitplanes')
    parser.add_argument('--palette', help='Palette file for preview generation')
    parser.add_argument('--preview', action='store_true', help='Generate preview image')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input file
    if not os.path.exists(args.input):
        logger.error(f"Input file not found: {args.input}")
        return 1
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    try:
        # Load background exactly like C++
        pixel_data = load_background(args.input, args.width, args.height)
        
        # Get base filename
        base_name = Path(args.input).stem
        
        # Generate bitplanes
        bitplanes = convert_to_bitplanes(pixel_data, args.width, args.height, args.bitplanes)
        
        # Save bitplanes
        output_path = os.path.join(args.output, f"{base_name}.bpl")
        save_bitplanes(bitplanes, output_path, args.width, args.height)
        
        # Generate preview if requested
        if args.preview:
            if args.palette and os.path.exists(args.palette):
                palette_data = load_palette(args.palette)
                preview_path = os.path.join(args.output, f"{base_name}_preview.png")
                save_png_preview(pixel_data, palette_data, preview_path, args.width, args.height)
            else:
                logger.warning("No palette file provided, skipping preview")
        
        logger.info(f"Background conversion complete. Output: {args.output}")
        return 0
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        return 1

if __name__ == '__main__':
    exit(main())

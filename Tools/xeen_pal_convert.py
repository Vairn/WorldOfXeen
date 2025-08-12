#!/usr/bin/env python3
"""
World of Xeen Palette Converter

Converts original game palettes to Amiga format with support for:
- AGA: 256 colors (12-bit RGB)
- ECS: 64 colors (6-bit RGB) 
- OCS: 32 colors (5-bit RGB)

Includes color quantization and remap table generation for limited color modes.
"""

import argparse
import os
import struct
import json
import logging
from pathlib import Path
from typing import List, Tuple, Dict
import numpy as np
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AmigaPalette:
    """Amiga palette converter and quantizer"""
    
    def __init__(self):
        self.aga_colors = []  # 12-bit RGB values
        self.ecs_colors = []  # 6-bit RGB values  
        self.ocs_colors = []  # 5-bit RGB values
        self.remap_table = {}  # Original -> quantized color mapping
        
    def load_palette(self, filepath: str) -> bool:
        """Load 256-color RGB palette from file"""
        try:
            with open(filepath, 'rb') as f:
                # Read 256 RGB triplets (3 bytes each)
                data = f.read(256 * 3)
                if len(data) != 256 * 3:
                    logger.error(f"Invalid palette file size: {len(data)} bytes")
                    return False
                
                # Convert to RGB values
                self.original_colors = []
                for i in range(256):
                    r, g, b = struct.unpack('BBB', data[i*3:(i+1)*3])
                    self.original_colors.append((r, g, b))
                
                logger.info(f"Loaded {len(self.original_colors)} colors from {filepath}")
                return True
                
        except Exception as e:
            logger.error(f"Error loading palette: {e}")
            return False
    
    def convert_to_aga(self) -> List[int]:
        """Convert to AGA 12-bit RGB format"""
        aga_colors = []
        
        for r, g, b in self.original_colors:
            # Convert 8-bit to 12-bit (scale 0-255 to 0-4095)
            r_12 = (r * 4095) // 255
            g_12 = (g * 4095) // 255
            b_12 = (b * 4095) // 255
            
            # Pack into 16-bit value (4 bits each for R,G,B)
            aga_color = (r_12 >> 4) | ((g_12 >> 4) << 4) | ((b_12 >> 4) << 8)
            aga_colors.append(aga_color)
        
        self.aga_colors = aga_colors
        logger.info(f"Converted to {len(aga_colors)} AGA colors")
        return aga_colors
    
    def quantize_colors(self, target_colors: int, method: str = 'median_cut') -> List[Tuple[int, int, int]]:
        """Quantize colors to target palette size"""
        if method == 'median_cut':
            return self._median_cut_quantization(target_colors)
        elif method == 'kmeans':
            return self._kmeans_quantization(target_colors)
        else:
            logger.error(f"Unknown quantization method: {method}")
            return []
    
    def _median_cut_quantization(self, target_colors: int) -> List[Tuple[int, int, int]]:
        """Median cut color quantization"""
        # Convert to numpy array for easier processing
        colors = np.array(self.original_colors, dtype=np.float32)
        
        # Initialize with all colors
        boxes = [colors]
        
        # Split boxes until we have enough colors
        while len(boxes) < target_colors:
            # Find box with largest range
            largest_box_idx = 0
            largest_range = 0
            
            for i, box in enumerate(boxes):
                if len(box) == 0:
                    continue
                    
                # Calculate range for each channel
                ranges = np.max(box, axis=0) - np.min(box, axis=0)
                max_range = np.max(ranges)
                
                if max_range > largest_range:
                    largest_range = max_range
                    largest_box_idx = i
            
            # Split the largest box
            box = boxes[largest_box_idx]
            if len(box) == 0:
                break
                
            # Find channel with largest range
            ranges = np.max(box, axis=0) - np.min(box, axis=0)
            split_channel = np.argmax(ranges)
            
            # Sort by that channel and split at median
            sorted_indices = np.argsort(box[:, split_channel])
            median_idx = len(box) // 2
            
            box1 = box[sorted_indices[:median_idx]]
            box2 = box[sorted_indices[median_idx:]]
            
            # Replace original box with split boxes
            boxes[largest_box_idx] = box1
            boxes.append(box2)
        
        # Calculate representative color for each box (mean)
        quantized_colors = []
        for box in boxes:
            if len(box) > 0:
                mean_color = np.mean(box, axis=0)
                quantized_colors.append(tuple(map(int, mean_color)))
        
        return quantized_colors[:target_colors]
    
    def _kmeans_quantization(self, target_colors: int) -> List[Tuple[int, int, int]]:
        """K-means color quantization (simplified)"""
        # Simple k-means implementation
        colors = np.array(self.original_colors, dtype=np.float32)
        
        # Initialize centroids randomly
        indices = np.random.choice(len(colors), target_colors, replace=False)
        centroids = colors[indices].copy()
        
        # Iterate until convergence
        for iteration in range(10):
            # Assign colors to nearest centroid
            distances = np.sqrt(((colors[:, np.newaxis, :] - centroids[np.newaxis, :, :]) ** 2).sum(axis=2))
            assignments = np.argmin(distances, axis=1)
            
            # Update centroids
            new_centroids = np.zeros_like(centroids)
            counts = np.zeros(target_colors)
            
            for i, assignment in enumerate(assignments):
                new_centroids[assignment] += colors[i]
                counts[assignment] += 1
            
            # Avoid division by zero
            for i in range(target_colors):
                if counts[i] > 0:
                    new_centroids[i] /= counts[i]
            
            # Check convergence
            if np.allclose(centroids, new_centroids):
                break
                
            centroids = new_centroids
        
        return [tuple(map(int, centroid)) for centroid in centroids]
    
    def create_remap_table(self, quantized_colors: List[Tuple[int, int, int]]) -> Dict[int, int]:
        """Create mapping from original colors to quantized palette"""
        remap = {}
        
        for i, original_color in enumerate(self.original_colors):
            # Find closest quantized color
            min_distance = float('inf')
            closest_idx = 0
            
            for j, quantized_color in enumerate(quantized_colors):
                distance = sum((a - b) ** 2 for a, b in zip(original_color, quantized_color))
                if distance < min_distance:
                    min_distance = distance
                    closest_idx = j
            
            remap[i] = closest_idx
        
        self.remap_table = remap
        return remap
    
    def convert_to_ecs(self) -> List[int]:
        """Convert to ECS 64-color format"""
        # Quantize to 64 colors
        quantized = self.quantize_colors(64, 'median_cut')
        
        # Convert to ECS 6-bit format
        ecs_colors = []
        for r, g, b in quantized:
            # Convert to 6-bit (scale 0-255 to 0-63)
            r_6 = (r * 63) // 255
            g_6 = (g * 63) // 255
            b_6 = (b * 63) // 255
            
            # Pack into 16-bit value (6 bits each for R,G,B)
            ecs_color = r_6 | (g_6 << 6) | (b_6 << 12)
            ecs_colors.append(ecs_color)
        
        self.ecs_colors = ecs_colors
        self.create_remap_table(quantized)
        logger.info(f"Converted to {len(ecs_colors)} ECS colors")
        return ecs_colors
    
    def convert_to_ocs(self) -> List[int]:
        """Convert to OCS 32-color format"""
        # Quantize to 32 colors
        quantized = self.quantize_colors(32, 'median_cut')
        
        # Convert to OCS 5-bit format
        ocs_colors = []
        for r, g, b in quantized:
            # Convert to 5-bit (scale 0-255 to 0-31)
            r_5 = (r * 31) // 255
            g_5 = (g * 31) // 255
            b_5 = (b * 31) // 255
            
            # Pack into 16-bit value (5 bits each for R,G,B)
            ocs_color = r_5 | (g_5 << 5) | (b_5 << 10)
            ocs_colors.append(ocs_color)
        
        self.ocs_colors = ocs_colors
        self.create_remap_table(quantized)
        logger.info(f"Converted to {len(ocs_colors)} OCS colors")
        return ocs_colors
    
    def save_aga_palette(self, filepath: str) -> bool:
        """Save AGA palette to binary file"""
        try:
            with open(filepath, 'wb') as f:
                # Write 256 16-bit color values
                for color in self.aga_colors:
                    f.write(struct.pack('<H', color))
            
            logger.info(f"Saved AGA palette to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving AGA palette: {e}")
            return False
    
    def save_ecs_palette(self, filepath: str) -> bool:
        """Save ECS palette to binary file"""
        try:
            with open(filepath, 'wb') as f:
                # Write 64 16-bit color values
                for color in self.ecs_colors:
                    f.write(struct.pack('<H', color))
            
            logger.info(f"Saved ECS palette to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving ECS palette: {e}")
            return False
    
    def save_ocs_palette(self, filepath: str) -> bool:
        """Save OCS palette to binary file"""
        try:
            with open(filepath, 'wb') as f:
                # Write 32 16-bit color values
                for color in self.ocs_colors:
                    f.write(struct.pack('<H', color))
            
            logger.info(f"Saved OCS palette to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving OCS palette: {e}")
            return False
    
    def save_remap_table(self, filepath: str) -> bool:
        """Save remap table to binary file"""
        try:
            with open(filepath, 'wb') as f:
                # Write 256 8-bit remap indices
                for i in range(256):
                    remap_idx = self.remap_table.get(i, 0)
                    f.write(struct.pack('B', remap_idx))
            
            logger.info(f"Saved remap table to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving remap table: {e}")
            return False
    
    def save_metadata(self, filepath: str) -> bool:
        """Save palette metadata to JSON"""
        try:
            metadata = {
                'original_colors': len(self.original_colors),
                'aga_colors': len(self.aga_colors),
                'ecs_colors': len(self.ecs_colors),
                'ocs_colors': len(self.ocs_colors),
                'has_remap_table': bool(self.remap_table)
            }
            
            with open(filepath, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved metadata to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Convert World of Xeen palettes to Amiga format')
    parser.add_argument('--input', '-i', required=True, help='Input palette file (.pal)')
    parser.add_argument('--output', '-o', required=True, help='Output directory')
    parser.add_argument('--aga', action='store_true', help='Generate AGA palette')
    parser.add_argument('--ecs', action='store_true', help='Generate ECS palette')
    parser.add_argument('--ocs', action='store_true', help='Generate OCS palette')
    parser.add_argument('--all', action='store_true', help='Generate all formats')
    parser.add_argument('--quantization', choices=['median_cut', 'kmeans'], default='median_cut', help='Quantization method')
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
    
    # Create palette converter
    palette = AmigaPalette()
    
    # Load original palette
    if not palette.load_palette(args.input):
        return 1
    
    # Determine which formats to generate
    generate_aga = args.aga or args.all
    generate_ecs = args.ecs or args.all
    generate_ocs = args.ocs or args.all
    
    if not any([generate_aga, generate_ecs, generate_ocs]):
        logger.error("No output format specified. Use --aga, --ecs, --ocs, or --all")
        return 1
    
    # Get base filename
    base_name = Path(args.input).stem
    
    # Generate palettes
    if generate_aga:
        palette.convert_to_aga()
        aga_path = os.path.join(args.output, f"{base_name}_aga.pal")
        palette.save_aga_palette(aga_path)
    
    if generate_ecs:
        palette.convert_to_ecs()
        ecs_path = os.path.join(args.output, f"{base_name}_ecs.pal")
        palette.save_ecs_palette(ecs_path)
        
        # Save remap table
        remap_path = os.path.join(args.output, f"{base_name}_ecs_remap.bin")
        palette.save_remap_table(remap_path)
    
    if generate_ocs:
        palette.convert_to_ocs()
        ocs_path = os.path.join(args.output, f"{base_name}_ocs.pal")
        palette.save_ocs_palette(ocs_path)
        
        # Save remap table
        remap_path = os.path.join(args.output, f"{base_name}_ocs_remap.bin")
        palette.save_remap_table(remap_path)
    
    # Save metadata
    metadata_path = os.path.join(args.output, f"{base_name}_metadata.json")
    palette.save_metadata(metadata_path)
    
    logger.info(f"Palette conversion complete. Output: {args.output}")
    return 0

if __name__ == '__main__':
    exit(main())

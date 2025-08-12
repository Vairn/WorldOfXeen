#!/usr/bin/env python3
"""
World of Xeen Batch Asset Converter

Automates the complete asset conversion workflow:
1. Extract CC archives
2. Convert palettes to Amiga format
3. Convert backgrounds to bitplanes
4. Convert sprites (placeholder)
5. Pack into XPA archive
"""

import argparse
import os
import sys
import subprocess
import logging
import json
from pathlib import Path
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BatchConverter:
    """Batch asset converter for World of Xeen"""
    
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.extracted_dir = os.path.join(output_dir, "extracted")
        self.converted_dir = os.path.join(output_dir, "converted")
        self.tools_dir = os.path.dirname(os.path.abspath(__file__))
        
    def run_command(self, cmd: List[str], description: str) -> bool:
        """Run a command and log the result"""
        logger.info(f"Running: {description}")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            if result.stdout:
                logger.debug(f"Output: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}")
            if e.stdout:
                logger.error(f"stdout: {e.stdout}")
            if e.stderr:
                logger.error(f"stderr: {e.stderr}")
            return False
    
    def extract_cc_archives(self) -> bool:
        """Extract all CC archives from input directory"""
        logger.info("Extracting CC archives...")
        
        # Find CC archives
        cc_files = []
        for file in os.listdir(self.input_dir):
            if file.upper().endswith('.CC'):
                cc_files.append(file)
        
        if not cc_files:
            logger.error("No CC archives found in input directory")
            return False
        
        # Create extracted directory
        os.makedirs(self.extracted_dir, exist_ok=True)
        
        # Extract each archive
        for cc_file in cc_files:
            cc_path = os.path.join(self.input_dir, cc_file)
            extract_dir = os.path.join(self.extracted_dir, Path(cc_file).stem.lower())
            
            cmd = [
                sys.executable,
                os.path.join(self.tools_dir, "xeencc_unpack.py"),
                "--input", cc_path,
                "--output", extract_dir
            ]
            
            if not self.run_command(cmd, f"Extracting {cc_file}"):
                return False
        
        logger.info(f"Extracted {len(cc_files)} CC archives")
        return True
    
    def convert_palettes(self) -> bool:
        """Convert all palette files to Amiga format"""
        logger.info("Converting palettes...")
        
        # Find palette files
        palette_files = []
        for root, dirs, files in os.walk(self.extracted_dir):
            for file in files:
                if file.lower().endswith('.pal'):
                    palette_files.append(os.path.join(root, file))
        
        if not palette_files:
            logger.warning("No palette files found")
            return True
        
        # Create palette output directory
        palette_dir = os.path.join(self.converted_dir, "pal")
        os.makedirs(palette_dir, exist_ok=True)
        
        # Convert each palette
        for palette_file in palette_files:
            base_name = Path(palette_file).stem
            
            cmd = [
                sys.executable,
                os.path.join(self.tools_dir, "xeen_pal_convert.py"),
                "--input", palette_file,
                "--output", palette_dir,
                "--all"  # Generate all formats (AGA, ECS, OCS)
            ]
            
            if not self.run_command(cmd, f"Converting palette {base_name}"):
                return False
        
        logger.info(f"Converted {len(palette_files)} palettes")
        return True
    
    def convert_backgrounds(self) -> bool:
        """Convert all background files to bitplanes"""
        logger.info("Converting backgrounds...")
        
        # Find background files (common extensions)
        bg_extensions = ['.raw', '.bg', '.bmp', '.dat']
        bg_files = []
        
        for root, dirs, files in os.walk(self.extracted_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in bg_extensions):
                    # Check if it might be a background (320x200 size)
                    file_path = os.path.join(root, file)
                    try:
                        size = os.path.getsize(file_path)
                        if size == 320 * 200:  # Likely a background
                            bg_files.append(file_path)
                    except:
                        pass
        
        if not bg_files:
            logger.warning("No background files found")
            return True
        
        # Create background output directory
        bg_dir = os.path.join(self.converted_dir, "bg")
        os.makedirs(bg_dir, exist_ok=True)
        
        # Find a palette file to use
        palette_file = None
        for root, dirs, files in os.walk(self.extracted_dir):
            for file in files:
                if file.lower().endswith('.pal'):
                    palette_file = os.path.join(root, file)
                    break
            if palette_file:
                break
        
        # Convert each background
        for bg_file in bg_files:
            base_name = Path(bg_file).stem
            
            cmd = [
                sys.executable,
                os.path.join(self.tools_dir, "xeen_bg_convert.py"),
                "--input", bg_file,
                "--output", bg_dir,
                "--width", "320",
                "--height", "200",
                "--bitplanes", "8",
                "--format", "raw",
                "--preview"
            ]
            
            # Add palette if found
            if palette_file:
                cmd.extend(["--palette", palette_file])
            
            if not self.run_command(cmd, f"Converting background {base_name}"):
                return False
        
        logger.info(f"Converted {len(bg_files)} backgrounds")
        return True
    
    def convert_sprites(self) -> bool:
        """Convert sprite resources and generate previews (DISABLED)"""
        logger.info("Sprite conversion disabled - skipping")
        return True
    
    def pack_assets(self) -> bool:
        """Pack all converted assets into XPA archive"""
        logger.info("Packing assets...")
        
        if not os.path.exists(self.converted_dir):
            logger.error("No converted assets found")
            return False
        
        # Create XPA archive
        xpa_path = os.path.join(self.output_dir, "amiga_assets.xpa")
        manifest_path = os.path.join(self.output_dir, "manifest.json")
        
        cmd = [
            sys.executable,
            os.path.join(self.tools_dir, "xeen_pack_assets.py"),
            "pack",
            "--root", self.converted_dir,
            "--output", xpa_path,
            "--manifest", manifest_path
        ]
        
        if not self.run_command(cmd, "Packing assets into XPA archive"):
            return False
        
        logger.info(f"Created XPA archive: {xpa_path}")
        return True
    
    def verify_assets(self) -> bool:
        """Verify the created XPA archive"""
        logger.info("Verifying assets...")
        
        xpa_path = os.path.join(self.output_dir, "amiga_assets.xpa")
        
        if not os.path.exists(xpa_path):
            logger.error("XPA archive not found")
            return False
        
        # List archive contents
        cmd = [
            sys.executable,
            os.path.join(self.tools_dir, "xeen_pack_assets.py"),
            "unpack",
            "--input", xpa_path,
            "--list"
        ]
        
        if not self.run_command(cmd, "Verifying XPA archive"):
            return False
        
        logger.info("Asset verification complete")
        return True
    
    def create_summary(self) -> bool:
        """Create a summary of the conversion process"""
        logger.info("Creating conversion summary...")
        
        summary = {
            "input_directory": self.input_dir,
            "output_directory": self.output_dir,
            "extracted_files": 0,
            "converted_palettes": 0,
            "converted_backgrounds": 0,
            "converted_sprites": 0,
            "xpa_archive": None,
            "manifest": None
        }
        
        # Count files
        if os.path.exists(self.extracted_dir):
            for root, dirs, files in os.walk(self.extracted_dir):
                summary["extracted_files"] += len(files)
        
        if os.path.exists(self.converted_dir):
            palette_dir = os.path.join(self.converted_dir, "pal")
            if os.path.exists(palette_dir):
                summary["converted_palettes"] = len([f for f in os.listdir(palette_dir) if f.endswith('.pal')])
            
            bg_dir = os.path.join(self.converted_dir, "bg")
            if os.path.exists(bg_dir):
                summary["converted_backgrounds"] = len([f for f in os.listdir(bg_dir) if f.endswith('.bpl')])
            
            # Sprite conversion disabled
            summary["converted_sprites"] = 0
        
        # Check for XPA archive
        xpa_path = os.path.join(self.output_dir, "amiga_assets.xpa")
        if os.path.exists(xpa_path):
            summary["xpa_archive"] = {
                "path": xpa_path,
                "size": os.path.getsize(xpa_path)
            }
        
        # Check for manifest
        manifest_path = os.path.join(self.output_dir, "manifest.json")
        if os.path.exists(manifest_path):
            summary["manifest"] = manifest_path
        
        # Save summary
        summary_path = os.path.join(self.output_dir, "conversion_summary.json")
        try:
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Saved conversion summary to {summary_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save summary: {e}")
            return False
    
    def run_conversion(self, skip_steps: List[str] = None) -> bool:
        """Run the complete conversion process"""
        if skip_steps is None:
            skip_steps = []
        
        logger.info("Starting World of Xeen asset conversion...")
        logger.info(f"Input directory: {self.input_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Run conversion steps
        steps = [
            ("extract", self.extract_cc_archives),
            ("palettes", self.convert_palettes),
            ("backgrounds", self.convert_backgrounds),
            ("sprites", self.convert_sprites),  # Disabled but kept for compatibility
            ("pack", self.pack_assets),
            ("verify", self.verify_assets),
            ("summary", self.create_summary)
        ]
        
        for step_name, step_func in steps:
            if step_name in skip_steps:
                logger.info(f"Skipping step: {step_name}")
                continue
            
            if not step_func():
                logger.error(f"Step '{step_name}' failed")
                return False
        
        logger.info("Asset conversion completed successfully!")
        return True

def main():
    parser = argparse.ArgumentParser(description='Batch convert World of Xeen assets to Amiga format')
    parser.add_argument('--input', '-i', required=True, help='Input directory containing CC archives')
    parser.add_argument('--output', '-o', required=True, help='Output directory for converted assets')
    parser.add_argument('--skip', nargs='*', choices=['extract', 'palettes', 'backgrounds', 'sprites', 'pack', 'verify', 'summary'], 
                       help='Steps to skip')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input directory
    if not os.path.exists(args.input):
        logger.error(f"Input directory not found: {args.input}")
        return 1
    
    # Create converter and run
    converter = BatchConverter(args.input, args.output)
    
    if converter.run_conversion(args.skip):
        logger.info("Conversion completed successfully!")
        return 0
    else:
        logger.error("Conversion failed!")
        return 1

if __name__ == '__main__':
    exit(main())

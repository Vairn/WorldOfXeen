#!/usr/bin/env python3
"""
World of Xeen Asset Packer

Creates a simple archive format (.xpa) for Amiga assets with:
- Indexed file access
- CRC32 verification
- Little-endian format for 68k compatibility
"""

import argparse
import os
import struct
import json
import logging
import hashlib
import zlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class XeenAssetPack:
    """Xeen Asset Packer for Amiga assets"""
    
    MAGIC = b'XPA\x00'
    VERSION = 1
    
    def __init__(self):
        self.entries = {}
        self.data_offset = 0
        
    def add_file(self, filepath: str, archive_path: str) -> bool:
        """Add a file to the archive"""
        try:
            if not os.path.exists(filepath):
                logger.error(f"File not found: {filepath}")
                return False
            
            # Read file data
            with open(filepath, 'rb') as f:
                data = f.read()
            
            # Calculate CRC32
            crc32 = zlib.crc32(data) & 0xFFFFFFFF
            
            # Store entry
            self.entries[archive_path] = {
                'filepath': filepath,
                'size': len(data),
                'crc32': crc32,
                'data': data
            }
            
            logger.info(f"Added {archive_path} ({len(data)} bytes, CRC32: {crc32:08x})")
            return True
            
        except Exception as e:
            logger.error(f"Error adding file {filepath}: {e}")
            return False
    
    def add_directory(self, directory: str, prefix: str = "") -> bool:
        """Add all files from a directory recursively"""
        success_count = 0
        total_count = 0
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                filepath = os.path.join(root, file)
                
                # Create archive path
                rel_path = os.path.relpath(filepath, directory)
                if prefix:
                    archive_path = f"{prefix}/{rel_path}"
                else:
                    archive_path = rel_path
                
                # Normalize path separators
                archive_path = archive_path.replace('\\', '/')
                
                if self.add_file(filepath, archive_path):
                    success_count += 1
                total_count += 1
        
        logger.info(f"Added {success_count}/{total_count} files from {directory}")
        return success_count == total_count
    
    def write_archive(self, filepath: str) -> bool:
        """Write archive to file"""
        try:
            with open(filepath, 'wb') as f:
                # Write header
                f.write(self.MAGIC)
                f.write(struct.pack('<I', self.VERSION))
                f.write(struct.pack('<I', len(self.entries)))
                
                # Calculate data offset
                header_size = 4 + 4 + 4  # magic + version + entry_count
                toc_size = len(self.entries) * (2 + 255 + 4 + 4 + 4)  # name_len + name + offset + size + crc32
                self.data_offset = header_size + toc_size
                
                # Write table of contents
                current_offset = self.data_offset
                for archive_path, entry in sorted(self.entries.items()):
                    # Write name length and name
                    name_bytes = archive_path.encode('utf-8')
                    f.write(struct.pack('<H', len(name_bytes)))
                    f.write(name_bytes)
                    
                    # Pad name to 255 bytes
                    padding = 255 - len(name_bytes)
                    if padding > 0:
                        f.write(b'\x00' * padding)
                    
                    # Write entry metadata
                    f.write(struct.pack('<III', current_offset, entry['size'], entry['crc32']))
                    current_offset += entry['size']
                
                # Write file data
                for archive_path, entry in sorted(self.entries.items()):
                    f.write(entry['data'])
            
            logger.info(f"Wrote archive to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing archive: {e}")
            return False
    
    def save_manifest(self, filepath: str) -> bool:
        """Save manifest with file information"""
        try:
            manifest = {
                'version': self.VERSION,
                'entry_count': len(self.entries),
                'data_offset': self.data_offset,
                'entries': {}
            }
            
            for archive_path, entry in sorted(self.entries.items()):
                manifest['entries'][archive_path] = {
                    'size': entry['size'],
                    'crc32': f"{entry['crc32']:08x}",
                    'filepath': entry['filepath']
                }
            
            with open(filepath, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            logger.info(f"Saved manifest to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving manifest: {e}")
            return False

class XeenAssetUnpack:
    """Xeen Asset Unpacker"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.entries = {}
        self.data_offset = 0
        
    def read_header(self) -> bool:
        """Read archive header and table of contents"""
        try:
            with open(self.filepath, 'rb') as f:
                # Read magic and version
                magic = f.read(4)
                if magic != XeenAssetPack.MAGIC:
                    logger.error(f"Invalid XPA magic: {magic}")
                    return False
                
                version = struct.unpack('<I', f.read(4))[0]
                if version != XeenAssetPack.VERSION:
                    logger.warning(f"Unexpected version: {version}")
                
                # Read entry count
                num_entries = struct.unpack('<I', f.read(4))[0]
                logger.info(f"XPA Archive version {version}, {num_entries} entries")
                
                # Read table of contents
                for i in range(num_entries):
                    # Read name
                    name_len = struct.unpack('<H', f.read(2))[0]
                    name_bytes = f.read(255)  # Always read 255 bytes
                    archive_path = name_bytes[:name_len].decode('utf-8')
                    
                    # Read metadata
                    offset, size, crc32 = struct.unpack('<III', f.read(12))
                    
                    self.entries[archive_path] = {
                        'offset': offset,
                        'size': size,
                        'crc32': crc32
                    }
                
                # Store data offset
                self.data_offset = f.tell()
                logger.info(f"Data starts at offset: {self.data_offset}")
                
                return True
                
        except Exception as e:
            logger.error(f"Error reading archive: {e}")
            return False
    
    def extract_file(self, archive_path: str, output_path: str) -> bool:
        """Extract a single file from the archive"""
        if archive_path not in self.entries:
            logger.error(f"Entry not found: {archive_path}")
            return False
        
        entry = self.entries[archive_path]
        
        try:
            with open(self.filepath, 'rb') as f:
                f.seek(entry['offset'])
                data = f.read(entry['size'])
                
                # Verify CRC32
                actual_crc32 = zlib.crc32(data) & 0xFFFFFFFF
                if actual_crc32 != entry['crc32']:
                    logger.error(f"CRC32 mismatch for {archive_path}: expected {entry['crc32']:08x}, got {actual_crc32:08x}")
                    return False
                
                # Create output directory
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Write file
                with open(output_path, 'wb') as out_f:
                    out_f.write(data)
                
                logger.info(f"Extracted {archive_path} -> {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"Error extracting {archive_path}: {e}")
            return False
    
    def extract_all(self, output_dir: str) -> bool:
        """Extract all files from the archive"""
        success_count = 0
        total_count = len(self.entries)
        
        for archive_path in self.entries:
            output_path = os.path.join(output_dir, archive_path)
            if self.extract_file(archive_path, output_path):
                success_count += 1
        
        logger.info(f"Extracted {success_count}/{total_count} files")
        return success_count == total_count
    
    def list_entries(self) -> List[str]:
        """Return list of all entry names"""
        return list(self.entries.keys())
    
    def get_entry_info(self, archive_path: str) -> Optional[Dict]:
        """Get information about a specific entry"""
        return self.entries.get(archive_path)

def main():
    parser = argparse.ArgumentParser(description='Pack/Unpack World of Xeen Amiga assets')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Pack command
    pack_parser = subparsers.add_parser('pack', help='Pack assets into archive')
    pack_parser.add_argument('--root', '-r', required=True, help='Root directory containing assets')
    pack_parser.add_argument('--output', '-o', required=True, help='Output archive file')
    pack_parser.add_argument('--prefix', help='Prefix for archive paths')
    pack_parser.add_argument('--manifest', help='Output manifest file')
    pack_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # Unpack command
    unpack_parser = subparsers.add_parser('unpack', help='Unpack assets from archive')
    unpack_parser.add_argument('--input', '-i', required=True, help='Input archive file')
    unpack_parser.add_argument('--output', '-o', required=True, help='Output directory')
    unpack_parser.add_argument('--entry', help='Extract specific entry only')
    unpack_parser.add_argument('--list', action='store_true', help='List archive contents')
    unpack_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.command == 'pack':
        # Pack assets
        packer = XeenAssetPack()
        
        if not os.path.exists(args.root):
            logger.error(f"Root directory not found: {args.root}")
            return 1
        
        # Add directory
        if not packer.add_directory(args.root, args.prefix):
            logger.warning("Some files failed to be added")
        
        # Write archive
        if not packer.write_archive(args.output):
            return 1
        
        # Save manifest if requested
        if args.manifest:
            packer.save_manifest(args.manifest)
        
        logger.info(f"Asset packing complete: {args.output}")
        return 0
    
    elif args.command == 'unpack':
        # Unpack assets
        if not os.path.exists(args.input):
            logger.error(f"Input file not found: {args.input}")
            return 1
        
        unpacker = XeenAssetUnpack(args.input)
        
        if not unpacker.read_header():
            return 1
        
        # List entries if requested
        if args.list:
            print(f"XPA Archive: {args.input}")
            print(f"Entries: {len(unpacker.entries)}")
            print()
            for name in sorted(unpacker.entries.keys()):
                entry = unpacker.entries[name]
                print(f"{name:<30} {entry['size']} bytes (CRC32: {entry['crc32']:08x})")
            return 0
        
        # Create output directory
        os.makedirs(args.output, exist_ok=True)
        
        # Extract files
        if args.entry:
            # Extract specific entry
            if args.entry not in unpacker.entries:
                logger.error(f"Entry not found: {args.entry}")
                return 1
            
            output_path = os.path.join(args.output, args.entry)
            if not unpacker.extract_file(args.entry, output_path):
                return 1
        else:
            # Extract all files
            if not unpacker.extract_all(args.output):
                logger.warning("Some files failed to extract")
        
        logger.info(f"Asset unpacking complete: {args.output}")
        return 0
    
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    exit(main())

#!/usr/bin/env python3
"""
World of Xeen CC Archive Unpacker

Extracts files from World of Xeen CC archives based on the actual format
used by the game (as implemented in ScummVM).
"""

import argparse
import json
import os
import struct
import sys
import zlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional

def decrypt_index(data: bytes) -> bytes:
    """
    Decrypt the CC archive index using the same algorithm as ScummVM.
    
    Args:
        data: Encrypted index data
        
    Returns:
        Decrypted index data
    """
    result = bytearray(len(data))
    seed = 0xac
    
    for i in range(len(data)):
        # Decrypt algorithm from ScummVM
        result[i] = (((data[i] << 2) | (data[i] >> 6)) + seed) & 0xff
        seed += 0x67
        
    return bytes(result)

def convert_name_to_id(filename: str) -> int:
    """
    Convert a filename to a 16-bit ID using the same algorithm as ScummVM.
    
    Args:
        filename: The filename to convert
        
    Returns:
        16-bit ID for the filename
    """
    name = filename.upper()
    
    # Check if it's a direct hex number
    if len(name) == 4:
        try:
            return int(name, 16)
        except ValueError:
            pass
    
    # Hash algorithm from ScummVM
    total = ord(name[0])
    for c in name[1:]:
        total += ord(c)
        # Rotate the bits in 'total' right 7 places
        total = (total & 0x007F) << 9 | (total & 0xFF80) >> 7
        
    return total & 0xFFFF

def parse_cc_archive(filepath: str) -> Tuple[List[Dict], bytes]:
    """
    Parse a CC archive file.
    
    Args:
        filepath: Path to the CC archive file
        
    Returns:
        Tuple of (entries list, file data)
    """
    with open(filepath, 'rb') as f:
        # Read count (2 bytes, little-endian)
        count = struct.unpack('<H', f.read(2))[0]
        
        # Read encrypted index data (count * 8 bytes)
        encrypted_index = f.read(count * 8)
        if len(encrypted_index) != count * 8:
            raise ValueError(f"Failed to read index data: expected {count * 8} bytes, got {len(encrypted_index)}")
        
        # Decrypt the index
        decrypted_index = decrypt_index(encrypted_index)
        
        # Parse entries
        entries = []
        for i in range(count):
            offset = i * 8
            entry_data = decrypted_index[offset:offset + 8]
            
            # Parse entry: ID (2 bytes) + offset (3 bytes) + size (2 bytes) + padding (1 byte)
            entry_id = struct.unpack('<H', entry_data[0:2])[0]
            entry_offset = struct.unpack('<I', entry_data[2:5] + b'\x00')[0] & 0xFFFFFF  # 3-byte offset
            entry_size = struct.unpack('<H', entry_data[5:7])[0]
            
            # Verify padding byte is zero
            if entry_data[7] != 0:
                print(f"Warning: Non-zero padding byte in entry {i}: {entry_data[7]}")
            
            entries.append({
                'id': entry_id,
                'offset': entry_offset,
                'size': entry_size,
                'index': i
            })
        
        # Read the rest of the file (file data)
        file_data = f.read()
        
        return entries, file_data

def extract_file(file_data: bytes, entry: Dict, output_dir: Path,
                filename_map: Optional[Dict[int, str]] = None,
                xor_decode: bool = True) -> str:
    """
    Extract a single file from the archive.
    
    Args:
        file_data: Raw file data from the archive
        entry: Entry dictionary with id, offset, size
        output_dir: Directory to extract to
        filename_map: Optional mapping of IDs to filenames
        
    Returns:
        Path to the extracted file
    """
    # Determine filename
    if filename_map and entry['id'] in filename_map:
        filename = filename_map[entry['id']]
    else:
        # Use ID as filename with .bin extension
        filename = f"{entry['id']:04X}.bin"
    
    # Extract data
    start = entry['offset']
    end = start + entry['size']
    
    if start >= len(file_data):
        raise ValueError(f"Entry offset {start} beyond file data size {len(file_data)}")
    if end > len(file_data):
        raise ValueError(f"Entry end {end} beyond file data size {len(file_data)}")
    
    data = file_data[start:end]

    # Xeen CC members are typically XOR-encoded with 0x35
    if xor_decode and data:
        data = bytes(b ^ 0x35 for b in data)
    
    # Write file
    output_path = output_dir / filename
    with open(output_path, 'wb') as f:
        f.write(data)
    
    return str(output_path)

def main():
    parser = argparse.ArgumentParser(description='Extract files from World of Xeen CC archives')
    parser.add_argument('--input', '-i', required=True, help='Input CC archive file')
    parser.add_argument('--output', '-o', required=True, help='Output directory')
    parser.add_argument('--index', help='Save index to JSON file')
    parser.add_argument('--list', action='store_true', help='List contents without extracting')
    parser.add_argument('--file', help='Extract specific file by ID (hex)')
    parser.add_argument('--filename-map', help='JSON file mapping IDs to filenames')
    parser.add_argument('--no-xor', action='store_true', help='Do not XOR-decode member payloads (default decodes)')
    parser.add_argument('--generate-mappings', action='store_true', 
                       help='Generate filename mappings automatically')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' not found")
        return 1
    
    try:
        # Parse the archive
        print(f"Parsing CC archive: {input_path}")
        entries, file_data = parse_cc_archive(str(input_path))
        
        print(f"Found {len(entries)} entries")
        
        # Load or generate filename mapping
        filename_map = None
        
        # First try to load the combined mappings from the extracted wiki data
        combined_mappings_path = Path(__file__).parent / "combined_mappings.json"
        if combined_mappings_path.exists():
            try:
                with open(combined_mappings_path, 'r') as f:
                    filename_map = {int(k, 16): v for k, v in json.load(f).items()}
                print(f"Loaded {len(filename_map)} filename mappings from combined_mappings.json")
            except Exception as e:
                print(f"Warning: Could not load combined mappings: {e}")
        
        # If no combined mappings, try specific archive mappings based on input filename
        if not filename_map:
            archive_name = input_path.stem.upper()  # Get filename without extension
            if archive_name in ['DARK', 'XEEN', 'INTRO']:
                specific_mappings_path = Path(__file__).parent / f"{archive_name.lower()}_cc_mappings.json"
                if specific_mappings_path.exists():
                    try:
                        with open(specific_mappings_path, 'r') as f:
                            filename_map = {int(k, 16): v for k, v in json.load(f).items()}
                        print(f"Loaded {len(filename_map)} filename mappings from {specific_mappings_path.name}")
                    except Exception as e:
                        print(f"Warning: Could not load {specific_mappings_path.name}: {e}")
        
        # Fallback to generate mappings if requested
        if not filename_map and args.generate_mappings:
            # Import and use the filename mapper
            try:
                import sys
                import os
                # Add current directory to path to ensure we can import the mapper
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                from xeen_filename_mapper import generate_all_mappings
                filename_map = generate_all_mappings()
                print(f"Generated {len(filename_map)} filename mappings")
            except ImportError as e:
                print(f"Warning: Could not import filename mapper: {e}")
                print("Using ID-based names instead")
        
        # Manual filename map override
        if args.filename_map:
            with open(args.filename_map, 'r') as f:
                filename_map = {int(k, 16): v for k, v in json.load(f).items()}
                print(f"Loaded {len(filename_map)} filename mappings from manual file")
        
        # Save index if requested
        if args.index:
            index_data = {
                'archive': str(input_path),
                'entry_count': len(entries),
                'file_size': len(file_data),
                'entries': entries
            }
            with open(args.index, 'w') as f:
                json.dump(index_data, f, indent=2)
            print(f"Index saved to: {args.index}")
        
        # List contents if requested
        if args.list:
            print("\nArchive contents:")
            print(f"{'ID':>4} {'Offset':>8} {'Size':>8} {'Filename':<20}")
            print("-" * 50)
            for entry in entries:
                if filename_map and entry['id'] in filename_map:
                    filename = filename_map[entry['id']]
                else:
                    filename = f"{entry['id']:04X}.bin"
                print(f"{entry['id']:04X} {entry['offset']:8} {entry['size']:8} {filename}")
            return 0
        
        # Extract specific file if requested
        if args.file:
            try:
                file_id = int(args.file, 16)
                matching_entries = [e for e in entries if e['id'] == file_id]
                if not matching_entries:
                    print(f"Error: No file found with ID {file_id:04X}")
                    return 1
                
                entry = matching_entries[0]
                output_dir.mkdir(parents=True, exist_ok=True)
                extracted_path = extract_file(file_data, entry, output_dir, filename_map, xor_decode=not args.no_xor)
                print(f"Extracted: {extracted_path}")
                return 0
            except ValueError:
                print(f"Error: Invalid file ID '{args.file}' (must be hex)")
                return 1
        
        # Extract all files
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Extracting to: {output_dir}")
        extracted_count = 0
        
        for entry in entries:
            try:
                extracted_path = extract_file(file_data, entry, output_dir, filename_map, xor_decode=not args.no_xor)
                print(f"Extracted: {extracted_path}")
                extracted_count += 1
            except Exception as e:
                print(f"Error extracting entry {entry['id']:04X}: {e}")
        

        
        print(f"\nExtraction complete: {extracted_count} files extracted")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())

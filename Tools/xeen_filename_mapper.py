#!/usr/bin/env python3
"""
World of Xeen Filename Mapper

Generates filename mappings for CC archive IDs based on known patterns
from the ScummVM codebase.
"""

import json
import struct
from pathlib import Path
from typing import Dict, List, Set

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

def generate_maze_filename_mappings() -> Dict[int, str]:
    """Generate filename mappings for maze files"""
    mappings = {}
    
    # Maze data files: maze{0/x}{###}.dat
    for map_id in range(1, 200):  # Reasonable range for map IDs
        prefix = 'x' if map_id >= 100 else '0'
        filename = f"maze{prefix}{map_id:03d}.dat"
        mappings[convert_name_to_id(filename)] = filename
    
    # Maze monster/object files: maze{0/x}{###}.mob
    for map_id in range(1, 200):
        prefix = 'x' if map_id >= 100 else '0'
        filename = f"maze{prefix}{map_id:03d}.mob"
        mappings[convert_name_to_id(filename)] = filename
    
    # Maze header files: aaze{0/x}{###}.hed
    for map_id in range(1, 200):
        prefix = 'x' if map_id >= 100 else '0'
        filename = f"aaze{prefix}{map_id:03d}.hed"
        mappings[convert_name_to_id(filename)] = filename
    
    # Maze text files: aaze{0/x}{###}.txt
    for map_id in range(1, 200):
        prefix = 'x' if map_id >= 100 else '0'
        filename = f"aaze{prefix}{map_id:03d}.txt"
        mappings[convert_name_to_id(filename)] = filename
    
    # Maze event files: maze{0/x}{###}.evt
    for map_id in range(1, 200):
        prefix = 'x' if map_id >= 100 else '0'
        filename = f"maze{prefix}{map_id:03d}.evt"
        mappings[convert_name_to_id(filename)] = filename
    
    return mappings

def generate_sprite_filename_mappings() -> Dict[int, str]:
    """Generate filename mappings for sprite files"""
    mappings = {}
    
    # Monster sprites: {###}.mon
    for sprite_id in range(1, 1000):
        filename = f"{sprite_id:03d}.mon"
        mappings[convert_name_to_id(filename)] = filename
    
    # Attack sprites: {###}.att
    for sprite_id in range(1, 1000):
        filename = f"{sprite_id:03d}.att"
        mappings[convert_name_to_id(filename)] = filename
    
    # Object sprites: {###}.obj (for < 100) and {###}.obj (for >= 100)
    for sprite_id in range(1, 1000):
        if sprite_id >= 100:
            filename = f"{sprite_id:03d}.obj"
        else:
            filename = f"{sprite_id:03d}.obj"
        mappings[convert_name_to_id(filename)] = filename
    
    # Picture sprites: {###}.pic
    for sprite_id in range(1, 1000):
        filename = f"{sprite_id:03d}.pic"
        mappings[convert_name_to_id(filename)] = filename
    
    return mappings

def generate_data_filename_mappings() -> Dict[int, str]:
    """Generate filename mappings for data files"""
    mappings = {}
    
    # Known data files from ScummVM code
    known_files = [
        "dark.dat",
        "animinfo.cld", 
        "monsters.cld",
        "wallpics.cld",
        "xeen.mon",
        "dark.mon",
        "xeenpic.dat",
        "darkpic.dat",
        "monsters.swd"
    ]
    
    for filename in known_files:
        mappings[convert_name_to_id(filename)] = filename
    
    return mappings

def generate_palette_filename_mappings() -> Dict[int, str]:
    """Generate filename mappings for palette files"""
    mappings = {}
    
    # Common palette file patterns
    for i in range(1, 100):
        filename = f"palette{i:02d}.pal"
        mappings[convert_name_to_id(filename)] = filename
    
    # Some games use numbered palettes
    for i in range(1, 50):
        filename = f"{i:03d}.pal"
        mappings[convert_name_to_id(filename)] = filename
    
    return mappings

def generate_background_filename_mappings() -> Dict[int, str]:
    """Generate filename mappings for background files"""
    mappings = {}
    
    # Common background file patterns
    for i in range(1, 100):
        filename = f"background{i:02d}.raw"
        mappings[convert_name_to_id(filename)] = filename
    
    # Some games use numbered backgrounds
    for i in range(1, 50):
        filename = f"{i:03d}.raw"
        mappings[convert_name_to_id(filename)] = filename
    
    return mappings

def generate_known_filename_mappings() -> Dict[int, str]:
    """Generate filename mappings based on known files from Xeen Wiki"""
    mappings = {}
    
    # DARK.CC files from https://xeen.fandom.com/wiki/Filenames
    dark_cc_files = {
        0x2A0C: "OUT0.SPL",
        0x2A1C: "OUT1.SPL", 
        0x2A2C: "OUT2.SPL",
        0x2A3C: "OUT3.SPL",
        0x284C: "OUT4.SPL",
        0x2A5C: "OUT5.SPL",
        0x64B2: "SPELLS.XEN",
        0x3348: "MAE.XEN",
        0x0D75: "TITLE2.INT",
        0x078A: "TITLE2A.INT",
        0x079A: "TITLE2B.INT",
        0x07AA: "TITLE2C.INT",
        0x07BA: "TITLE2D.INT",
        0x07CA: "TITLE2E.INT",
        0x07DA: "TITLE2F.INT",
        0x07EA: "TITLE2G.INT",
        0x07FA: "TITLE2H.INT",
        0x080A: "TITLE2I.INT",
        0xEDC0: "TITLE2B.RAW",
        0xCF93: "KLUDGE.INT",
        0x6392: "WORLD.RAW",
        0xF359: "WORLD0.INT",
        0xF369: "WORLD1.INT",
        0xF379: "WORLD2.INT",
        0x9D6C: "FNT",
        0x5E82: "XEENMIRR.TXT",
        0x4AFC: "DARKMIRR.TXT",
        0x966F: "XEEN0006.TXT",
        0x961F: "XEEN0001.TXT",
        0x962F: "XEEN0002.TXT",
        0x963F: "XEEN0003.TXT",
        0x964F: "XEEN0004.TXT",
        0x965F: "XEEN0005.TXT",
        0x967F: "XEEN0007.TXT",
        0x968F: "XEEN0008.TXT",
        0x969F: "XEEN0009.TXT",
        0xB60F: "XEEN0010.TXT",
        0x3582: "SCF28.END",
        0x35C2: "SCG28.END",
        0x3602: "SCH28.END",
        0x3642: "SCI28.END",
        0x3682: "SCJ28.END",
        0x36C2: "SCK28.END",
        0x1113: "SC29A.END",
        0x1123: "SC29B.END",
        0x1133: "SC29C.END",
        0x1143: "SC29D.END",
        0x1153: "SC29E.END",
        0x1163: "SC29F.END",
        0xBDB5: "MAINBACK.RAW",
        0x46C8: "SC050001.RAW",
        0x48C8: "SC070001.RAW",
        0x4AC8: "SC090001.RAW",
        0x48CA: "SC170001.RAW",
        0x49CA: "SC180001.RAW",
        0x4ACA: "SC190001.RAW",
        0x44CC: "SC230001.RAW",
        0x46CC: "SC250001.RAW",
        0x47CC: "SC260001.RAW",
        0x48CC: "SC270001.RAW",
        0x6E02: "SCENE1.RAW",
        0x818C: "SCENE2-B.RAW",
        0x6E32: "SCENE4.RAW",
        0x80FC: "SCENE4-1.RAW",
        0x0AC1: "BLANK.RAW",
        0x4ACC: "SC290001.RAW",
        0xB9B5: "SCENE12.RAW",
        0x4C23: "SPECIAL.BIN",
        0xF5A4: "BOX.VGA",
        0x5BCD: "DREAMS2.VOC",
        0xD2B5: "CORAK2.VOC",
        0x0424: "YES1.VOC",
        0x96FD: "NOWRE1.VOC",
        0x538C: "NORDO2.VOC",
        0x098D: "READY2.VOC",
        0x6E77: "FIGHT2.VOC",
        0x6B17: "FAIL1.VOC",
        0x69B0: "ADMIT2.VOC",
        0x83EB: "IDO2.VOC",
        0xFA3B: "WHAT3.VOC",
        0x4E75: "SKYMAIN.PAL",
        0x50BD: "WHOOSH.VOC",
        0xC9BB: "CLICK.VOC",
        0x7847: "EXPLOSIO.VOC",
        0xF545: "WINDSTOR.VOC",
        0xF20D: "GASCOMPR.VOC",
        0x0549: "CAST.VOC",
        0xFFD7: "PADSPELL.VOC",
        0x7A41: "RUMBLE.VOC",
        0xC790: "CRASH.VOC",
        0xFC15: "TABLMAIN.RAW",
        0x1323: "FOURA.RAW",
        0x5649: "EG250001.PAL",
        0x515A: "EG100001.RAW",
        0x555A: "EG140001.RAW",
        0x565C: "EG250001.RAW",
        0x585C: "EG270001.RAW",
        0xDD00: "EG23PRT2.RAW",
        0x4E88: "SKYMAIN.RAW",
        0x4C55: "TWRSKY1.RAW",
        0x08A9: "DOOR.VOC",
        0xD901: "CUBE.EG2",
        0x6021: "HANDS.EG2",
        0x9357: "SC02.EG2",
        0x9397: "SC06.EG2",
        0xB337: "SC10.EG2",
        0xB367: "SC13.EG2",
        0xB377: "SC14.EG2",
        0xB3A7: "SC17.EG2",
        0xE2FF: "SC20A.EG2",
        0xE30F: "SC20B.EG2",
        0xE31F: "SC20C.EG2",
        0xE32F: "SC20D.EG2",
        0x2300: "SC22A.EG2",
        0x2310: "SC22B.EG2",
        0x4300: "SC23A.EG2",
        0x4310: "SC23B.EG2",
        0x4320: "SC23C.EG2",
        0x4330: "SC23D.EG2",
        0x4340: "SC23E.EG2",
        0x4350: "SC23F.EG2",
        0x4360: "SC23G.EG2",
        0x4370: "SC23H.EG2",
        0xD377: "SC24.EG2",
        0xF447: "SC3A.EG2",
        0x2242: "SC3B1.EG2",
        0x2252: "SC3B2.EG2",
        0x271B: "STAFF.EG2",
        0x2376: "TOWER1.EG2",
        0x2386: "TOWER2.EG2",
        0xD387: "SC25.EG2",
        0x749D: "SC261A.EG2",
        0x74AD: "SC261B.EG2",
        0xA210: "SC262.EG2",
        0xA220: "SC263.EG2",
        0xA230: "SC264.EG2",
        0xD3A7: "SC27.EG2"
    }
    
    # Load extracted mappings from the wiki HTML
    dark_cc_files = load_manual_mappings("dark_cc_mappings.json")
    xeen_cc_files = load_manual_mappings("xeen_cc_mappings.json")
    intro_cc_files = load_manual_mappings("intro_cc_mappings.json")
    
    mappings.update(dark_cc_files)
    mappings.update(xeen_cc_files)
    mappings.update(intro_cc_files)
    
    return mappings

def generate_all_mappings() -> Dict[int, str]:
    """Generate all filename mappings"""
    mappings = {}
    
    # Start with known filenames from the wiki (these take priority)
    mappings.update(generate_known_filename_mappings())
    
    # Add algorithmic mappings (these will only be used if not already mapped)
    mappings.update(generate_maze_filename_mappings())
    mappings.update(generate_sprite_filename_mappings())
    mappings.update(generate_data_filename_mappings())
    mappings.update(generate_palette_filename_mappings())
    mappings.update(generate_background_filename_mappings())
    
    return mappings

def load_manual_mappings(filepath: str) -> Dict[int, str]:
    """Load manual filename mappings from a JSON file"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            # Convert string keys to integers
            return {int(k, 16): v for k, v in data.items()}
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Warning: Could not load manual mappings from {filepath}: {e}")
        return {}

def save_mappings(mappings: Dict[int, str], filepath: str):
    """Save filename mappings to a JSON file"""
    # Convert integer keys to hex strings for better readability
    output_data = {f"{k:04X}": v for k, v in mappings.items()}
    
    with open(filepath, 'w') as f:
        json.dump(output_data, f, indent=2, sort_keys=True)

def analyze_cc_archive(filepath: str, mappings: Dict[int, str]) -> Dict[str, List[int]]:
    """Analyze a CC archive and show which IDs have known filenames"""
    from xeencc_unpack import parse_cc_archive
    
    try:
        entries, _ = parse_cc_archive(filepath)
        
        # Categorize entries
        categorized = {
            'known': [],
            'unknown': []
        }
        
        for entry in entries:
            entry_id = entry['id']
            if entry_id in mappings:
                categorized['known'].append(entry_id)
            else:
                categorized['unknown'].append(entry_id)
        
        return categorized
        
    except Exception as e:
        print(f"Error analyzing CC archive: {e}")
        return {'known': [], 'unknown': []}

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate filename mappings for World of Xeen CC archives')
    parser.add_argument('--output', '-o', default='filename_mappings.json', 
                       help='Output JSON file for mappings')
    parser.add_argument('--manual', '-m', help='Manual mappings JSON file to merge')
    parser.add_argument('--analyze', '-a', help='Analyze a CC archive file')
    parser.add_argument('--list-unknown', action='store_true', 
                       help='List unknown IDs when analyzing')
    
    args = parser.parse_args()
    
    # Generate mappings
    print("Generating filename mappings...")
    mappings = generate_all_mappings()
    
    # Load manual mappings if provided
    if args.manual:
        print(f"Loading manual mappings from {args.manual}...")
        manual_mappings = load_manual_mappings(args.manual)
        mappings.update(manual_mappings)
        print(f"Added {len(manual_mappings)} manual mappings")
    
    # Save mappings
    print(f"Saving {len(mappings)} mappings to {args.output}...")
    save_mappings(mappings, args.output)
    
    # Analyze CC archive if provided
    if args.analyze:
        print(f"\nAnalyzing CC archive: {args.analyze}")
        categorized = analyze_cc_archive(args.analyze, mappings)
        
        print(f"Known files: {len(categorized['known'])}")
        print(f"Unknown files: {len(categorized['unknown'])}")
        
        if categorized['known']:
            print("\nKnown files:")
            for entry_id in sorted(categorized['known']):
                filename = mappings[entry_id]
                print(f"  {entry_id:04X} -> {filename}")
        
        if args.list_unknown and categorized['unknown']:
            print("\nUnknown files:")
            for entry_id in sorted(categorized['unknown']):
                print(f"  {entry_id:04X}")
    
    print(f"\nMapping generation complete. Total mappings: {len(mappings)}")

if __name__ == '__main__':
    main()

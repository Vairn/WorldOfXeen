# World of Xeen Asset Conversion Tools

This directory contains tools for converting original World of Xeen assets into Amiga-friendly formats.

## Overview

The tools follow a workflow to extract, convert, and repack game assets:

1. **Extract** CC archives from original game data
2. **Convert** assets to Amiga-optimized formats (bitplanes, palettes, etc.)
3. **Pack** converted assets into a simple archive format
4. **Verify** asset integrity and completeness

## Tool Chain

### Core Tools

- `xeencc_unpack.py` - Extract and index CC archives
- `xeen_pal_convert.py` - Convert palettes to Amiga format
- `xeen_bg_convert.py` - Convert backgrounds to bitplanes
- `xeen_spr_convert.py` - Convert sprites to Amiga format
- `xeen_pack_assets.py` - Create Amiga asset archive
- `xeen_verify_assets.py` - Verify asset integrity

### Utility Tools

- `xeen_analyze_cc.py` - Analyze CC archive structure
- `xeen_extract_specific.py` - Extract specific files from CC archives
- `xeen_convert_batch.py` - Batch conversion script

## Usage

### Prerequisites

```bash
pip install pillow numpy structlog
```

### Basic Workflow

```bash
# 1. Extract CC archives
python Tools/xeencc_unpack.py --input path/to/XEEN.CC --output extracted/

# 2. Convert palettes
python Tools/xeen_pal_convert.py --input extracted/mm4.pal --aga --output converted/pal/mm4_aga.pal

# 3. Convert backgrounds
python Tools/xeen_bg_convert.py --input extracted/back.raw --output converted/bg/back.bpl

# 4. Convert sprites
python Tools/xeen_spr_convert.py --input extracted/sprites/ --output converted/spr/

# 5. Pack all assets
python Tools/xeen_pack_assets.py --root converted/ --output amiga_assets.xpa

# 6. Verify
python Tools/xeen_verify_assets.py --archive amiga_assets.xpa
```

### Batch Processing

```bash
python Tools/xeen_convert_batch.py --input path/to/game/data --output converted/
```

## Asset Formats

### Input Formats
- **CC Archives**: Original game data archives
- **Palettes**: 256-color RGB palettes (.pal)
- **Backgrounds**: Raw 320x200 pixel data (.raw)
- **Sprites**: Original sprite resources

### Output Formats
- **XPA Archive**: Simple indexable archive with CRC32 verification
- **AGA Palettes**: 256-color Amiga palette format
- **Bitplane Graphics**: 8-bitplane aligned for Amiga blitter
- **RLE Sprites**: Run-length encoded sprite data

## Legal Notice

These tools are provided for educational and preservation purposes. Users must provide their own legally obtained World of Xeen game data. No original game assets are included in this repository.

## Future: Native Amiga Tools

Long-term goal is to port these tools to run natively on Amiga hardware using ACE engine, but host-side tools provide faster iteration during development.

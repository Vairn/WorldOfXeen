#!/usr/bin/env python3
"""
World of Xeen Sprite Converter

Decodes Xeen sprite resources (e.g., PIC/ICN/FAC/EG2 containers) and:
- Exports per-frame PNG previews (indexed color, optional palette)
- Optionally exports per-frame raw 8-bit chunky buffers
- Optionally converts frames to Amiga bitplanes (raw/interleaved/RLE)

Based on the sprite decoding logic from ScummVM's Xeen engine.
"""

import argparse
import os
import struct
import logging
from pathlib import Path
from typing import List, Tuple, Optional

try:
    import numpy as np
except Exception:
    np = None


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Pattern steps used by opcode 6/7 (pattern command)
PATTERN_STEPS = [
    0, 1, 1, 1, 2, 2, 3, 3,
    0, -1, -1, -1, -2, -2, -3, -3,
]


class ByteStream:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def seek(self, offset: int, whence: int = os.SEEK_SET):
        if whence == os.SEEK_SET:
            self.pos = offset
        elif whence == os.SEEK_CUR:
            self.pos += offset
        elif whence == os.SEEK_END:
            self.pos = len(self.data) + offset
        else:
            raise ValueError("Invalid whence")

        if self.pos < 0 or self.pos > len(self.data):
            raise ValueError("Seek out of bounds")

    def tell(self) -> int:
        return self.pos

    def read(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise EOFError("Read out of bounds")
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b

    def read_u8(self) -> int:
        return self.read(1)[0]

    def read_u16le(self) -> int:
        return struct.unpack('<H', self.read(2))[0]


class SpriteFrame:
    def __init__(self, width: int, height: int, x_offset: int, y_offset: int):
        self.width = width
        self.height = height
        self.x_offset = x_offset
        self.y_offset = y_offset
        # Pixel buffer as 2D list (height x width), initialized to transparent (-1)
        self.pixels: List[List[int]] = [[-1] * width for _ in range(height)]


class SpriteResource:
    def __init__(self, data: bytes):
        self.data = data
        self.index: List[Tuple[int, int]] = []  # (offset1, offset2)

    @staticmethod
    def try_xor35(data: bytes) -> Optional[bytes]:
        # Light heuristic: if initial count looks insane, try XOR 0x35 and re-check
        if len(data) < 2:
            return None
        count = struct.unpack('<H', data[:2])[0]
        if 0 < count < 0x0800:  # plausible count
            return None
        return bytes(b ^ 0x35 for b in data)

    @classmethod
    def load_from_file(cls, path: str) -> 'SpriteResource':
        with open(path, 'rb') as f:
            raw = f.read()

        # Allow for possible XOR-encoded entries (some CC members are encoded)
        try:
            stream = ByteStream(raw)
            count = stream.read_u16le()
            # Sanity: header size must fit in file
            if 4 * count + 2 > len(raw):
                maybe = cls.try_xor35(raw)
                if maybe is not None:
                    raw = maybe
        except Exception:
            maybe = cls.try_xor35(raw)
            if maybe is not None:
                raw = maybe

        res = cls(raw)
        res._parse_index()
        return res

    def _parse_index(self):
        s = ByteStream(self.data)
        count = s.read_u16le()
        self.index = []
        # Each entry: offset1 (u16), offset2 (u16)
        for _ in range(count):
            offset1 = s.read_u16le()
            offset2 = s.read_u16le()
            self.index.append((offset1, offset2))

    def get_frame_bounds(self, frame_idx: int) -> Tuple[int, int]:
        """Compute width/height of the composed frame across its 1 or 2 cells."""
        s = ByteStream(self.data)
        w_max = 0
        h_max = 0
        for which in (0, 1):
            off = self.index[frame_idx][which]
            if off == 0:
                continue
            s.seek(off)
            x_off = s.read_u16le()
            width = s.read_u16le()
            y_off = s.read_u16le()
            height = s.read_u16le()
            w_max = max(w_max, x_off + width)
            h_max = max(h_max, y_off + height)
        if w_max == 0 or h_max == 0:
            # Fallback, avoid zero-sized surfaces
            w_max = max(1, w_max)
            h_max = max(1, h_max)
        return w_max, h_max

    def decode_cell_into(self, frame: SpriteFrame, cell_offset: int):
        s = ByteStream(self.data)
        s.seek(cell_offset)
        x_off = s.read_u16le()
        width = s.read_u16le()
        y_off = s.read_u16le()
        height = s.read_u16le()

        # Draw scanlines
        dest_y = y_off
        remaining = height
        while remaining > 0:
            line_length = s.read_u8()
            if line_length == 0:
                # Skip lines
                num_lines = s.read_u8()
                dest_y += (num_lines + 1)
                remaining -= (num_lines + 1)
                continue

            # Per-line x offset
            x_offset_line = s.read_u8()
            # Build a temporary line buffer (initialized to transparent)
            line = [-1] * width
            x = x_offset_line
            bytes_consumed = 1  # we already consumed x_offset_line within line_length

            while bytes_consumed < line_length:
                opcode = s.read_u8()
                bytes_consumed += 1
                length_low5 = opcode & 0x1F
                cmd = (opcode & 0xE0) >> 5

                if cmd == 0 or cmd == 1:
                    # The code in ScummVM uses (opcode + 1) as the count for both cases
                    count = opcode + 1
                    for _ in range(count):
                        if bytes_consumed >= line_length:
                            break
                        b = s.read_u8()
                        bytes_consumed += 1
                        if 0 <= x < width:
                            line[x] = b
                        x += 1

                elif cmd == 2:
                    # RLE: draw value (len + 3) times
                    val = s.read_u8()
                    bytes_consumed += 1
                    count = length_low5 + 3
                    for _ in range(count):
                        if 0 <= x < width:
                            line[x] = val
                        x += 1

                elif cmd == 3:
                    # Stream copy: copy from earlier in stream
                    back = s.read_u16le()
                    bytes_consumed += 2
                    pos = s.tell()
                    s.seek(-back, os.SEEK_CUR)
                    for _ in range(length_low5 + 4):
                        b = s.read_u8()
                        if 0 <= x < width:
                            line[x] = b
                        x += 1
                    s.seek(pos, os.SEEK_SET)

                elif cmd == 4:
                    # Two-byte pair repeated len + 2 times
                    a = s.read_u8()
                    b = s.read_u8()
                    bytes_consumed += 2
                    for _ in range(length_low5 + 2):
                        if 0 <= x < width:
                            line[x] = a
                        x += 1
                        if 0 <= x < width:
                            line[x] = b
                        x += 1

                elif cmd == 5:
                    # Skip len + 1 pixels
                    x += (length_low5 + 1)

                else:  # cmd 6 or 7: pattern
                    # Special encoding
                    patt_len = opcode & 0x07
                    patt_cmd = (opcode >> 2) & 0x0E
                    val = s.read_u8()
                    bytes_consumed += 1
                    for i in range(patt_len + 3):
                        if 0 <= x < width:
                            line[x] = val
                        x += 1
                        step = PATTERN_STEPS[patt_cmd + (i % 2)]
                        val = (val + step) & 0xFF

            # Blit line into frame if within bounds
            if 0 <= dest_y < frame.height:
                row = frame.pixels[dest_y]
                for i in range(width):
                    c = line[i]
                    if c != -1:
                        dst_x = x_off + i
                        if 0 <= dst_x < frame.width:
                            row[dst_x] = c
            dest_y += 1
            remaining -= 1

    def decode_frame(self, frame_idx: int) -> SpriteFrame:
        w, h = self.get_frame_bounds(frame_idx)
        # We position sub-cells at their own (x,y) offsets inside this canvas; x_offset here is 0 for canvas
        frame = SpriteFrame(w, h, 0, 0)
        offset1, offset2 = self.index[frame_idx]
        if offset1:
            self.decode_cell_into(frame, offset1)
        if offset2:
            self.decode_cell_into(frame, offset2)
        return frame


def save_png_preview(frame: SpriteFrame, out_path: str, palette_file: Optional[str]):
    try:
        from PIL import Image
    except Exception:
        logger.warning("PIL not available; skipping PNG preview")
        return False

    img = Image.new('P', (frame.width, frame.height))
    # Convert -1 (transparent) to 0; others keep as-is
    flat = []
    for y in range(frame.height):
        row = frame.pixels[y]
        for x in range(frame.width):
            v = row[x]
            flat.append(0 if v < 0 else v & 0xFF)
    img.putdata(flat)

    if palette_file and os.path.exists(palette_file):
        with open(palette_file, 'rb') as f:
            pal_data = f.read(256 * 3)
        pal = []
        for i in range(256):
            if i * 3 + 3 <= len(pal_data):
                r, g, b = pal_data[i * 3:(i + 1) * 3]
            else:
                r = g = b = 0
            # Xeen palettes are 6-bit values that need to be left-shifted by 2
            # This matches the C++ code: f.readByte() << 2
            pal.extend([min(255, r << 2), min(255, g << 2), min(255, b << 2)])
        img.putpalette(pal)
    else:
        # grayscale palette fallback
        pal = []
        for i in range(256):
            pal.extend([i, i, i])
        img.putpalette(pal)

    img.save(out_path)
    return True


def chunky_to_bitplanes(pixels: List[List[int]], num_planes: int) -> List[bytes]:
    h = len(pixels)
    w = len(pixels[0]) if h > 0 else 0
    # Width padded to multiple of 8
    padded_w = (w + 7) & ~7
    # Initialize planes
    planes = [bytearray((padded_w // 8) * h) for _ in range(num_planes)]

    for y in range(h):
        xbyte = 0
        bitpos = 0
        # Build bytes per row
        for x in range(padded_w):
            val = pixels[y][x] if x < w else 0
            for p in range(num_planes):
                bit = (val >> p) & 1
                if bit:
                    planes[p][(y * (padded_w // 8)) + (x // 8)] |= (1 << (x % 8))

    return [bytes(b) for b in planes]


def interleave_bitplanes(planes: List[bytes], width: int, height: int) -> bytes:
    if not planes:
        return b''
    bytes_per_row = ((width + 7) // 8)
    num_planes = len(planes)
    out = bytearray()
    for y in range(height):
        for p in range(num_planes):
            start = y * bytes_per_row
            end = start + bytes_per_row
            out.extend(planes[p][start:end])
    return bytes(out)


def rle_compress(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        # Count run
        run = 1
        while i + run < n and data[i] == data[i + run] and run < 255:
            run += 1
        if run >= 3:
            out.append(0x80 | run)
            out.append(data[i])
            i += run
        else:
            out.append(run)
            out.extend(data[i:i + run])
            i += run
    return bytes(out)


def process_file(input_path: str, out_dir: str, palette: Optional[str], export_chunky: bool,
                 bitplanes: Optional[int], interleaved: bool, rle: bool, max_frames: Optional[int]) -> bool:
    try:
        res = SpriteResource.load_from_file(input_path)
    except Exception as e:
        logger.error(f"{Path(input_path).name}: cannot parse sprite resource: {e}")
        return False

    base = Path(input_path).stem
    frame_count = len(res.index)
    if max_frames is not None:
        frame_count = min(frame_count, max_frames)

    os.makedirs(out_dir, exist_ok=True)
    ok = True

    for fi in range(frame_count):
        try:
            frame = res.decode_frame(fi)

            # PNG preview
            png_path = os.path.join(out_dir, f"{base}_frame_{fi:03d}.png")
            save_png_preview(frame, png_path, palette)

            # Optional chunky buffer export
            if export_chunky:
                raw_path = os.path.join(out_dir, f"{base}_frame_{fi:03d}.raw")
                with open(raw_path, 'wb') as f:
                    for y in range(frame.height):
                        for x in range(frame.width):
                            v = frame.pixels[y][x]
                            f.write(bytes([(0 if v < 0 else v & 0xFF)]))

            # Optional bitplanes
            if bitplanes and bitplanes > 0:
                planes = chunky_to_bitplanes(frame.pixels, bitplanes)
                if interleaved:
                    data = interleave_bitplanes(planes, frame.width, frame.height)
                    bp_path = os.path.join(out_dir, f"{base}_frame_{fi:03d}_ilv.bpl")
                    with open(bp_path, 'wb') as f:
                        f.write(struct.pack('<IIII', frame.width, frame.height, bitplanes, len(data)))
                        f.write(data)
                elif rle:
                    bp_path = os.path.join(out_dir, f"{base}_frame_{fi:03d}_rle.bpl")
                    with open(bp_path, 'wb') as f:
                        # header with size placeholder
                        f.write(struct.pack('<IIII', frame.width, frame.height, bitplanes, 0))
                        total = 0
                        for pdat in planes:
                            cd = rle_compress(pdat)
                            f.write(struct.pack('<I', len(cd)))
                            f.write(cd)
                            total += len(cd)
                        f.seek(12)
                        f.write(struct.pack('<I', total))
                else:
                    bp_path = os.path.join(out_dir, f"{base}_frame_{fi:03d}.bpl")
                    with open(bp_path, 'wb') as f:
                        f.write(struct.pack('<IIII', frame.width, frame.height, bitplanes, len(planes[0])))
                        for pdat in planes:
                            f.write(pdat)

        except Exception as e:
            logger.error(f"{Path(input_path).name} frame {fi}: {e}")
            ok = False

    return ok


def find_palette_near(input_path: str) -> Optional[str]:
    # Try common palette names in same directory
    dirname = os.path.dirname(input_path)
    candidates = [
        'mm4.pal', 'mm5.pal', 'dark.pal', 'cloud.pal', 'clouds.pal', 'mm4e.pal', 'pal.pal'
    ]
    for c in candidates:
        p = os.path.join(dirname, c)
        if os.path.exists(p):
            return p
    return None


def main():
    parser = argparse.ArgumentParser(description='Convert Xeen sprite resources and generate PNG previews')
    parser.add_argument('--input', '-i', required=True, help='Input file or directory')
    parser.add_argument('--output', '-o', required=True, help='Output directory')
    parser.add_argument('--palette', help='Optional 256xRGB palette file to apply to previews')
    parser.add_argument('--export-chunky', action='store_true', help='Also export per-frame raw 8-bit buffers')
    parser.add_argument('--bitplanes', type=int, choices=range(1, 9), help='Also export bitplanes with given plane count')
    parser.add_argument('--interleaved', action='store_true', help='When exporting bitplanes, save interleaved format')
    parser.add_argument('--rle', action='store_true', help='When exporting bitplanes, save RLE-compressed planes')
    parser.add_argument('--max-frames', type=int, help='Limit frames per resource for quick previews')
    parser.add_argument('--glob', nargs='*', help='Filter by extensions (e.g. .pic .icn .fac .eg2 .dat)')
    parser.add_argument('--verbose', '-v', action='store_true')

    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    inputs: List[str] = []
    if os.path.isdir(args.input):
        exts = None
        if args.glob:
            exts = {e.lower() if e.startswith('.') else f'.{e.lower()}' for e in args.glob}
        for root, _, files in os.walk(args.input):
            for f in files:
                if exts is None:
                    inputs.append(os.path.join(root, f))
                else:
                    if Path(f).suffix.lower() in exts:
                        inputs.append(os.path.join(root, f))
    else:
        inputs = [args.input]

    if not inputs:
        logger.error('No input files found')
        return 1

    os.makedirs(args.output, exist_ok=True)

    ok_all = True
    for ip in inputs:
        pal = args.palette or find_palette_near(ip)
        out_sub = os.path.join(args.output, Path(ip).stem)
        os.makedirs(out_sub, exist_ok=True)
        ok = process_file(
            ip,
            out_sub,
            pal,
            export_chunky=args.export_chunky,
            bitplanes=args.bitplanes,
            interleaved=args.interleaved,
            rle=args.rle,
            max_frames=args.max_frames,
        )
        ok_all &= ok

    return 0 if ok_all else 2


if __name__ == '__main__':
    raise SystemExit(main())



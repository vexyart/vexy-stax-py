#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["fire", "fonttools"]
# ///
# this_file: ftfonttrak.py

import fire
import math
from pathlib import Path
from fontTools.ttLib import TTFont


def trak_font(
    input_font: str,
    trak: float,
    output_font: str,
) -> None:
    """Adjust tracking (glyph widths) in a TTF font's hmtx table.

    Args:
        input_font: Path to the input .ttf font
        trak: Tracking value in permille of the em (1/1000ths of EM)
        output_font: Path to the output .ttf font
    """
    input_path = Path(input_font)
    output_path = Path(output_font)

    # Validate that files end with .ttf
    if input_path.suffix.lower() != ".ttf":
        raise ValueError(f"Input font must be a .ttf file, got: {input_font}")
    
    if output_path.suffix.lower() != ".ttf":
        raise ValueError(f"Output font must be a .ttf file, got: {output_font}")

    if not input_path.is_file():
        raise FileNotFoundError(f"Input font file not found: {input_font}")

    print(f"Loading font: {input_path}")
    font = TTFont(input_path)

    # Get UPM (Units Per Em)
    if 'head' not in font:
        raise ValueError("The font is missing the 'head' table, cannot determine UPM.")
    upm = font['head'].unitsPerEm  # type: ignore[attr-defined]
    print(f"Font UPM: {upm}")

    # Calculate trak units
    # "takes the trak value and divides by 1000 and multiplies by font UPM and rounds up to get the number of font units"
    shift_val = (trak / 1000.0) * upm
    trak_units = int(math.ceil(shift_val))
    print(f"Tracking value (permille): {trak}")
    print(f"Calculated shift: {shift_val} -> Rounded up: {trak_units} font units")

    # Modify hmtx table
    if 'hmtx' not in font:
        raise ValueError("The font is missing the 'hmtx' table.")

    metrics = font['hmtx'].metrics  # type: ignore[attr-defined]
    modified_count = 0
    zero_count = 0

    for glyph_name in metrics:
        width, lsb = metrics[glyph_name]
        if width == 0:
            zero_count += 1
            continue

        new_width = width + trak_units
        metrics[glyph_name] = (new_width, lsb)
        modified_count += 1

    # Save to output font
    print(f"Saving modified font to: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    font.save(output_path)

    print(f"Done! Modified {modified_count} glyph widths (left {zero_count} zero-width glyphs untouched).")


if __name__ == "__main__":
    fire.Fire(trak_font)

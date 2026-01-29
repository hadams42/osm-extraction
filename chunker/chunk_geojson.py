#!/usr/bin/env python3
"""
Interactive GeoJSON Chunker
Splits large GeoJSON files into smaller chunks based on user-specified max size.
"""

import os
import sys
import json
import glob
from pathlib import Path


def get_size_in_bytes(size_str: str) -> int:
    """Convert size string (e.g., '1mb', '500kb') to bytes."""
    size_str = size_str.strip().lower()
    
    multipliers = {
        'b': 1,
        'kb': 1024,
        'k': 1024,
        'mb': 1024 * 1024,
        'm': 1024 * 1024,
        'gb': 1024 * 1024 * 1024,
        'g': 1024 * 1024 * 1024,
    }
    
    # Extract numeric part and unit
    num_part = ''
    unit_part = ''
    for i, char in enumerate(size_str):
        if char.isdigit() or char == '.':
            num_part += char
        else:
            unit_part = size_str[i:].strip()
            break
    
    if not num_part:
        raise ValueError("Invalid size format. Use format like '1mb', '500kb', '2gb'")
    
    num = float(num_part)
    unit = unit_part if unit_part else 'b'
    
    if unit not in multipliers:
        raise ValueError(f"Unknown unit '{unit}'. Use b, kb, mb, or gb")
    
    return int(num * multipliers[unit])


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def list_geojson_files(directory: str = '.') -> list:
    """Find all GeoJSON files in the specified directory."""
    patterns = ['*.geojson', '*.json']
    files = []
    for pattern in patterns:
        files.extend(glob.glob(os.path.join(directory, pattern)))
    # Filter to only include files that look like GeoJSON
    geojson_files = []
    for f in files:
        if f.endswith('.geojson'):
            geojson_files.append(f)
        elif f.endswith('.json'):
            # Quick check if it might be GeoJSON
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    # Read just the beginning to check
                    start = file.read(500)
                    if '"type"' in start and ('FeatureCollection' in start or 'Feature' in start or 'geometry' in start):
                        geojson_files.append(f)
            except:
                pass
    return sorted(geojson_files)


def select_file() -> str:
    """Interactive file selection."""
    print("\n" + "=" * 60)
    print("  GeoJSON File Chunker")
    print("=" * 60)
    
    geojson_files = list_geojson_files()
    
    if geojson_files:
        print("\nAvailable GeoJSON files in current directory:")
        print("-" * 40)
        for i, f in enumerate(geojson_files, 1):
            size = os.path.getsize(f)
            print(f"  [{i}] {os.path.basename(f)} ({format_size(size)})")
        print(f"  [0] Enter filename manually")
        print("-" * 40)
        
        while True:
            choice = input("\nSelect a file (number) or press Enter for manual entry: ").strip()
            
            if choice == '' or choice == '0':
                break
            
            try:
                idx = int(choice)
                if 1 <= idx <= len(geojson_files):
                    return geojson_files[idx - 1]
                else:
                    print(f"Please enter a number between 1 and {len(geojson_files)}")
            except ValueError:
                print("Invalid input. Please enter a number.")
    else:
        print("\nNo GeoJSON files found in current directory.")
    
    # Manual entry
    while True:
        filename = input("\nEnter the GeoJSON filename (or path): ").strip()
        if not filename:
            print("Filename cannot be empty.")
            continue
        if os.path.isfile(filename):
            return filename
        else:
            print(f"File not found: {filename}")
            retry = input("Try again? (y/n): ").strip().lower()
            if retry != 'y':
                sys.exit(0)


def get_max_size() -> int:
    """Get maximum chunk size from user."""
    print("\n" + "-" * 40)
    print("Enter maximum chunk size")
    print("Examples: 1mb, 500kb, 2gb, 1024kb")
    print("-" * 40)
    
    while True:
        size_input = input("\nMax chunk size: ").strip()
        if not size_input:
            print("Please enter a size.")
            continue
        
        try:
            size_bytes = get_size_in_bytes(size_input)
            if size_bytes < 1024:
                print("Minimum size is 1KB")
                continue
            print(f"  -> {format_size(size_bytes)}")
            return size_bytes
        except ValueError as e:
            print(f"Error: {e}")


def estimate_feature_size(feature: dict) -> int:
    """Estimate the size of a single feature in bytes."""
    return len(json.dumps(feature, ensure_ascii=False))


def chunk_geojson(input_file: str, max_size: int) -> list:
    """
    Split a GeoJSON file into chunks.
    Returns list of (chunk_data, estimated_size) tuples.
    """
    print(f"\nLoading {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle different GeoJSON types
    if data.get('type') != 'FeatureCollection':
        if data.get('type') == 'Feature':
            # Single feature - wrap it
            data = {'type': 'FeatureCollection', 'features': [data]}
        else:
            raise ValueError("Input file must be a GeoJSON FeatureCollection or Feature")
    
    features = data.get('features', [])
    total_features = len(features)
    print(f"Found {total_features} features")
    
    if total_features == 0:
        raise ValueError("GeoJSON file contains no features")
    
    # Preserve any extra properties from the original FeatureCollection
    base_properties = {k: v for k, v in data.items() if k != 'features'}
    
    # Estimate overhead for the FeatureCollection wrapper
    wrapper_overhead = len(json.dumps(base_properties, ensure_ascii=False)) + 20  # +20 for "features":[]
    
    chunks = []
    current_chunk = []
    current_size = wrapper_overhead
    
    # Allow 10% margin of error on the max size
    effective_max = int(max_size * 0.95)
    
    for i, feature in enumerate(features):
        feature_size = estimate_feature_size(feature)
        
        # Check if single feature exceeds max size
        if feature_size + wrapper_overhead > max_size:
            print(f"  Warning: Feature {i} ({format_size(feature_size)}) exceeds max chunk size")
            # Still add it as its own chunk
            if current_chunk:
                # Save current chunk first
                chunk_data = {**base_properties, 'features': current_chunk}
                chunks.append((chunk_data, current_size))
                current_chunk = []
                current_size = wrapper_overhead
            
            chunk_data = {**base_properties, 'features': [feature]}
            chunks.append((chunk_data, feature_size + wrapper_overhead))
            continue
        
        # Check if adding this feature would exceed the limit
        # Account for comma separator between features
        separator_size = 1 if current_chunk else 0
        
        if current_size + feature_size + separator_size > effective_max:
            # Save current chunk and start new one
            if current_chunk:
                chunk_data = {**base_properties, 'features': current_chunk}
                chunks.append((chunk_data, current_size))
            
            current_chunk = [feature]
            current_size = wrapper_overhead + feature_size
        else:
            current_chunk.append(feature)
            current_size += feature_size + separator_size
    
    # Don't forget the last chunk
    if current_chunk:
        chunk_data = {**base_properties, 'features': current_chunk}
        chunks.append((chunk_data, current_size))
    
    return chunks


def save_chunks(chunks: list, input_file: str, output_dir: str = None) -> list:
    """Save chunks to files. Returns list of output filenames."""
    base_name = Path(input_file).stem
    extension = Path(input_file).suffix or '.geojson'
    
    if output_dir is None:
        output_dir = os.path.dirname(input_file) or '.'
    
    os.makedirs(output_dir, exist_ok=True)
    
    output_files = []
    total_chunks = len(chunks)
    padding = len(str(total_chunks))
    
    print(f"\nSaving {total_chunks} chunks...")
    
    for i, (chunk_data, estimated_size) in enumerate(chunks, 1):
        chunk_filename = f"{base_name}_chunk_{str(i).zfill(padding)}{extension}"
        chunk_path = os.path.join(output_dir, chunk_filename)
        
        with open(chunk_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, ensure_ascii=False)
        
        actual_size = os.path.getsize(chunk_path)
        feature_count = len(chunk_data.get('features', []))
        print(f"  [{i}/{total_chunks}] {chunk_filename} - {feature_count} features, {format_size(actual_size)}")
        
        output_files.append(chunk_path)
    
    return output_files


def main():
    try:
        # Step 1: Select file
        input_file = select_file()
        print(f"\nSelected: {input_file}")
        
        original_size = os.path.getsize(input_file)
        print(f"Original size: {format_size(original_size)}")
        
        # Step 2: Get max chunk size
        max_size = get_max_size()
        
        # Quick check if chunking is needed
        if original_size <= max_size:
            print(f"\nFile is already smaller than {format_size(max_size)}.")
            proceed = input("Proceed anyway? (y/n): ").strip().lower()
            if proceed != 'y':
                print("Exiting.")
                return
        
        # Step 3: Optional output directory
        print("\n" + "-" * 40)
        output_dir = input("Output directory (press Enter for same as input): ").strip()
        if not output_dir:
            output_dir = os.path.dirname(input_file) or '.'
        
        # Step 4: Chunk the file
        chunks = chunk_geojson(input_file, max_size)
        
        # Step 5: Confirm and save
        print(f"\nWill create {len(chunks)} chunk files in: {os.path.abspath(output_dir)}")
        confirm = input("Proceed? (y/n): ").strip().lower()
        
        if confirm != 'y':
            print("Cancelled.")
            return
        
        # Step 6: Save chunks
        output_files = save_chunks(chunks, input_file, output_dir)
        
        # Summary
        print("\n" + "=" * 60)
        print("  Summary")
        print("=" * 60)
        print(f"  Input file: {input_file}")
        print(f"  Original size: {format_size(original_size)}")
        print(f"  Chunks created: {len(output_files)}")
        total_output_size = sum(os.path.getsize(f) for f in output_files)
        print(f"  Total output size: {format_size(total_output_size)}")
        print("=" * 60)
        print("\nDone!")
        
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

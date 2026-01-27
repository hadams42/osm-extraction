# GeoJSON Chunker

An interactive Python CLI tool to split large GeoJSON files into smaller chunks based on a user-specified maximum file size.

## Features

- **Interactive file selection** - Lists available GeoJSON files in the current directory with file sizes
- **Manual entry support** - Enter any filename or path directly
- **Flexible size input** - Accepts human-readable formats: `1mb`, `500kb`, `2gb`, etc.
- **Smart chunking** - Splits FeatureCollections while preserving GeoJSON structure and metadata
- **Size margin** - Allows ~5% margin of error for more natural chunk boundaries
- **No dependencies** - Uses only Python standard library

## Requirements

- Python 3.6+

## Usage

```bash
python chunk_geojson.py
```

### Interactive Flow

1. **Select a file** - Choose from the list of detected GeoJSON files or enter a filename manually
2. **Set max chunk size** - Enter the maximum size for each chunk (e.g., `1mb`, `500kb`)
3. **Choose output directory** - Press Enter to use the same directory as the input file
4. **Confirm** - Review and confirm before chunks are created

### Example Session

```
============================================================
  GeoJSON File Chunker
============================================================

Available GeoJSON files in current directory:
----------------------------------------
  [1] buildings.geojson (45.23 MB)
  [2] roads.geojson (12.50 MB)
  [0] Enter filename manually
----------------------------------------

Select a file (number) or press Enter for manual entry: 1

Selected: buildings.geojson
Original size: 45.23 MB

----------------------------------------
Enter maximum chunk size
Examples: 1mb, 500kb, 2gb, 1024kb
----------------------------------------

Max chunk size: 5mb
  -> 5.00 MB

----------------------------------------
Output directory (press Enter for same as input): 

Loading buildings.geojson...
Found 15234 features

Will create 10 chunk files in: D:\OSM
Proceed? (y/n): y

Saving 10 chunks...
  [1/10] buildings_chunk_01.geojson - 1524 features, 4.87 MB
  [2/10] buildings_chunk_02.geojson - 1498 features, 4.92 MB
  ...

============================================================
  Summary
============================================================
  Input file: buildings.geojson
  Original size: 45.23 MB
  Chunks created: 10
  Total output size: 45.23 MB
============================================================

Done!
```

## Output

Chunk files are named using the pattern:

```
{original_name}_chunk_{number}.geojson
```

For example:
- `buildings.geojson` → `buildings_chunk_01.geojson`, `buildings_chunk_02.geojson`, ...

## Size Format

The following size formats are supported:

| Format | Example |
|--------|---------|
| Bytes | `1024b` or `1024` |
| Kilobytes | `500kb` or `500k` |
| Megabytes | `1mb` or `1m` |
| Gigabytes | `1gb` or `1g` |

## How It Works

1. Loads the GeoJSON file and extracts all features from the FeatureCollection
2. Estimates the size of each feature
3. Groups features into chunks that stay under the specified max size
4. Preserves any additional properties from the original FeatureCollection (e.g., `name`, `crs`)
5. Writes each chunk as a valid GeoJSON FeatureCollection

## Notes

- If a single feature exceeds the maximum chunk size, it will be placed in its own chunk with a warning
- The tool uses 95% of the specified max size to allow for slight variations in JSON serialization
- Only GeoJSON files with `FeatureCollection` or `Feature` types are supported

## License

MIT

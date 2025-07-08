#!/usr/bin/env python3

import sys
import os
import json
from scene_downloader import SceneDownloader

if len(sys.argv) != 3:
    print("Usage: python3 scene_downloader_wrapper.py <date_range_json> <output_dir>")
    sys.exit(1)

date_range_json = sys.argv[1]
output_dir = sys.argv[2]

# Validate inputs
try:
    date_range_data = json.loads(date_range_json)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON format: {e}")
    sys.exit(1)

# Check required fields
required_fields = ['start_date', 'end_date']
for field in required_fields:
    if field not in date_range_data:
        print(f"Error: Missing required field '{field}' in date range JSON")
        sys.exit(1)

# Set up parameters with defaults
params = {
    "start_date": date_range_data['start_date'],
    "end_date": date_range_data['end_date'],
    "path": date_range_data.get('path', 15),
    "row": date_range_data.get('row', 35),
    "cloud_cover": date_range_data.get('cloud_cover', 0.80),
    "output_dir": output_dir
}

# Validate date format (basic check)
def is_valid_date(date_str):
    try:
        import datetime
        datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

if not is_valid_date(params['start_date']):
    print(f"Error: Invalid start_date format: {params['start_date']}. Expected YYYY-MM-DD")
    sys.exit(1)

if not is_valid_date(params['end_date']):
    print(f"Error: Invalid end_date format: {params['end_date']}. Expected YYYY-MM-DD")
    sys.exit(1)

# Validate date range
if params['start_date'] > params['end_date']:
    print(f"Error: start_date ({params['start_date']}) must be before end_date ({params['end_date']})")
    sys.exit(1)

# Validate WRS parameters
if not (1 <= params['path'] <= 233):
    print(f"Error: path must be between 1 and 233, got {params['path']}")
    sys.exit(1)

if not (1 <= params['row'] <= 248):
    print(f"Error: row must be between 1 and 248, got {params['row']}")
    sys.exit(1)

if not (0.0 <= params['cloud_cover'] <= 1.0):
    print(f"Error: cloud_cover must be between 0.0 and 1.0, got {params['cloud_cover']}")
    sys.exit(1)

# Create output directory if it doesn't exist
if not os.path.exists(params['output_dir']):
    os.makedirs(params['output_dir'])

print(f"Starting scene search and download")
print(f"Date range: {params['start_date']} to {params['end_date']}")
print(f"WRS Path/Row: {params['path']}/{params['row']}")
print(f"Max cloud cover: {params['cloud_cover']:.1%}")
print(f"Output directory: {params['output_dir']}")

try:
    # Initialize scene downloader
    downloader = SceneDownloader(params['output_dir'])
    
    # Process the date range
    result = downloader.process_date_range(
        params['start_date'], 
        params['end_date'], 
        params['path'], 
        params['row'], 
        params['cloud_cover']
    )
    
    if result:
        print(f"Scene download completed successfully")
        print(f"Extracted files available at: {result}")
        print("Done")
    else:
        print("Scene download failed - no files found")
        sys.exit(1)
        
except Exception as e:
    print(f"Error during scene download: {str(e)}")
    sys.exit(1) 
#!/usr/bin/env python3

import os
import sys
import logging
import datetime
import json
from pathlib import Path
from dotenv import load_dotenv

# Import our modules
from m2m_searcher import LandsatSceneFinder
from espa_downloader import ESPADownloader

# Load environment variables
load_dotenv()

class SceneDownloader:
    """
    Middleman class that handles scene search and download workflow
    Integrates with the server's processing steps interface
    """
    
    def __init__(self, output_dir: str, telemetry_callback=None):
        """
        Initialize the scene downloader
        
        Args:
            output_dir: Directory where downloaded files will be stored
            telemetry_callback: Function to call for logging telemetry
        """
        self.output_dir = output_dir
        self.telemetry_callback = telemetry_callback or self._default_telemetry
        
        # Get credentials from environment
        self.username = os.getenv("ESPA_USERNAME")
        self.token = os.getenv("ESPA_TOKEN")
        self.password = os.getenv("ESPA_PASSWORD")
        
        if not all([self.username, self.token, self.password]):
            raise ValueError("Missing required environment variables: USERNAME, TOKEN, PASSWORD")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        self.telemetry_callback("SceneDownloader initialized successfully")
    
    def _default_telemetry(self, message):
        """Default telemetry function if none provided"""
        print(f"[SceneDownloader] {message}")
    
    def process_date_range(self, start_date: str, end_date: str, path: int = 15, row: int = 35, max_cloud_cover: float = 0.80) -> str:
        """
        Process a date range: search for scenes and download them
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            path: WRS path number
            row: WRS row number
            max_cloud_cover: Maximum cloud cover (0.0 to 1.0)
            
        Returns:
            str: Path to the directory containing extracted tar.gz files
        """
        self.telemetry_callback(f"Starting scene search and download for date range: {start_date} to {end_date}")
        
        # Step 1: Search for scenes
        scene_ids = self._search_scenes(start_date, end_date, path, row, max_cloud_cover)
        
        if not scene_ids:
            self.telemetry_callback("No scenes found, exiting")
            return None
        
        # Step 2: Download scenes
        downloaded_files = self._download_scenes(scene_ids)
        
        if not downloaded_files:
            self.telemetry_callback("No files downloaded, exiting")
            return None
        
        # Step 3: Extract tar.gz files
        extracted_dirs = self._extract_files(downloaded_files)
        
        if not extracted_dirs:
            self.telemetry_callback("No files extracted, exiting")
            return None
        
        # Return the path to the extracted files directory
        return extracted_dirs[0] if len(extracted_dirs) == 1 else extracted_dirs
    
    def process_dates_list(self, dates_list: list, path: int = 15, row: int = 35, max_cloud_cover: float = 0.80) -> str:
        """
        Process a list of dates: search for scenes and download them
        
        Args:
            dates_list: List of dates in YYYY-MM-DD format
            path: WRS path number
            row: WRS row number
            max_cloud_cover: Maximum cloud cover (0.0 to 1.0)
            
        Returns:
            str: Path to the directory containing extracted tar.gz files
        """
        self.telemetry_callback(f"Starting scene search and download for {len(dates_list)} dates")
        
        # Step 1: Search for scenes
        scene_ids = self._search_scenes_list(dates_list, path, row, max_cloud_cover)
        
        if not scene_ids:
            self.telemetry_callback("No scenes found, exiting")
            return None
        
        # Step 2: Download scenes
        downloaded_files = self._download_scenes(scene_ids)
        
        if not downloaded_files:
            self.telemetry_callback("No files downloaded, exiting")
            return None
        
        # Step 3: Extract tar.gz files
        extracted_dirs = self._extract_files(downloaded_files)
        
        if not extracted_dirs:
            self.telemetry_callback("No files extracted, exiting")
            return None
        
        # Return the path to the extracted files directory
        return extracted_dirs[0] if len(extracted_dirs) == 1 else extracted_dirs
    
    def _search_scenes(self, start_date: str, end_date: str, path: int, row: int, max_cloud_cover: float) -> list:
        """Search for scenes in a date range"""
        self.telemetry_callback("Initializing scene finder...")
        
        try:
            finder = LandsatSceneFinder(
                username=self.username,
                token=self.token,
                dates_range=(start_date, end_date),
                dates_list=None,
                filters={'max_cloud_cover': max_cloud_cover},
                params={'path': path, 'row': row}
            )
            
            self.telemetry_callback("Scene finder initialized successfully")
            
            # Search for scenes
            scene_ids = finder.process()
            
            if scene_ids:
                self.telemetry_callback(f"Found {len(scene_ids)} scene IDs")
                for scene_id in scene_ids:
                    self.telemetry_callback(f"  - {scene_id}")
            else:
                self.telemetry_callback("No scene IDs found")
            
            finder.logout()
            return scene_ids
            
        except Exception as e:
            self.telemetry_callback(f"Error in scene search: {str(e)}")
            return []
    
    def _search_scenes_list(self, dates_list: list, path: int, row: int, max_cloud_cover: float) -> list:
        """Search for scenes in a list of dates"""
        self.telemetry_callback("Initializing scene finder...")
        
        try:
            finder = LandsatSceneFinder(
                username=self.username,
                token=self.token,
                dates_range=None,
                dates_list=dates_list,
                filters={'max_cloud_cover': max_cloud_cover},
                params={'path': path, 'row': row}
            )
            
            self.telemetry_callback("Scene finder initialized successfully")
            
            # Search for scenes
            scene_ids = finder.process()
            
            if scene_ids:
                self.telemetry_callback(f"Found {len(scene_ids)} scene IDs")
                for scene_id in scene_ids:
                    self.telemetry_callback(f"  - {scene_id}")
            else:
                self.telemetry_callback("No scene IDs found")
            
            finder.logout()
            return scene_ids
            
        except Exception as e:
            self.telemetry_callback(f"Error in scene search: {str(e)}")
            return []
    
    def _download_scenes(self, scene_ids: list) -> list:
        """Download scenes using ESPA downloader"""
        self.telemetry_callback("Initializing ESPA downloader...")
        
        try:
            downloader = ESPADownloader(
                username=self.username,
                password=self.password,
                token=self.token,
                scene_ids=scene_ids,
                output_dir=self.output_dir
            )
            
            self.telemetry_callback("ESPA downloader initialized successfully")
            
            # Process downloads
            downloader.process()
            
            # Find downloaded tar.gz files
            tar_files = []
            for root, dirs, files in os.walk(self.output_dir):
                for file in files:
                    if file.endswith('.tar.gz'):
                        tar_files.append(os.path.join(root, file))
            
            if tar_files:
                self.telemetry_callback(f"Downloaded {len(tar_files)} tar.gz files")
                for tar_file in tar_files:
                    self.telemetry_callback(f"  - {os.path.basename(tar_file)}")
            else:
                self.telemetry_callback("No tar.gz files found after download")
            
            return tar_files
            
        except Exception as e:
            self.telemetry_callback(f"Error in scene download: {str(e)}")
            return []
    
    def _extract_files(self, tar_files: list) -> list:
        """Extract tar.gz files"""
        self.telemetry_callback("Starting file extraction...")
        
        extracted_dirs = []
        
        for tar_file in tar_files:
            try:
                import tarfile
                
                filename = os.path.basename(tar_file)
                base_name = os.path.splitext(os.path.splitext(filename)[0])[0]
                extract_dir = os.path.join(self.output_dir, base_name)
                
                os.makedirs(extract_dir, exist_ok=True)
                
                self.telemetry_callback(f"Extracting {filename} to {extract_dir}...")
                
                with tarfile.open(tar_file, 'r:gz') as tar:
                    tar.extractall(path=extract_dir)
                
                self.telemetry_callback(f"Successfully extracted {filename}")
                extracted_dirs.append(extract_dir)
                
            except Exception as e:
                self.telemetry_callback(f"Error extracting {os.path.basename(tar_file)}: {str(e)}")
        
        if extracted_dirs:
            self.telemetry_callback(f"Successfully extracted {len(extracted_dirs)} files")
        else:
            self.telemetry_callback("No files were successfully extracted")
        
        return extracted_dirs


def main():
    """Command line interface for testing"""
    if len(sys.argv) < 4:
        print("Usage: python scene_downloader.py <start_date> <end_date> <output_dir> [path] [row] [cloud_cover]")
        print("Example: python scene_downloader.py 2023-06-01 2023-06-30 ./downloads 11 31 0.80")
        sys.exit(1)
    
    start_date = sys.argv[1]
    end_date = sys.argv[2]
    output_dir = sys.argv[3]
    path = int(sys.argv[4]) if len(sys.argv) > 4 else 11
    row = int(sys.argv[5]) if len(sys.argv) > 5 else 31
    cloud_cover = float(sys.argv[6]) if len(sys.argv) > 6 else 0.80
    
    try:
        downloader = SceneDownloader(output_dir)
        result = downloader.process_date_range(start_date, end_date, path, row, cloud_cover)
        
        if result:
            print(f"\nSuccess! Extracted files available at: {result}")
        else:
            print("\nNo files were processed successfully")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
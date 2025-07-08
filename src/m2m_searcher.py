#!/usr/bin/env python3

import os
import sys
import logging
import datetime
from pathlib import Path
import json
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("landsat_scene_finder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LandsatSceneFinder:
    def __init__(self, username, token, dates_list=None, dates_range=None, filters=None, params=None):
        """
        Initialize the Landsat scene finder

        Args:
            username (str): USGS username
            token (str): USGS API token
            dates_list (list): List of dates to search for
            dates_range (tuple): Tuple of (start_date, end_date) for range search
            filters (dict): Search filters
            params (dict): Additional parameters
        """
        self.dates_list = dates_list
        self.dates_range = dates_range
        self.filters = filters or {}
        self.params = params or {}

        # Extract credentials
        self.username = username
        self.token = token

        # API configuration - Updated to use correct dataset name
        self.serviceUrl = "https://m2m.cr.usgs.gov/api/api/json/stable/"
        # Use the correct dataset name for Landsat 8 Collection 2 Level 1
        # According to USGS documentation, the correct dataset name is:
        self.dataset_name = "landsat_ot_c2_l1"

        # Default search parameters - Updated to use WRS path/row that has data
        self.path = self.params.get('path', 15)  # Changed from 11 to 15
        self.row = self.params.get('row', 35)    # Changed from 31 to 35
        self.max_cloud_cover = self.filters.get('max_cloud_cover', 0.80)

        # Login and get API key
        self.apiKey = self.login()

        # Validate input
        if not self.dates_list and not self.dates_range:
            raise ValueError("Either dates_list or dates_range must be provided")

        logger.info(f"Initialized LandsatSceneFinder")

    def login(self):
        """
        Login to the USGS M2M API and get an API key

        Returns:
            str: API key for further requests
        """
        logger.info(f"Logging in with username: {self.username}")
        payload = {'username': self.username, 'token': self.token}

        apiKey = self.sendRequest(self.serviceUrl + "login-token", payload)
        logger.info("Successfully obtained API Key")

        return apiKey

    def logout(self):
        """
        Logout from the USGS M2M API
        """
        endpoint = "logout"
        result = self.sendRequest(self.serviceUrl + endpoint, None, self.apiKey)
        if result is None:
            logger.info("Logged Out")
        else:
            logger.error("Logout Failed")

    def sendRequest(self, url, data, apiKey=None):
        """
        Send HTTP request to the USGS M2M API

        Args:
            url (str): API endpoint URL
            data (dict): Request payload
            apiKey (str, optional): API key for authentication

        Returns:
            dict/str: Response data
        """
        pos = url.rfind('/') + 1
        endpoint = url[pos:]

        # Convert data to JSON
        json_data = json.dumps(data) if data else None

        try:
            if apiKey is None:
                response = requests.post(url, data=json_data)
            else:
                headers = {'X-Auth-Token': apiKey}
                response = requests.post(url, data=json_data, headers=headers)

            # Check HTTP status code
            http_status_code = response.status_code
            if http_status_code != 200:
                logger.error(f"HTTP Error: {http_status_code}")
                response.close()
                return None

            # Parse response
            output = json.loads(response.text)

            # Check for API errors
            if output.get('errorCode'):
                logger.error(f"API Error: {output.get('errorCode')} - {output.get('errorMessage')}")
                logger.error(f"Request ID: {output.get('requestId')}")
                response.close()
                return None

            # Log success
            logger.info(f"Request {endpoint} completed with request ID {output.get('requestId', 'unknown')}")

            # Close response
            response.close()

            # Return data
            return output.get('data')

        except Exception as e:
            logger.error(f"Error in sendRequest for {endpoint}: {e}")
            if 'response' in locals() and response:
                response.close()
            return None

    def format_date_payload(self, date_obj):
        """
        Format the payload for scene ID request using a date

        Args:
            date_obj: A datetime object

        Returns:
            dict: Formatted payload for API request
        """
        logger.info(f"Formatting payload for date: {date_obj}")

        try:
            # Format as YYYY-MM-DD for API
            date_str = date_obj.strftime('%Y-%m-%d')

            # Create temporal filter
            temporal_filter = {'start': date_str, 'end': date_str}

            # Create metadata filter with correct filter IDs
            # These filter IDs are from the official USGS M2M API documentation
            metadataFilter = {
                "filterType": "and",
                "childFilters": [
                    {'filterType': 'value', 'filterId': '5e83d14fb9436d88', 'value': self.path},  # WRS Path
                    {'filterType': 'value', 'filterId': '5e83d14ff1eda1b8', 'value': self.row},  # WRS Row
                    {'filterType': 'value', 'filterId': '5e83d14fc6e09eb6', 'value': 'OLI_TIRS'}  # Sensor Identifier
                ]
            }

            # Create payload structure
            payload = {
                'datasetName': self.dataset_name,
                'maxResults': 10,
                'sceneFilter': {
                    'acquisitionFilter': temporal_filter,
                    'metadataFilter': metadataFilter
                }
            }

            # Add cloud cover filter only if specified
            if self.max_cloud_cover is not None:
                payload['sceneFilter']['cloudCoverFilter'] = {
                    "max": self.max_cloud_cover,
                    "min": 0,
                    "includeUnknown": True
                }

            logger.info(f"Generated payload for date: {date_obj}")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
            return payload

        except Exception as e:
            logger.error(f"Error formatting payload: {e}")
            return None

    def format_range_payload(self, start_date, end_date):
        """
        Format the payload for scene ID request using a date range

        Args:
            start_date: Start date string or datetime
            end_date: End date string or datetime

        Returns:
            dict: Formatted payload for API request
        """
        logger.info(f"Formatting payload for range: {start_date} to {end_date}")

        # Convert date strings to datetime objects if needed
        if isinstance(start_date, str):
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')

        try:
            # Format as YYYY-MM-DD for API
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')

            # Create temporal filter
            temporal_filter = {'start': start_date_str, 'end': end_date_str}

            # Create metadata filter with correct filter IDs
            # These filter IDs are from the official USGS M2M API documentation
            metadataFilter = {
                "filterType": "and",
                "childFilters": [
                    {'filterType': 'value', 'filterId': '5e83d14fb9436d88', 'value': self.path},  # WRS Path
                    {'filterType': 'value', 'filterId': '5e83d14ff1eda1b8', 'value': self.row},  # WRS Row
                    {'filterType': 'value', 'filterId': '5e83d14fc6e09eb6', 'value': 'OLI_TIRS'}  # Sensor Identifier
                ]
            }

            # Create payload structure
            payload = {
                'datasetName': self.dataset_name,
                'maxResults': 100,  # Higher for date range queries
                'sceneFilter': {
                    'acquisitionFilter': temporal_filter,
                    'metadataFilter': metadataFilter
                }
            }

            # Add cloud cover filter only if specified
            if self.max_cloud_cover is not None:
                payload['sceneFilter']['cloudCoverFilter'] = {
                    "max": self.max_cloud_cover,
                    "min": 0,
                    "includeUnknown": True
                }

            logger.info(f"Generated payload for date range")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
            return payload

        except Exception as e:
            logger.error(f"Error formatting range payload: {e}")
            return None

    def search_scenes(self, payload):
        """
        Search for scenes based on the provided payload

        Args:
            payload (dict): Search criteria payload

        Returns:
            list: List of scene metadata found
        """
        logger.info("Searching scenes...")
        logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            url = self.serviceUrl + "scene-search"
            response = requests.post(
                url,
                json=payload,
                headers={'X-Auth-Token': self.apiKey}
            )

            logger.info(f"Response status: {response.status_code}")

            try:
                response_data = response.json()
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response")
                return []

            # Check for API errors
            if response.status_code != 200 or response_data.get('errorCode'):
                error_msg = f"API Error: {response_data.get('errorCode')} - {response_data.get('errorMessage')}"
                logger.error(error_msg)
                logger.error(f"Full response: {json.dumps(response_data, indent=2)}")
                return []

            # Get the scenes data
            scenes = response_data.get('data', {})

            if scenes.get('recordsReturned', 0) > 0:
                # Log the structure of the first result if available
                if scenes.get('results') and len(scenes.get('results')) > 0:
                    first_result = scenes['results'][0]
                    logger.info(f"First result keys: {list(first_result.keys())}")

                # Return the results
                return scenes.get('results', [])
            else:
                logger.info("Search found no results")
                logger.debug(f"Full response: {json.dumps(response_data, indent=2)}")
                return []

        except Exception as e:
            logger.error(f"Error searching scenes: {e}")
            return []

    def process_date(self, date_obj):
        """
        Process a single date

        Args:
            date_obj: Date to search for

        Returns:
            list: List of scene IDs found
        """
        logger.info(f"Processing date: {date_obj}")

        # Format the payload
        payload = self.format_date_payload(date_obj)
        if not payload:
            logger.error(f"Failed to create payload for date {date_obj}")
            return []

        # Search for scenes
        scenes = self.search_scenes(payload)

        # Check if any scenes were found
        if not scenes:
            logger.warning(f"No scenes found for date {date_obj}")
            return []

        # Extract scene IDs
        scene_ids = []
        for scene in scenes:
            scene_id = scene.get('displayId')
            if scene_id:
                scene_ids.append(scene_id)
                print(f"Found scene ID: {scene_id}")

        return scene_ids

    def process_dates_list(self):
        """
        Process list of dates
        """
        if not self.dates_list:
            logger.error("No dates list provided")
            return []

        logger.info(f"Processing {len(self.dates_list)} dates")

        all_scene_ids = []
        for date_str in self.dates_list:
            try:
                # Convert string to datetime if needed
                if isinstance(date_str, str):
                    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                else:
                    date_obj = date_str

                scene_ids = self.process_date(date_obj)
                all_scene_ids.extend(scene_ids)

            except Exception as e:
                logger.error(f"Error processing date {date_str}: {e}")
                continue

        logger.info(f"Found {len(all_scene_ids)} total scene IDs")
        return all_scene_ids

    def process_date_range(self):
        """
        Process date range
        """
        if not self.dates_range:
            logger.error("No date range provided")
            return []

        start_date, end_date = self.dates_range

        # Check if dates are valid
        if not start_date or not end_date:
            logger.error(f"Invalid date range: {start_date} to {end_date}")
            return []

        logger.info(f"Processing date range from {start_date} to {end_date}")

        # Format the payload
        payload = self.format_range_payload(start_date, end_date)
        if not payload:
            logger.error("Failed to create payload for date range")
            return []

        # Search for scenes
        scenes = self.search_scenes(payload)

        # Check if any scenes were found
        if not scenes:
            logger.warning(f"No scenes found for date range")
            return []

        # Extract scene IDs
        scene_ids = []
        for scene in scenes:
            scene_id = scene.get('displayId')
            if scene_id:
                scene_ids.append(scene_id)
                print(f"Found scene ID: {scene_id}")

        logger.info(f"Found {len(scene_ids)} scene IDs for date range")
        return scene_ids

    def process(self):
        """
        Main processing function
        """
        if self.dates_list:
            return self.process_dates_list()
        elif self.dates_range:
            return self.process_date_range()
        else:
            logger.error("No search method specified")
            return []

def main():
    """Main function to run the Landsat scene finder"""
    
    # Example usage - you can modify these parameters as needed
    username = os.getenv("ESPA_USERNAME")
    token = os.getenv("ESPA_TOKEN")
    
    if not username or not token:
        print("Please set ESPA_USERNAME and ESPA_TOKEN environment variables in your .env file")
        sys.exit(1)

    # Example 1: Search for specific dates
    dates_list = [
        "2023-06-15",
        "2023-06-16", 
        "2023-06-17"
    ]
    
    # Example 2: Search for date range
    dates_range = ("2023-06-01", "2023-06-30")
    
    # Choose which search method to use
    use_dates_list = True  # Set to False to use date range instead
    
    try:
        if use_dates_list:
            # Create scene finder for dates list
            finder = LandsatSceneFinder(
                username=username,
                token=token,
                dates_list=dates_list,
                dates_range=None,
                filters={'max_cloud_cover': 0.80},
                params={'path': 15, 'row': 35}
            )
        else:
            # Create scene finder for date range
            finder = LandsatSceneFinder(
                username=username,
                token=token,
                dates_list=None,
                dates_range=dates_range,
                filters={'max_cloud_cover': 0.80},
                params={'path': 15, 'row': 35}
            )

        # Process and get scene IDs
        scene_ids = finder.process()
        
        # Print summary
        print(f"\nSummary: Found {len(scene_ids)} scene IDs")
        if scene_ids:
            print("Scene IDs:")
            for scene_id in scene_ids:
                print(f"  {scene_id}")

        # Logout
        finder.logout()

        logger.info("Script completed successfully")

    except Exception as e:
        logger.error(f"An error occurred in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
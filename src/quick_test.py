#!/usr/bin/env python3

import os
import json
import requests

def quick_test():
    """Quick test to identify the API issue"""
    
    print("USGS M2M API Quick Test")
    print("=" * 30)
    
    # Get credentials
    username = input("Enter your USGS username: ")
    token = input("Enter your USGS token: ")
    
    print(f"\nTesting with username: {username}")
    
    # Step 1: Login
    print("\n1. Testing login...")
    login_url = "https://m2m.cr.usgs.gov/api/api/json/stable/login-token"
    login_payload = {'username': username, 'token': token}
    
    try:
        response = requests.post(login_url, json=login_payload)
        print(f"Login status: {response.status_code}")
        
        if response.status_code == 200:
            login_data = response.json()
            if login_data.get('errorCode'):
                print(f"❌ Login failed: {login_data.get('errorCode')} - {login_data.get('errorMessage')}")
                return
            else:
                api_key = login_data.get('data')
                print(f"✅ Login successful")
        else:
            print(f"❌ Login failed: {response.status_code}")
            return
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return
    
    # Step 2: Test dataset search
    print("\n2. Finding available Landsat datasets...")
    dataset_url = "https://m2m.cr.usgs.gov/api/api/json/stable/dataset-search"
    dataset_payload = {
        "includeMessages": True,
        "includeFacets": True,
        "maxResults": 20,
        "searchTerms": "landsat"
    }
    
    try:
        response = requests.post(dataset_url, json=dataset_payload, headers={'X-Auth-Token': api_key})
        print(f"Dataset search status: {response.status_code}")
        
        if response.status_code == 200:
            dataset_data = response.json()
            if dataset_data.get('errorCode'):
                print(f"❌ Dataset search failed: {dataset_data.get('errorCode')}")
            else:
                datasets = dataset_data.get('data', [])
                landsat_datasets = [d for d in datasets if 'landsat' in d.get('datasetName', '').lower()]
                print(f"✅ Found {len(landsat_datasets)} Landsat datasets:")
                for dataset in landsat_datasets[:5]:  # Show first 5
                    print(f"   - {dataset.get('datasetName')}: {dataset.get('datasetFullName')}")
        else:
            print(f"❌ Dataset search failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Dataset search error: {e}")
    
    # Step 3: Test scene search with different parameters
    print("\n3. Testing scene search...")
    scene_url = "https://m2m.cr.usgs.gov/api/api/json/stable/scene-search"
    
    # Test different scenarios
    test_scenarios = [
        {
            "name": "Basic search (no filters)",
            "payload": {
                "datasetName": "landsat_ot_c2_l1",
                "maxResults": 5,
                "sceneFilter": {
                    "acquisitionFilter": {
                        "start": "2023-06-01",
                        "end": "2023-06-05"
                    }
                }
            }
        },
        {
            "name": "Different date range (2022)",
            "payload": {
                "datasetName": "landsat_ot_c2_l1",
                "maxResults": 5,
                "sceneFilter": {
                    "acquisitionFilter": {
                        "start": "2022-06-01",
                        "end": "2022-06-30"
                    }
                }
            }
        },
        {
            "name": "Different dataset (landsat_8_c2_l1)",
            "payload": {
                "datasetName": "landsat_8_c2_l1",
                "maxResults": 5,
                "sceneFilter": {
                    "acquisitionFilter": {
                        "start": "2023-06-01",
                        "end": "2023-06-05"
                    }
                }
            }
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n   Testing: {scenario['name']}")
        try:
            response = requests.post(scene_url, json=scenario['payload'], headers={'X-Auth-Token': api_key})
            
            if response.status_code == 200:
                scene_data = response.json()
                if scene_data.get('errorCode'):
                    print(f"      ❌ API Error: {scene_data.get('errorCode')} - {scene_data.get('errorMessage')}")
                else:
                    scenes = scene_data.get('data', {})
                    records_returned = scenes.get('recordsReturned', 0)
                    print(f"      ✅ Found {records_returned} scenes")
                    
                    if records_returned > 0:
                        results = scenes.get('results', [])
                        for i, scene in enumerate(results[:2]):
                            scene_id = scene.get('displayId', 'Unknown')
                            print(f"         Scene {i+1}: {scene_id}")
            else:
                print(f"      ❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    # Step 4: Logout
    print("\n4. Logging out...")
    logout_url = "https://m2m.cr.usgs.gov/api/api/json/stable/logout"
    
    try:
        response = requests.post(logout_url, headers={'X-Auth-Token': api_key})
        if response.status_code == 200:
            print("✅ Logout successful")
        else:
            print(f"❌ Logout failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Logout error: {e}")
    
    print("\n" + "=" * 30)
    print("Test completed!")

if __name__ == "__main__":
    quick_test() 
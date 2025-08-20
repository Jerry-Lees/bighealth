#!/usr/bin/env python3
"""
F5 iHealth API Utility Functions

Common utility functions and base API client.
"""

import json
import requests
from datetime import datetime
from qkview_directory_utils import initialize_qkview_processing, save_data_to_qkview


class F5iHealthClient:
    """Base F5 iHealth API client"""
    
    def __init__(self, auth_handler, debug=False):
        self.auth = auth_handler
        self.base_url = "https://ihealth2-api.f5.com/qkview-analyzer/api"
        self.debug = debug
        
    def _make_request(self, method, endpoint, **kwargs):
        """Make an authenticated API request"""
        # Ensure we have a valid token
        if not self.auth.refresh_token_if_needed():
            print("Failed to authenticate or refresh token")
            return None
            
        session = self.auth.get_authenticated_session()
        if not session:
            print("No authenticated session available")
            return None
            
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = session.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Check if response has content
            if not response.content:
                if self.debug:
                    print(f"DEBUG: Empty response from {url}")
                return None
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if 'application/json' not in content_type:
                if self.debug:
                    print(f"DEBUG: Non-JSON response from {url}")
                    print(f"DEBUG: Content-Type: {content_type}")
                    print(f"DEBUG: Response text: {response.text[:200]}...")
                return None
            
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Status code: {e.response.status_code}")
                if self.debug:
                    print(f"DEBUG: Response headers: {dict(e.response.headers)}")
                try:
                    error_details = e.response.json()
                    if self.debug:
                        print(f"DEBUG: Error details: {json.dumps(error_details, indent=2)}")
                except:
                    print(f"Response text: {e.response.text}")
            return None
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            if self.debug:
                print(f"DEBUG: Response status: {response.status_code}")
                print(f"DEBUG: Response headers: {dict(response.headers)}")
                print(f"DEBUG: Response text: {response.text[:500]}...")
            return None
    
    def list_qkviews(self):
        """Get a list of all QKViews"""
        return self._make_request("GET", "/qkviews")
    
    def get_qkview_details(self, qkview_id):
        """Get detailed information about a specific QKView"""
        return self._make_request("GET", f"/qkviews/{qkview_id}")
    
    def delete_qkview(self, qkview_id):
        """Delete a QKView"""
        result = self._make_request("DELETE", f"/qkviews/{qkview_id}")
        return result is not None
    
    def process_qkview(self, qkview_id, create_directories=True):
        """
        Process a QKView - get details and optionally create directory structure
        
        Args:
            qkview_id (str): QKView ID
            create_directories (bool): Whether to create directory structure
            
        Returns:
            dict: QKView details
        """
        print(f"Processing QKView {qkview_id}...")
        
        # Get detailed QKView information
        qkview_details = self.get_qkview_details(qkview_id)
        
        if qkview_details and create_directories:
            # Create directory structure and save basic info
            initialize_qkview_processing(qkview_id, qkview_details)
            
            # Save the raw API response
            save_data_to_qkview(qkview_id, "Docs", "api_response.json", qkview_details)
        
        return qkview_details


def format_timestamp(timestamp_str):
    """Format timestamp string to human-readable format"""
    try:
        # Try different timestamp formats that F5 iHealth might use
        for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except ValueError:
                continue
        return timestamp_str  # Return original if no format matches
    except:
        return timestamp_str


def print_qkview_summary(qkview_data, show_raw=False):
    """Print a formatted summary of QKView data"""
    print("\n" + "="*80)
    print("F5 IHEALTH QKVIEW LISTING")
    print("="*80)
    
    if not qkview_data:
        print("No qkview data received from API")
        return
    
    if show_raw:
        print("\nRAW API RESPONSE:")
        print("-" * 40)
        print(json.dumps(qkview_data, indent=2))
        print("-" * 40)
    
    # Handle different response formats
    if isinstance(qkview_data, list):
        print(f"\nFOUND {len(qkview_data)} QKVIEW ID(S):")
        print("="*80)
        for i, qkview_id in enumerate(qkview_data, 1):
            print(f"QKVIEW ID #{i}: {qkview_id}")
        return
    
    if isinstance(qkview_data, dict):
        # Check if this is a simple ID list in a dictionary
        if len(qkview_data) == 1:
            key, value = next(iter(qkview_data.items()))
            if isinstance(value, list) and all(isinstance(item, (str, int)) for item in value):
                print(f"\nFOUND {len(value)} QKVIEW ID(S) in '{key}':")
                print("="*80)
                for i, qkview_id in enumerate(value, 1):
                    print(f"QKVIEW ID #{i}: {qkview_id}")
                return
        
        # Handle structured qkview data
        if 'qkviews' in qkview_data:
            qkviews = qkview_data['qkviews']
        elif 'data' in qkview_data:
            qkviews = qkview_data['data']
        else:
            qkviews = [qkview_data]
    else:
        print(f"Unexpected data format: {type(qkview_data)}")
        return
    
    # Handle detailed qkview objects
    if isinstance(qkviews, list) and qkviews and isinstance(qkviews[0], dict):
        print(f"\nFOUND {len(qkviews)} DETAILED QKVIEW(S):")
        print("="*80)
        
        for i, qkview in enumerate(qkviews, 1):
            print(f"\nQKVIEW #{i}")
            print("-" * 20)
            
            # Common fields
            common_fields = [
                ('id', 'ID'),
                ('name', 'Name'),
                ('filename', 'Filename'),
                ('file_name', 'File Name'),
                ('status', 'Status'),
                ('upload_date', 'Upload Date'),
                ('uploaded_date', 'Uploaded Date'),
                ('created_date', 'Created Date'),
                ('file_size', 'File Size'),
                ('size', 'Size'),
                ('device_name', 'Device Name'),
                ('hostname', 'Hostname'),
                ('version', 'F5 Version'),
                ('f5_version', 'F5 Version'),
                ('platform', 'Platform'),
                ('serial_number', 'Serial Number'),
                ('analysis_status', 'Analysis Status'),
                ('diagnostics_count', 'Diagnostics Count'),
                ('recommendations_count', 'Recommendations Count')
            ]
            
            # Print known fields
            for field_key, field_label in common_fields:
                if field_key in qkview:
                    value = qkview[field_key]
                    if 'date' in field_key.lower() and isinstance(value, str):
                        value = format_timestamp(value)
                    print(f"{field_label:20}: {value}")
            
            # Print additional fields
            printed_fields = {field[0] for field in common_fields}
            additional_fields = {k: v for k, v in qkview.items() if k not in printed_fields}
            
            if additional_fields:
                print("\nAdditional Fields:")
                for key, value in additional_fields.items():
                    if isinstance(value, (dict, list)):
                        print(f"{key:20}: {json.dumps(value, indent=2)}")
                    else:
                        print(f"{key:20}: {value}")


if __name__ == "__main__":
    # Test the client
    from ihealth_auth import F5iHealthAuth, load_credentials_from_files
    
    client_id, client_secret = load_credentials_from_files()
    if not client_id or not client_secret:
        print("No credentials found in files")
        exit(1)
    
    auth = F5iHealthAuth(client_id, client_secret)
    if auth.authenticate():
        client = F5iHealthClient(auth)
        qkviews = client.list_qkviews()
        print_qkview_summary(qkviews, show_raw=True)
    else:
        print("Authentication failed")


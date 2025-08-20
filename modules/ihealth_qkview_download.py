#!/usr/bin/env python3
"""
F5 iHealth QKView Download Module

Handles downloading QKView files from the F5 iHealth API and saving them
with proper naming conventions based on hostname and creation date.
"""

import os
import time
from datetime import datetime
from ihealth_utils import F5iHealthClient
from qkview_directory_utils import update_qkview_metadata, find_qkview_directory


class F5iHealthQKViewDownload(F5iHealthClient):
    """F5 iHealth QKView file download operations"""
    
    def __init__(self, auth_handler):
        super().__init__(auth_handler)
    
    def _download_qkview_file(self, qkview_id):
        """
        Download QKView file content from the API
        
        Args:
            qkview_id (str): QKView ID
            
        Returns:
            bytes: QKView file content or None if failed
        """
        # Ensure we have a valid token
        if not self.auth.refresh_token_if_needed():
            print("Failed to authenticate or refresh token")
            return None
            
        session = self.auth.get_authenticated_session()
        if not session:
            print("No authenticated session available")
            return None
        
        # QKView download endpoint - correct endpoint according to F5 iHealth API docs
        endpoint = f"/qkviews/{qkview_id}/files/qkview"
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if self.debug:
                print(f"  DEBUG: QKView download URL: {url}")
            
            print(f"  Downloading QKView file for {qkview_id}...")
            
            # Set appropriate headers for QKView file download
            headers = {
                'Accept': 'application/octet-stream',
                'User-Agent': 'BigHealth-iHealthClient'
            }
            
            response = session.get(url, stream=True, headers=headers)
            
            # Handle 202 (processing) responses
            if response.status_code == 202:
                print("  QKView file is being prepared, waiting...")
                time.sleep(10)  # Wait 10 seconds as recommended by API docs
                response = session.get(url, stream=True, headers=headers)
            
            response.raise_for_status()
            
            # Read the content
            content = b""
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content += chunk
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r  Downloading: {percent:.1f}%", end="")
            
            print()  # New line after progress
            return content
            
        except Exception as e:
            error_msg = f"  Failed to download QKView file: {e}"
            print(error_msg)
            
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                print(f"  Status code: {status_code}")
                
                if status_code == 404:
                    print(f"  ERROR: QKView {qkview_id} not found or not accessible")
                    print(f"  This could mean:")
                    print(f"    - QKView doesn't exist")
                    print(f"    - QKView is not processed yet")
                    print(f"    - Insufficient permissions")
                elif status_code == 403:
                    print(f"  ERROR: Access denied to QKView {qkview_id}")
                    print(f"  Check your API credentials and permissions")
                elif status_code == 401:
                    print(f"  ERROR: Authentication failed")
                    print(f"  Your session may have expired")
                
                if self.debug:
                    print(f"  DEBUG: Response headers: {dict(e.response.headers)}")
                    try:
                        print(f"  DEBUG: Response content: {e.response.text[:500]}")
                    except:
                        pass
            return None
    
    def _extract_hostname_from_qkview_data(self, qkview_data):
        """
        Extract hostname from QKView API response data
        
        Args:
            qkview_data (dict): QKView details from API
            
        Returns:
            str: Hostname or fallback name
        """
        if not qkview_data or not isinstance(qkview_data, dict):
            return "unknown_device"
        
        # Look for hostname in various possible fields (in order of preference)
        hostname_fields = [
            'hostname',           # Most direct field
            'device_name',        # Device name
            'name',              # General name field
            'filename',          # Original filename
            'file_name',         # Alternative filename field
            'device_hostname',   # Alternative hostname field
            'system_hostname'    # System-level hostname
        ]
        
        for field in hostname_fields:
            if field in qkview_data and qkview_data[field]:
                hostname = str(qkview_data[field])
                
                # Clean up the hostname
                # Remove .qkview extension if present
                if hostname.lower().endswith('.qkview'):
                    hostname = hostname[:-7]
                
                # Remove common file extensions
                for ext in ['.tar', '.gz', '.tgz', '.zip']:
                    if hostname.lower().endswith(ext):
                        hostname = hostname[:-(len(ext))]
                
                # Replace invalid filename characters
                invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']
                for char in invalid_chars:
                    hostname = hostname.replace(char, '_')
                
                # Remove extra underscores
                while '__' in hostname:
                    hostname = hostname.replace('__', '_')
                
                hostname = hostname.strip('_')
                
                if hostname:  # Make sure we still have something after cleaning
                    return hostname
        
        # Fallback to QKView ID if no hostname found
        return f"qkview_{qkview_data.get('id', 'unknown')}"
    
    def _get_generation_date_from_metadata(self, qkview_id, base_path="QKViews"):
        """
        Get generation date from existing metadata.json file (from api_data.generation_date)
        
        Args:
            qkview_id (str): QKView ID
            base_path (str): Base directory path
            
        Returns:
            str: Formatted date string (MM-DD-YYYY_HH:MM:SS) or empty string if not found
        """
        import json
        
        # Use the new directory finder to locate the correct directory
        qkview_dir, is_hostname_based = find_qkview_directory(qkview_id, base_path)
        
        if not qkview_dir:
            return ""
        
        metadata_file = os.path.join(qkview_dir, "metadata.json")
        
        if not os.path.exists(metadata_file):
            return ""
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Look for generation_date in api_data (Unix timestamp in milliseconds)
            if 'api_data' in metadata and isinstance(metadata['api_data'], dict):
                api_data = metadata['api_data']
                
                if 'generation_date' in api_data and api_data['generation_date']:
                    try:
                        # Convert from milliseconds to seconds
                        timestamp_ms = int(api_data['generation_date'])
                        timestamp_s = timestamp_ms / 1000.0
                        dt = datetime.fromtimestamp(timestamp_s)
                        # Format as MM-DD-YYYY_HH:MM:SS
                        return dt.strftime("%m-%d-%Y_%H:%M:%S")
                    except (ValueError, TypeError, OSError) as e:
                        if hasattr(self, 'debug') and self.debug:
                            print(f"  DEBUG: Error parsing generation_date {api_data['generation_date']}: {e}")
                        return ""
            
            # Fallback to other date fields if generation_date not available
            return self._extract_creation_date_from_qkview_data(metadata.get('api_data', {}))
                
        except Exception as e:
            if hasattr(self, 'debug') and self.debug:
                print(f"  DEBUG: Error reading metadata for generation date: {e}")
        
        return ""
    
    def _extract_creation_date_from_qkview_data(self, qkview_data):
        """
        Extract creation date from QKView API response data (fallback method)
        
        Args:
            qkview_data (dict): QKView details from API
            
        Returns:
            str: Formatted date string or empty string if not found
        """
        if not qkview_data or not isinstance(qkview_data, dict):
            return ""
        
        # Look for generation_date first (Unix timestamp in milliseconds)
        if 'generation_date' in qkview_data and qkview_data['generation_date']:
            try:
                timestamp_ms = int(qkview_data['generation_date'])
                timestamp_s = timestamp_ms / 1000.0
                dt = datetime.fromtimestamp(timestamp_s)
                return dt.strftime("%m-%d-%Y_%H:%M:%S")
            except (ValueError, TypeError, OSError):
                pass
        
        # Look for other date fields in order of preference
        date_fields = [
            'created_date',
            'creation_date', 
            'upload_date',
            'uploaded_date',
            'date_created',
            'timestamp',
            'created_timestamp',
            'date'
        ]
        
        for field in date_fields:
            if field in qkview_data and qkview_data[field]:
                date_str = str(qkview_data[field])
                
                # Try to parse various date formats
                date_formats = [
                    "%Y-%m-%dT%H:%M:%S.%fZ",      # ISO format with microseconds
                    "%Y-%m-%dT%H:%M:%SZ",         # ISO format without microseconds
                    "%Y-%m-%dT%H:%M:%S",          # ISO format without Z
                    "%Y-%m-%d %H:%M:%S",          # Space-separated format
                    "%Y/%m/%d %H:%M:%S",          # Slash-separated format
                    "%m/%d/%Y %H:%M:%S",          # US format
                    "%d/%m/%Y %H:%M:%S",          # European format
                    "%Y-%m-%d",                   # Date only
                    "%m/%d/%Y",                   # US date only
                    "%d/%m/%Y"                    # European date only
                ]
                
                for fmt in date_formats:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        # Format as MM-DD-YYYY_HH:MM:SS
                        return dt.strftime("%m-%d-%Y_%H:%M:%S")
                    except ValueError:
                        continue
                
                # If no format matches, try to extract just date parts if it's a timestamp
                try:
                    # Handle Unix timestamps (if it's a number)
                    timestamp = float(date_str)
                    dt = datetime.fromtimestamp(timestamp)
                    return dt.strftime("%m-%d-%Y_%H:%M:%S")
                except (ValueError, TypeError):
                    pass
        
        return ""  # Return empty string if no valid date found
    
    def _generate_qkview_filename(self, qkview_data, qkview_id, base_path="QKViews"):
        """
        Generate appropriate filename for QKView based on hostname and generation date from metadata
        
        Args:
            qkview_data (dict): QKView details from API
            qkview_id (str): QKView ID
            base_path (str): Base directory path
            
        Returns:
            str: Generated filename
        """
        hostname = self._extract_hostname_from_qkview_data(qkview_data)
        
        # Get generation date from metadata first (preferred)
        date_str = self._get_generation_date_from_metadata(qkview_id, base_path)
        
        # Fallback to extracting from qkview_data if metadata doesn't have it
        if not date_str:
            date_str = self._extract_creation_date_from_qkview_data(qkview_data)
        
        # Build filename
        if date_str:
            filename = f"{hostname}_{date_str}.qkview"
        else:
            filename = f"{hostname}.qkview"
        
        return filename
    
    def _get_expected_file_size_from_metadata(self, qkview_id, base_path="QKViews"):
        """
        Get expected file size from existing metadata.json file
        
        Args:
            qkview_id (str): QKView ID
            base_path (str): Base directory path
            
        Returns:
            int: Expected file size in bytes, or None if not found
        """
        import json
        
        # Use the new directory finder to locate the correct directory
        qkview_dir, is_hostname_based = find_qkview_directory(qkview_id, base_path)
        
        if not qkview_dir:
            return None
        
        metadata_file = os.path.join(qkview_dir, "metadata.json")
        
        if not os.path.exists(metadata_file):
            return None
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Look for file_size in api_data
            if 'api_data' in metadata and isinstance(metadata['api_data'], dict):
                api_data = metadata['api_data']
                
                # Look for various file size fields
                size_fields = ['file_size', 'size', 'filesize', 'file_size_bytes', 'content_length']
                
                for field in size_fields:
                    if field in api_data and api_data[field]:
                        try:
                            return int(api_data[field])
                        except (ValueError, TypeError):
                            continue
                            
        except Exception as e:
            if hasattr(self, 'debug') and self.debug:
                print(f"  DEBUG: Error reading metadata for file size: {e}")
        
        return None
    
    def _validate_file_size(self, file_path, expected_size, tolerance_percent=5):
        """
        Validate downloaded file size against expected size
        
        Args:
            file_path (str): Path to downloaded file
            expected_size (int): Expected file size in bytes
            tolerance_percent (int): Acceptable difference percentage
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        if not os.path.exists(file_path) or expected_size is None:
            return True, "No validation needed"
        
        actual_size = os.path.getsize(file_path)
        
        # Calculate percentage difference
        if expected_size == 0:
            return actual_size == 0, "Expected zero-size file"
        
        diff_percent = abs(actual_size - expected_size) / expected_size * 100
        
        actual_mb = actual_size / (1024 * 1024)
        expected_mb = expected_size / (1024 * 1024)
        
        if diff_percent <= tolerance_percent:
            return True, f"File size validated ({actual_mb:.1f}MB matches expected {expected_mb:.1f}MB)"
        else:
            return False, f"File size mismatch: got {actual_mb:.1f}MB, expected {expected_mb:.1f}MB (difference: {diff_percent:.1f}%)"
    
    def _should_download_qkview(self, file_path, qkview_id, base_path="QKViews"):
        """
        Check if QKView file should be downloaded based on existence, size, and metadata validation
        
        Args:
            file_path (str): Path to the QKView file
            qkview_id (str): QKView ID for metadata lookup
            base_path (str): Base directory path
            
        Returns:
            tuple: (should_download: bool, reason: str)
        """
        if not os.path.exists(file_path):
            return True, "File does not exist"
        
        # Check file size (10MB = 10 * 1024 * 1024 bytes)
        file_size = os.path.getsize(file_path)
        min_size_bytes = 10 * 1024 * 1024  # 10MB
        
        if file_size < min_size_bytes:
            size_mb = file_size / (1024 * 1024)
            return True, f"File exists but is too small ({size_mb:.1f}MB < 10MB)"
        
        # Check against expected size from metadata if available
        expected_size = self._get_expected_file_size_from_metadata(qkview_id, base_path)
        if expected_size:
            size_valid, size_message = self._validate_file_size(file_path, expected_size, tolerance_percent=10)
            if not size_valid:
                actual_mb = file_size / (1024 * 1024)
                expected_mb = expected_size / (1024 * 1024)
                return True, f"File size mismatch: got {actual_mb:.1f}MB, expected {expected_mb:.1f}MB"
        
        # File exists and is adequate size
        size_mb = file_size / (1024 * 1024)
        return False, f"File exists and appears to be adequate size ({size_mb:.1f}MB)"

    def download_qkview_file(self, qkview_id, qkview_data, base_path="QKViews"):
        """
        Download QKView file and save it with proper naming to hostname-based directory
        
        Args:
            qkview_id (str): QKView ID
            qkview_data (dict): QKView details from API (for filename generation)
            base_path (str): Base directory path
            
        Returns:
            dict: Download result with filename and status
        """
        # Find the correct directory (hostname-based if available)
        qkview_dir, is_hostname_based = find_qkview_directory(qkview_id, base_path)
        
        if not qkview_dir:
            print(f"  ✗ Could not find directory for QKView {qkview_id}")
            return {'success': False, 'error': 'Directory not found'}
        
        # Generate filename using generation date from metadata
        filename = self._generate_qkview_filename(qkview_data, qkview_id, base_path)
        
        # Check if file already exists and determine if we should download
        file_path = os.path.join(qkview_dir, filename)
        
        should_download, reason = self._should_download_qkview(file_path, qkview_id, base_path)
        
        if not should_download:
            print(f"  QKView file skipped: {filename} - {reason}")
            return {
                'success': True, 
                'filename': filename, 
                'file_path': file_path, 
                'skipped': True,
                'reason': reason
            }
        
        print(f"  QKView download needed: {reason}")
        
        # Download the file content
        file_content = self._download_qkview_file(qkview_id)
        if not file_content:
            return {'success': False, 'error': 'Failed to download QKView file'}
        
        # Create directory if it doesn't exist (shouldn't be needed, but safety check)
        os.makedirs(qkview_dir, exist_ok=True)
        
        # Save the file
        try:
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            file_size = len(file_content)
            file_size_mb = file_size / (1024 * 1024)
            
            # Validate file size against metadata expectation
            expected_size = self._get_expected_file_size_from_metadata(qkview_id, base_path)
            size_valid, size_message = self._validate_file_size(file_path, expected_size)
            
            if size_valid:
                print(f"  ✓ Successfully saved QKView file: {filename} ({file_size_mb:.1f}MB)")
                if expected_size and self.debug:
                    print(f"  DEBUG: {size_message}")
            else:
                print(f"  ✓ QKView file saved: {filename} ({file_size_mb:.1f}MB)")
                print(f"  ▲ WARNING: {size_message}")
                print(f"  This could indicate a download issue or metadata inconsistency")
            
            # Update metadata
            hostname = self._extract_hostname_from_qkview_data(qkview_data)
            generation_date = self._get_generation_date_from_metadata(qkview_id, base_path)
            if not generation_date:
                generation_date = self._extract_creation_date_from_qkview_data(qkview_data)
            
            # Include size validation info in metadata
            metadata_update = {
                'qkview_file': {
                    'filename': filename,
                    'file_path': file_path,
                    'file_size': file_size,
                    'downloaded_at': datetime.now().isoformat(),
                    'hostname': hostname,
                    'generation_date': generation_date,
                    'size_validation': {
                        'actual_size': file_size,
                        'expected_size': expected_size,
                        'size_valid': size_valid,
                        'validation_message': size_message
                    }
                },
                'processing_status': {
                    'qkview_downloaded': True
                }
            }
            
            update_qkview_metadata(qkview_id, metadata_update, base_path)
            
            return {
                'success': True,
                'filename': filename,
                'file_path': file_path,
                'file_size': file_size,
                'hostname': hostname,
                'generation_date': generation_date,
                'size_validation': {
                    'valid': size_valid,
                    'message': size_message,
                    'expected_size': expected_size
                }
            }
            
        except Exception as e:
            print(f"  ✗ Failed to save QKView file: {e}")
            return {'success': False, 'error': f'Failed to save file: {e}'}
    
    def check_qkview_file_exists(self, qkview_id, base_path="QKViews"):
        """
        Check if QKView file already exists locally
        
        Args:
            qkview_id (str): QKView ID
            base_path (str): Base directory path
            
        Returns:
            dict: Information about existing file or None if not found
        """
        # Find the correct directory (hostname-based if available)
        qkview_dir, is_hostname_based = find_qkview_directory(qkview_id, base_path)
        
        if not qkview_dir or not os.path.exists(qkview_dir):
            return None
        
        # Look for .qkview files in the directory
        for filename in os.listdir(qkview_dir):
            if filename.endswith('.qkview'):
                file_path = os.path.join(qkview_dir, filename)
                file_size = os.path.getsize(file_path)
                file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                return {
                    'filename': filename,
                    'file_path': file_path,
                    'file_size': file_size,
                    'modified_date': file_modified.isoformat()
                }
        
        return None


if __name__ == "__main__":
    # Test the QKView download module
    from ihealth_auth import F5iHealthAuth, load_credentials_from_files
    
    client_id, client_secret = load_credentials_from_files()
    if not client_id or not client_secret:
        print("No credentials found in files")
        exit(1)
    
    auth = F5iHealthAuth(client_id, client_secret)
    if auth.authenticate():
        downloader = F5iHealthQKViewDownload(auth)
        
        # Test with a sample QKView ID
        test_qkview_id = "24821984"  # Replace with actual ID
        
        print(f"Testing QKView download for {test_qkview_id}")
        
        # Check if file already exists
        existing = downloader.check_qkview_file_exists(test_qkview_id)
        if existing:
            print(f"QKView file already exists: {existing['filename']}")
        else:
            # Get QKView details first (needed for filename generation)
            from ihealth_utils import F5iHealthClient
            client = F5iHealthClient(auth)
            qkview_details = client.get_qkview_details(test_qkview_id)
            
            if qkview_details:
                # Download the QKView file
                result = downloader.download_qkview_file(test_qkview_id, qkview_details)
                print(f"Download result: {result}")
            else:
                print("Could not get QKView details")
    else:
        print("Authentication failed")


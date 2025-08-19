#!/usr/bin/env python3
"""
F5 iHealth Diagnostics Module

Handles comprehensive diagnostic operations including downloading PDF/CSV reports
for issues found on devices.
"""

import json
import os
import time
from ihealth_utils import F5iHealthClient
from qkview_directory_utils import save_data_to_qkview, update_qkview_metadata


class F5iHealthDiagnostics(F5iHealthClient):
    """F5 iHealth Diagnostics operations"""
    
    def __init__(self, auth_handler):
        super().__init__(auth_handler)
        self.diagnostic_sets = ['hit', 'miss', 'all']  # Different diagnostic sets available
        self.diagnostic_formats = ['json', 'xml', 'pdf', 'csv']
    
    def _make_diagnostic_request(self, qkview_id, diagnostic_set=None, format_type='json'):
        """
        Make a diagnostic request with specific parameters
        
        Args:
            qkview_id (str): QKView ID
            diagnostic_set (str): 'hit', 'miss', 'all', or None for all
            format_type (str): 'json', 'xml', 'pdf', 'csv'
            
        Returns:
            Response data or None if failed
        """
        # Build endpoint
        endpoint = f"/qkviews/{qkview_id}/diagnostics"
        
        # Add format extension if not json
        if format_type != 'json':
            endpoint += f".{format_type}"
        
        # Build query parameters
        params = {}
        if diagnostic_set and diagnostic_set != 'all':
            params['set'] = diagnostic_set
        
        # Make the request
        if format_type in ['pdf', 'csv']:
            # For binary/text downloads, we need to handle differently
            return self._download_diagnostic_file(endpoint, params, format_type)
        else:
            # For JSON/XML, use standard request
            return self._make_request("GET", endpoint, params=params)
    
    def _download_diagnostic_file(self, endpoint, params, format_type):
        """
        Download diagnostic file (PDF/CSV) and return content
        
        Args:
            endpoint (str): API endpoint
            params (dict): Query parameters
            format_type (str): File format (pdf/csv)
            
        Returns:
            bytes: File content or None if failed
        """
        # Ensure we have a valid token
        if not self.auth.refresh_token_if_needed():
            print("Failed to authenticate or refresh token")
            return None
            
        session = self.auth.get_authenticated_session()
        if not session:
            print("No authenticated session available")
            return None
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Set appropriate headers for file download
        headers = {
            'Accept': f'application/vnd.f5.ihealth.api+{format_type}'
        }
        
        try:
            print(f"Downloading {format_type.upper()} diagnostic file...")
            response = session.get(url, params=params, headers=headers)
            
            # Handle 202 (processing) responses
            if response.status_code == 202:
                print("Diagnostics are being processed, waiting...")
                time.sleep(10)  # Wait 10 seconds as recommended by API docs
                response = session.get(url, params=params, headers=headers)
            
            response.raise_for_status()
            return response.content
            
        except Exception as e:
            print(f"Failed to download {format_type} diagnostic file: {e}")
            return None
    
    def get_all_diagnostics(self, qkview_id, diagnostic_set='hit'):
        """
        Get all diagnostic results for a QKView in JSON format
        
        Args:
            qkview_id (str): QKView ID
            diagnostic_set (str): 'hit', 'miss', or 'all'
            
        Returns:
            dict: Diagnostic data
        """
        return self._make_diagnostic_request(qkview_id, diagnostic_set, 'json')
    
    def get_diagnostic_summary(self, qkview_id):
        """
        Get a summary of diagnostics for a QKView
        
        Args:
            qkview_id (str): QKView ID
            
        Returns:
            dict: Summary information
        """
        diagnostics = self.get_all_diagnostics(qkview_id, 'hit')
        
        if not diagnostics:
            return None
        
        # Extract summary information
        summary = {
            'qkview_id': qkview_id,
            'total_hits': 0,
            'critical_count': 0,
            'high_count': 0,
            'medium_count': 0,
            'low_count': 0,
            'info_count': 0,
            'issues': []
        }
        
        # Parse diagnostics to count issues by severity
        # Note: The exact structure depends on the API response format
        if isinstance(diagnostics, dict):
            # Extract issues from the response structure
            # This might need adjustment based on actual API response
            if 'diagnostics' in diagnostics:
                issues = diagnostics['diagnostics']
            elif 'results' in diagnostics:
                issues = diagnostics['results']
            else:
                issues = [diagnostics]
            
            for issue in issues:
                if isinstance(issue, dict):
                    severity = issue.get('h_importance', 'unknown').lower()
                    summary['total_hits'] += 1
                    
                    if 'critical' in severity:
                        summary['critical_count'] += 1
                    elif 'high' in severity:
                        summary['high_count'] += 1
                    elif 'medium' in severity:
                        summary['medium_count'] += 1
                    elif 'low' in severity:
                        summary['low_count'] += 1
                    else:
                        summary['info_count'] += 1
                    
                    # Add issue summary
                    summary['issues'].append({
                        'name': issue.get('h_name', 'Unknown'),
                        'severity': severity,
                        'summary': issue.get('h_summary', 'No summary available'),
                        'header': issue.get('h_header', 'No header available')
                    })
        
        return summary
    
    def get_hostname_from_qkview(self, qkview_id):
        """
        Extract hostname from QKView details for file naming
        
        Args:
            qkview_id (str): QKView ID
            
        Returns:
            str: Hostname or QKView ID if hostname not found
        """
        try:
            qkview_details = self.get_qkview_details(qkview_id)
            
            if qkview_details:
                # Look for hostname in various possible fields
                hostname_fields = ['hostname', 'device_name', 'name', 'filename']
                
                for field in hostname_fields:
                    if field in qkview_details and qkview_details[field]:
                        hostname = qkview_details[field]
                        # Clean up hostname (remove .qkview extension, etc.)
                        if hostname.endswith('.qkview'):
                            hostname = hostname[:-7]
                        return hostname
            
            # Fallback to QKView ID if hostname not found
            return f"qkview_{qkview_id}"
            
        except Exception as e:
            print(f"Failed to get hostname for QKView {qkview_id}: {e}")
            return f"qkview_{qkview_id}"
    
    def download_diagnostic_reports(self, qkview_id, base_path="QKViews"):
        """
        Download diagnostic reports (PDF and CSV) for issues found on the device
        
        Args:
            qkview_id (str): QKView ID
            base_path (str): Base directory path
            
        Returns:
            dict: Summary of downloaded files
        """
        print(f"Downloading diagnostic reports for QKView {qkview_id}...")
        
        # Get hostname for file naming
        hostname = self.get_hostname_from_qkview(qkview_id)
        
        downloaded_files = {
            'pdf': None,
            'csv': None,
            'json_hit': None
        }
        
        # Download diagnostic reports (hit diagnostics only - actual issues found)
        print("Downloading diagnostic reports...")
        
        # PDF (hit diagnostics - issues found)
        pdf_content = self._make_diagnostic_request(qkview_id, 'hit', 'pdf')
        if pdf_content:
            filename = f"{hostname}.pdf"
            file_path = os.path.join(base_path, str(qkview_id), "Diagnostics", filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(pdf_content)
            downloaded_files['pdf'] = filename
            print(f"✓ Downloaded {filename}")
        
        # CSV (hit diagnostics - issues found)
        csv_content = self._make_diagnostic_request(qkview_id, 'hit', 'csv')
        if csv_content:
            filename = f"{hostname}.csv"
            file_path = os.path.join(base_path, str(qkview_id), "Diagnostics", filename)
            with open(file_path, 'wb') as f:
                f.write(csv_content)
            downloaded_files['csv'] = filename
            print(f"✓ Downloaded {filename}")
        
        # Download JSON data for programmatic access
        print("Downloading JSON diagnostic data...")
        
        # Hit diagnostics JSON (issues found)
        json_hit = self.get_all_diagnostics(qkview_id, 'hit')
        if json_hit:
            filename = "diagnostics_hit.json"
            save_data_to_qkview(qkview_id, "Diagnostics", filename, json_hit, base_path)
            downloaded_files['json_hit'] = filename
            print(f"✓ Saved {filename}")
        
        # Generate and save summary
        summary = self.get_diagnostic_summary(qkview_id)
        if summary:
            filename = "diagnostic_summary.json"
            save_data_to_qkview(qkview_id, "Diagnostics", filename, summary, base_path)
            print(f"✓ Generated {filename}")
        
        # Update metadata
        update_qkview_metadata(qkview_id, {
            'processing_status': {'diagnostics': True},
            'diagnostic_files': downloaded_files,
            'hostname': hostname
        }, base_path)
        
        print(f"✓ Completed diagnostic downloads for {hostname}")
        return downloaded_files
    
    def get_critical_issues(self, qkview_id):
        """
        Get only critical diagnostic issues
        
        Args:
            qkview_id (str): QKView ID
            
        Returns:
            list: Critical issues
        """
        diagnostics = self.get_all_diagnostics(qkview_id, 'hit')
        critical_issues = []
        
        if diagnostics and isinstance(diagnostics, dict):
            # Extract issues and filter for critical ones
            issues = []
            if 'diagnostics' in diagnostics:
                issues = diagnostics['diagnostics']
            elif 'results' in diagnostics:
                issues = diagnostics['results']
            
            for issue in issues:
                if isinstance(issue, dict):
                    importance = issue.get('h_importance', '').lower()
                    if 'critical' in importance or 'high' in importance:
                        critical_issues.append(issue)
        
        return critical_issues
    
    def get_recommendations(self, qkview_id):
        """
        Get recommendations from diagnostics
        
        Args:
            qkview_id (str): QKView ID
            
        Returns:
            list: Recommendations
        """
        diagnostics = self.get_all_diagnostics(qkview_id, 'hit')
        recommendations = []
        
        if diagnostics and isinstance(diagnostics, dict):
            issues = []
            if 'diagnostics' in diagnostics:
                issues = diagnostics['diagnostics']
            elif 'results' in diagnostics:
                issues = diagnostics['results']
            
            for issue in issues:
                if isinstance(issue, dict) and 'h_action' in issue:
                    recommendations.append({
                        'issue': issue.get('h_name', 'Unknown'),
                        'action': issue.get('h_action', 'No action specified'),
                        'summary': issue.get('h_summary', ''),
                        'solutions': issue.get('h_sols', [])
                    })
        
        return recommendations


if __name__ == "__main__":
    # Test the diagnostics module
    from ihealth_auth import F5iHealthAuth, load_credentials_from_files
    
    client_id, client_secret = load_credentials_from_files()
    if not client_id or not client_secret:
        print("No credentials found in files")
        exit(1)
    
    auth = F5iHealthAuth(client_id, client_secret)
    if auth.authenticate():
        diagnostics = F5iHealthDiagnostics(auth)
        
        # Test with a sample QKView ID
        test_qkview_id = "24821984"  # Replace with actual ID
        
        print(f"Testing diagnostics for QKView {test_qkview_id}")
        
        # Download all diagnostic reports
        files = diagnostics.download_diagnostic_reports(test_qkview_id)
        print(f"Downloaded files: {files}")
        
        # Get summary
        summary = diagnostics.get_diagnostic_summary(test_qkview_id)
        if summary:
            print(f"Total issues: {summary['total_hits']}")
            print(f"Critical: {summary['critical_count']}, High: {summary['high_count']}")
    else:
        print("Authentication failed")


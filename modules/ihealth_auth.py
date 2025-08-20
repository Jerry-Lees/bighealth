#!/usr/bin/env python3
"""
F5 iHealth API Authentication Module

Handles OAuth2 authentication with the F5 iHealth API.
"""

import requests
import json
import base64
import os
from datetime import datetime, timedelta

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
NC = '\033[0m'  # No Color


class F5iHealthAuth:
    """F5 iHealth API Authentication handler using OAuth2 Client Credentials flow"""
    
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = "https://identity.account.f5.com/oauth2/ausp95ykc80HOU7SQ357/v1/token"
        self.access_token = None
        self.token_expires_at = None
        self.session = None
        
    def authenticate(self):
        """Authenticate and get access token"""
        try:
            # Create base64 encoded credentials
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                "Accept": "application/json",
                "Authorization": f"Basic {encoded_credentials}",
                "Cache-Control": "no-cache",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "grant_type": "client_credentials",
                "scope": "ihealth"
            }
            
            response = requests.post(self.auth_url, headers=headers, data=data)
            response.raise_for_status()
            
            auth_response = response.json()
            self.access_token = auth_response.get("access_token")
            expires_in = auth_response.get("expires_in", 1800)  # Default 30 minutes
            
            if self.access_token:
                # Calculate token expiration time
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # 1 min buffer
                
                # Create authenticated session
                self.session = requests.Session()
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json"
                })
                
                return True
            else:
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Authentication failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    print(f"Error details: {json.dumps(error_details, indent=2)}")
                except:
                    print(f"Response text: {e.response.text}")
            return False
        except json.JSONDecodeError as e:
            print(f"Authentication failed: Invalid JSON response - {e}")
            return False
    
    def is_token_valid(self):
        """Check if the current access token is still valid"""
        if not self.access_token or not self.token_expires_at:
            return False
        return datetime.now() < self.token_expires_at
    
    def get_authenticated_session(self):
        """Get an authenticated requests session"""
        if not self.is_token_valid():
            print("Token expired or invalid. Please re-authenticate.")
            return None
        return self.session
    
    def refresh_token_if_needed(self):
        """Refresh the access token if it's close to expiring"""
        if self.is_token_valid():
            return True
        
        print("Token expired, re-authenticating...")
        return self.authenticate()


def load_credentials_from_files(client_id_file="credentials/cid", client_secret_file="credentials/cs"):
    """Load credentials from local files"""
    try:
        if os.path.exists(client_id_file) and os.path.exists(client_secret_file):
            with open(client_id_file, 'r') as f:
                client_id = f.read().strip()
            with open(client_secret_file, 'r') as f:
                client_secret = f.read().strip()
            return client_id, client_secret
        else:
            return None, None
    except Exception as e:
        print(f"Error loading credentials from files: {e}")
        return None, None


def get_credentials_interactive():
    """Get credentials interactively from user input"""
    import getpass
    
    client_id = input("Enter F5 iHealth API Client ID: ")
    client_secret = getpass.getpass("Enter F5 iHealth API Client Secret: ")
    
    return client_id, client_secret


if __name__ == "__main__":
    # Test authentication
    client_id, client_secret = load_credentials_from_files()
    
    if not client_id or not client_secret:
        client_id, client_secret = get_credentials_interactive()
    
    auth = F5iHealthAuth(client_id, client_secret)
    if auth.authenticate():
        print(f"{GREEN}✓{NC} Authentication successful!")
        print(f"{GREEN}✓{NC} Token expires at: {auth.token_expires_at}")
    else:
        print(f"{RED}✗{NC} Authentication failed!")


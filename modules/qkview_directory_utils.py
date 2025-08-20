#!/usr/bin/env python3
"""
QKView Directory Structure Utilities

Functions for creating and managing the standardized QKView directory structure.
"""

import os
import json
from datetime import datetime
from pathlib import Path

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
NC = '\033[0m'  # No Color


def create_qkview_directory_structure(qkview_id, base_path="QKViews"):
    """
    Create standardized directory structure for a QKView
    
    Args:
        qkview_id (str): QKView ID
        base_path (str): Base directory path (default: "QKViews")
        
    Returns:
        str: Path to the created QKView directory
    """
    # Convert to Path object for easier manipulation
    base_dir = Path(base_path)
    qkview_dir = base_dir / str(qkview_id)
    
    # Create base QKViews directory if it doesn't exist
    base_dir.mkdir(exist_ok=True)
    
    # Create QKView ID directory
    qkview_dir.mkdir(exist_ok=True)
    
    # Define all subdirectories to create
    subdirectories = [
        "Diagnostics",
        "LTM", 
        "GTM",
        "APM",
        "ASM",
        "iRules",
        "System",
        "Configuration",
        "Commands",
        "Graphs", 
        "Logs",
        "Logs/search_results",
        "Docs"
    ]
    
    # Create all subdirectories
    for subdir in subdirectories:
        (qkview_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    print(f"{GREEN}✓{NC} Created directory structure for QKView {qkview_id}")
    return str(qkview_dir)


def create_qkview_metadata(qkview_id, qkview_data=None, base_path="QKViews"):
    """
    Create metadata.json file for a QKView with basic information
    
    Args:
        qkview_id (str): QKView ID
        qkview_data (dict): Optional QKView data from API
        base_path (str): Base directory path
    """
    qkview_dir = Path(base_path) / str(qkview_id)
    metadata_file = qkview_dir / "metadata.json"
    
    # Create basic metadata
    metadata = {
        "qkview_id": qkview_id,
        "created_timestamp": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "api_data": qkview_data if qkview_data else {},
        "processing_status": {
            "diagnostics": False,
            "configuration": False,
            "logs": False,
            "system_info": False
        },
        "file_counts": {
            "diagnostics": 0,
            "configuration_files": 0,
            "log_files": 0,
            "irules": 0
        }
    }
    
    # Write metadata to file
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"{GREEN}✓{NC} Created metadata.json for QKView {qkview_id}")


def extract_hostname_from_qkview_data(qkview_data):
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
        'description',       # Sometimes contains hostname
        'file_name',         # Original filename might have hostname
        'filename'           # Alternative filename field
    ]
    
    for field in hostname_fields:
        if field in qkview_data and qkview_data[field]:
            hostname = str(qkview_data[field])
            
            # Clean up the hostname
            # Remove .qkview extension if present
            if hostname.lower().endswith('.qkview'):
                hostname = hostname[:-7]
            
            # If it's a filename like "hostname_date.qkview", extract just hostname
            if '_' in hostname and any(char.isdigit() for char in hostname.split('_')[-1]):
                hostname = hostname.split('_')[0]
            
            # Remove common file extensions
            for ext in ['.tar', '.gz', '.tgz', '.zip']:
                if hostname.lower().endswith(ext):
                    hostname = hostname[:-(len(ext))]
            
            # Validate it looks like a hostname (basic check)
            if hostname and '.' in hostname and hostname.replace('.', '').replace('-', '').replace('_', '').isalnum():
                return hostname
    
    # Fallback to QKView ID if no hostname found
    qkview_id = qkview_data.get('id', 'unknown')
    return f"qkview_{qkview_id}"


def get_qkview_directory_by_hostname(hostname, base_path="QKViews"):
    """
    Get the directory path for a QKView using hostname
    
    Args:
        hostname (str): Device hostname
        base_path (str): Base directory path
        
    Returns:
        str: Path to QKView directory
    """
    return str(Path(base_path) / hostname)


def create_qkview_directory_structure_by_hostname(hostname, base_path="QKViews"):
    """
    Create standardized directory structure for a QKView using hostname
    
    Args:
        hostname (str): Device hostname
        base_path (str): Base directory path (default: "QKViews")
        
    Returns:
        str: Path to the created QKView directory
    """
    # Convert to Path object for easier manipulation
    base_dir = Path(base_path)
    qkview_dir = base_dir / hostname
    
    # Create base QKViews directory if it doesn't exist
    base_dir.mkdir(exist_ok=True)
    
    # Create hostname directory
    qkview_dir.mkdir(exist_ok=True)
    
    # Define all subdirectories to create
    subdirectories = [
        "Diagnostics",
        "LTM", 
        "GTM",
        "APM",
        "ASM",
        "iRules",
        "System",
        "Configuration",
        "Commands",
        "Graphs", 
        "Logs",
        "Logs/search_results",
        "Docs"
    ]
    
    # Create all subdirectories
    for subdir in subdirectories:
        (qkview_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    print(f"{GREEN}✓{NC} Created directory structure for {hostname}")
    return str(qkview_dir)


def create_metadata_first(qkview_id, qkview_data, base_path="QKViews"):
    """
    Create metadata.json file FIRST with complete QKView information
    This should be called immediately after getting QKView details from API
    
    Args:
        qkview_id (str): QKView ID
        qkview_data (dict): Complete QKView data from API
        base_path (str): Base directory path
        
    Returns:
        tuple: (hostname, qkview_dir_path)
    """
    if not qkview_data:
        raise ValueError("QKView data is required to create metadata")
    
    # Extract hostname from API data
    hostname = extract_hostname_from_qkview_data(qkview_data)
    
    # Create hostname-based directory structure
    qkview_dir = create_qkview_directory_structure_by_hostname(hostname, base_path)
    
    # Create comprehensive metadata
    metadata = {
        "qkview_id": qkview_id,
        "hostname": hostname,
        "created_timestamp": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "api_data": qkview_data,
        "processing_status": {
            "metadata_created": True,
            "diagnostics": False,
            "qkview_downloaded": False,
            "configuration": False,
            "logs": False,
            "system_info": False
        },
        "file_counts": {
            "diagnostics": 0,
            "configuration_files": 0,
            "log_files": 0,
            "irules": 0
        },
        "directory_info": {
            "path": qkview_dir,
            "created_with_hostname": True,
            "hostname_extracted_from": _find_hostname_source(qkview_data)
        }
    }
    
    # Save metadata to hostname-based directory
    metadata_file = Path(qkview_dir) / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"{GREEN}✓{NC} Created metadata.json for {hostname} (QKView {qkview_id})")
    
    return hostname, qkview_dir


def _find_hostname_source(qkview_data):
    """
    Helper function to determine which field the hostname was extracted from
    Useful for debugging and metadata tracking
    """
    hostname_fields = ['hostname', 'device_name', 'name', 'description', 'file_name', 'filename']
    
    for field in hostname_fields:
        if field in qkview_data and qkview_data[field]:
            return field
    
    return "fallback_to_qkview_id"


def find_qkview_directory(qkview_id, base_path="QKViews"):
    """
    Find existing QKView directory (supports both hostname and ID-based directories)
    
    Args:
        qkview_id (str): QKView ID to find
        base_path (str): Base directory path
        
    Returns:
        tuple: (directory_path, is_hostname_based) or (None, False) if not found
    """
    base_dir = Path(base_path)
    
    if not base_dir.exists():
        return None, False
    
    # Search all subdirectories for metadata.json files that match our QKView ID
    for item in base_dir.iterdir():
        if item.is_dir():
            metadata_file = item / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    # Check if this directory contains our QKView ID
                    if metadata.get('qkview_id') == qkview_id:
                        is_hostname_based = metadata.get('directory_info', {}).get('created_with_hostname', False)
                        return str(item), is_hostname_based
                except:
                    # If metadata is corrupted, skip this directory
                    continue
    
    return None, False


def update_qkview_metadata(qkview_id, updates, base_path="QKViews"):
    """
    Update existing metadata.json file (works with both hostname and ID-based directories)
    
    Args:
        qkview_id (str): QKView ID
        updates (dict): Dictionary of updates to apply
        base_path (str): Base directory path
    """
    # Find the directory first
    qkview_dir, is_hostname_based = find_qkview_directory(qkview_id, base_path)
    
    if not qkview_dir:
        # Fallback to legacy ID-based lookup
        metadata_file = Path(base_path) / str(qkview_id) / "metadata.json"
        if metadata_file.exists():
            qkview_dir = str(Path(base_path) / str(qkview_id))
        else:
            print(f"{YELLOW}⚠{NC} Warning: Could not find directory for QKView {qkview_id}")
            return
    
    metadata_file = Path(qkview_dir) / "metadata.json"
    
    if not metadata_file.exists():
        print(f"{YELLOW}⚠{NC} Warning: metadata.json not found in {qkview_dir}")
        return
    
    # Read existing metadata
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    # Apply updates (deep merge for nested dictionaries)
    def deep_merge(dict1, dict2):
        for key, value in dict2.items():
            if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
                deep_merge(dict1[key], value)
            else:
                dict1[key] = value
    
    deep_merge(metadata, updates)
    metadata["last_updated"] = datetime.now().isoformat()
    
    # Write back to file
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)


def save_data_to_qkview(qkview_id, category, filename, data, base_path="QKViews"):
    """
    Save data to appropriate QKView subdirectory (works with both directory types)
    
    Args:
        qkview_id (str): QKView ID
        category (str): Category subdirectory (e.g., "Diagnostics", "LTM")
        filename (str): Filename to save
        data: Data to save (dict for JSON, str for text)
        base_path (str): Base directory path
    """
    # Find the directory first
    qkview_dir, is_hostname_based = find_qkview_directory(qkview_id, base_path)
    
    if not qkview_dir:
        # Fallback to legacy ID-based lookup
        legacy_dir = Path(base_path) / str(qkview_id)
        if legacy_dir.exists():
            qkview_dir = str(legacy_dir)
        else:
            print(f"{YELLOW}⚠{NC} Warning: Could not find directory for QKView {qkview_id}")
            return None
    
    category_dir = Path(qkview_dir) / category
    
    # Ensure directory exists
    category_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = category_dir / filename
    
    # Save data based on type
    if isinstance(data, (dict, list)):
        # Save as JSON
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        # Save as text
        with open(file_path, 'w') as f:
            f.write(str(data))
    
    hostname = Path(qkview_dir).name
    print(f"{GREEN}✓{NC} Saved {filename} to {category} for {hostname}")
    return str(file_path)


def get_qkview_directory(qkview_id, base_path="QKViews"):
    """
    Get the directory path for a QKView (legacy function for backward compatibility)
    
    Args:
        qkview_id (str): QKView ID
        base_path (str): Base directory path
        
    Returns:
        str: Path to QKView directory
    """
    # Try to find using the new method first
    qkview_dir, is_hostname_based = find_qkview_directory(qkview_id, base_path)
    if qkview_dir:
        return qkview_dir
    
    # Fallback to legacy ID-based path
    return str(Path(base_path) / str(qkview_id))


def list_qkview_directories(base_path="QKViews"):
    """
    List all QKView directories (both hostname and ID-based)
    
    Args:
        base_path (str): Base directory path
        
    Returns:
        list: List of tuples (directory_name, qkview_id, is_hostname_based)
    """
    base_dir = Path(base_path)
    
    if not base_dir.exists():
        return []
    
    qkview_dirs = []
    for item in base_dir.iterdir():
        if item.is_dir():
            metadata_file = item / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    qkview_id = metadata.get('qkview_id', 'unknown')
                    is_hostname_based = metadata.get('directory_info', {}).get('created_with_hostname', False)
                    qkview_dirs.append((item.name, qkview_id, is_hostname_based))
                except:
                    # If metadata is corrupted, try to infer from directory name
                    if item.name.isdigit():
                        qkview_dirs.append((item.name, item.name, False))
            else:
                # Directory without metadata - check if it's numeric (legacy)
                if item.name.isdigit():
                    qkview_dirs.append((item.name, item.name, False))
    
    return sorted(qkview_dirs)


def create_readme_for_qkview(qkview_id, base_path="QKViews"):
    """
    Create a README.md file in the Docs subdirectory explaining the structure
    
    Args:
        qkview_id (str): QKView ID
        base_path (str): Base directory path
    """
    # Find the directory first
    qkview_dir, is_hostname_based = find_qkview_directory(qkview_id, base_path)
    
    if not qkview_dir:
        # Fallback to legacy ID-based lookup
        legacy_dir = Path(base_path) / str(qkview_id)
        if legacy_dir.exists():
            qkview_dir = str(legacy_dir)
            is_hostname_based = False
        else:
            print(f"{YELLOW}⚠{NC} Warning: Could not find directory for QKView {qkview_id}")
            return
    
    docs_dir = Path(qkview_dir) / "Docs"
    readme_file = docs_dir / "README.md"
    
    hostname = Path(qkview_dir).name
    
    readme_content = f"""# QKView {qkview_id} Analysis - {hostname}

This directory contains extracted and analyzed data from F5 iHealth QKView {qkview_id}.

## Device Information
- **Hostname**: {hostname}
- **QKView ID**: {qkview_id}
- **Directory Type**: {'Hostname-based' if is_hostname_based else 'Legacy ID-based'}

## Directory Structure

- **Diagnostics/** - Health checks, issues, and recommendations
- **LTM/** - Local Traffic Manager configuration and data
- **GTM/** - Global Traffic Manager configuration and data  
- **APM/** - Access Policy Manager configuration and data
- **ASM/** - Application Security Manager configuration and data
- **iRules/** - iRule scripts and analysis
- **System/** - Hardware, network, and platform information
- **Configuration/** - Configuration files and analysis
- **Logs/** - Log files and search results
- **Docs/** - Documentation and reports

## Files

### Metadata
- `metadata.json` - QKView processing metadata and status

### Common File Types
- `.json` - Structured data from API responses
- `.conf` - Configuration files
- `.tcl` - iRule scripts
- `.log` - Log files
- `.html` - Analysis reports
- `.pdf` - Executive summaries

## Generated

This structure was automatically created by the BigHealth F5 iHealth API tool.
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open(readme_file, 'w') as f:
        f.write(readme_content)
    
    print(f"{GREEN}✓{NC} Created README.md for {hostname}")


def initialize_qkview_processing(qkview_id, qkview_data=None, base_path="QKViews"):
    """
    Initialize complete QKView processing structure (legacy function)
    
    Args:
        qkview_id (str): QKView ID
        qkview_data (dict): Optional QKView data from API
        base_path (str): Base directory path
        
    Returns:
        str: Path to created QKView directory
    """
    # Create directory structure
    qkview_dir = create_qkview_directory_structure(qkview_id, base_path)
    
    # Create metadata
    create_qkview_metadata(qkview_id, qkview_data, base_path)
    
    # Create README
    create_readme_for_qkview(qkview_id, base_path)
    
    print(f"{GREEN}✓{NC} Initialized QKView {qkview_id} processing structure")
    return qkview_dir


def initialize_qkview_processing_metadata_first(qkview_id, qkview_data, base_path="QKViews"):
    """
    Initialize complete QKView processing structure with metadata-first approach
    
    Args:
        qkview_id (str): QKView ID
        qkview_data (dict): Complete QKView data from API (REQUIRED)
        base_path (str): Base directory path
        
    Returns:
        tuple: (hostname, qkview_dir_path)
    """
    if not qkview_data:
        raise ValueError("QKView data is required for metadata-first initialization")
    
    # Create metadata first with hostname-based directory
    hostname, qkview_dir = create_metadata_first(qkview_id, qkview_data, base_path)
    
    # Save the raw API response to Docs
    docs_dir = Path(qkview_dir) / "Docs"
    docs_dir.mkdir(exist_ok=True)
    
    with open(docs_dir / "api_response.json", 'w') as f:
        json.dump(qkview_data, f, indent=2)
    
    # Create README
    create_readme_for_qkview(qkview_id, base_path)
    
    print(f"{GREEN}✓{NC} Initialized QKView processing for {hostname} (ID: {qkview_id})")
    return hostname, qkview_dir


if __name__ == "__main__":
    # Test the directory creation
    test_qkview_id = "24821984"
    test_data = {
        "id": "24821984",
        "hostname": "bigip-prod-01.example.com",
        "name": "test_qkview", 
        "status": "processed",
        "file_size": 41284557,
        "generation_date": 1754943581000
    }
    
    # Test metadata-first initialization
    hostname, qkview_dir = initialize_qkview_processing_metadata_first(test_qkview_id, test_data)
    print(f"Created: {hostname} -> {qkview_dir}")
    
    # Test saving some data
    save_data_to_qkview(test_qkview_id, "Diagnostics", "test_diagnostics.json", 
                       {"critical_issues": 2, "warnings": 5})
    
    # List all QKView directories
    qkview_dirs = list_qkview_directories()
    print(f"QKView directories: {qkview_dirs}")


#!/usr/bin/env python3
"""
QKView Directory Structure Utilities

Functions for creating and managing the standardized QKView directory structure.
"""

import os
import json
from datetime import datetime
from pathlib import Path


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
        "Logs",
        "Logs/search_results",
        "Docs"
    ]
    
    # Create all subdirectories
    for subdir in subdirectories:
        (qkview_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    print(f"✓ Created directory structure for QKView {qkview_id}")
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
    
    print(f"✓ Created metadata.json for QKView {qkview_id}")


def update_qkview_metadata(qkview_id, updates, base_path="QKViews"):
    """
    Update existing metadata.json file
    
    Args:
        qkview_id (str): QKView ID
        updates (dict): Dictionary of updates to apply
        base_path (str): Base directory path
    """
    metadata_file = Path(base_path) / str(qkview_id) / "metadata.json"
    
    if not metadata_file.exists():
        create_qkview_metadata(qkview_id, base_path=base_path)
    
    # Read existing metadata
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    # Apply updates
    metadata.update(updates)
    metadata["last_updated"] = datetime.now().isoformat()
    
    # Write back to file
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)


def save_data_to_qkview(qkview_id, category, filename, data, base_path="QKViews"):
    """
    Save data to appropriate QKView subdirectory
    
    Args:
        qkview_id (str): QKView ID
        category (str): Category subdirectory (e.g., "Diagnostics", "LTM")
        filename (str): Filename to save
        data: Data to save (dict for JSON, str for text)
        base_path (str): Base directory path
    """
    qkview_dir = Path(base_path) / str(qkview_id)
    category_dir = qkview_dir / category
    
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
    
    print(f"✓ Saved {filename} to {category} for QKView {qkview_id}")
    return str(file_path)


def get_qkview_directory(qkview_id, base_path="QKViews"):
    """
    Get the directory path for a QKView
    
    Args:
        qkview_id (str): QKView ID
        base_path (str): Base directory path
        
    Returns:
        str: Path to QKView directory
    """
    return str(Path(base_path) / str(qkview_id))


def list_qkview_directories(base_path="QKViews"):
    """
    List all QKView directories
    
    Args:
        base_path (str): Base directory path
        
    Returns:
        list: List of QKView IDs that have directories
    """
    base_dir = Path(base_path)
    
    if not base_dir.exists():
        return []
    
    # Get all subdirectories that look like QKView IDs (numeric)
    qkview_dirs = []
    for item in base_dir.iterdir():
        if item.is_dir() and item.name.isdigit():
            qkview_dirs.append(item.name)
    
    return sorted(qkview_dirs)


def create_readme_for_qkview(qkview_id, base_path="QKViews"):
    """
    Create a README.md file in the Docs subdirectory explaining the structure
    
    Args:
        qkview_id (str): QKView ID
        base_path (str): Base directory path
    """
    docs_dir = Path(base_path) / str(qkview_id) / "Docs"
    readme_file = docs_dir / "README.md"
    
    readme_content = f"""# QKView {qkview_id} Analysis

This directory contains extracted and analyzed data from F5 iHealth QKView {qkview_id}.

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
    
    print(f"✓ Created README.md for QKView {qkview_id}")


def initialize_qkview_processing(qkview_id, qkview_data=None, base_path="QKViews"):
    """
    Initialize complete QKView processing structure
    
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
    
    print(f"✓ Initialized QKView {qkview_id} processing structure")
    return qkview_dir


if __name__ == "__main__":
    # Test the directory creation
    test_qkview_id = "24821984"
    test_data = {"name": "test_qkview", "status": "processed"}
    
    # Initialize structure
    qkview_dir = initialize_qkview_processing(test_qkview_id, test_data)
    
    # Test saving some data
    save_data_to_qkview(test_qkview_id, "Diagnostics", "test_diagnostics.json", 
                       {"critical_issues": 2, "warnings": 5})
    
    # List all QKView directories
    qkview_dirs = list_qkview_directories()
    print(f"QKView directories: {qkview_dirs}")


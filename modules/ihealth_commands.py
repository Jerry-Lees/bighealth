#!/usr/bin/env python3
"""
F5 iHealth Commands Module

Handles downloading and organizing command outputs from F5 iHealth API.
Commands are organized by type (tmsh, UNIX, Utilities) and saved as text files.
"""

import os
import json
import base64
import time
from pathlib import Path
from ihealth_utils import F5iHealthClient
from qkview_directory_utils import update_qkview_metadata, find_qkview_directory

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


class F5iHealthCommands(F5iHealthClient):
    """F5 iHealth Commands operations"""
    
    def __init__(self, auth_handler):
        super().__init__(auth_handler)
        
        # Command organization structure
        self.command_structure = {
            'tmsh': {
                'subtypes': ['apm', 'auth', 'cli', 'cm', 'gtm', 'ilx', 'ltm', 'net', 'security', 'sys'],
                'description': 'Traffic Management Shell commands'
            },
            'unix': {
                'subtypes': ['Configuration', 'Current Data', 'Directory', 'Networking', 'TMOS'],
                'description': 'UNIX system commands'
            },
            'utilities': {
                'subtypes': ['general'],  # May need to be refined based on actual API response
                'description': 'System utilities and tools'
            }
        }
    
    def _create_commands_directory_structure(self, qkview_dir):
        """
        Create the complete directory structure for commands
        
        Args:
            qkview_dir (str): Path to QKView directory
        """
        commands_base = Path(qkview_dir) / "Commands"
        
        # Create main Commands directory
        commands_base.mkdir(exist_ok=True)
        
        # Create subdirectories for each command type and subtype
        for cmd_type, config in self.command_structure.items():
            type_dir = commands_base / cmd_type
            type_dir.mkdir(exist_ok=True)
            
            # Create subtype directories
            for subtype in config['subtypes']:
                subtype_dir = type_dir / subtype
                subtype_dir.mkdir(exist_ok=True)
        
        # Create a JSON directory for raw API responses
        json_dir = commands_base / "_json_responses"
        json_dir.mkdir(exist_ok=True)
        
        return str(commands_base)
    
    def _get_available_commands(self, qkview_id):
        """
        Get list of available commands for a QKView
        
        Args:
            qkview_id (str): QKView ID
            
        Returns:
            dict: Available commands or None if failed
        """
        endpoint = f"/qkviews/{qkview_id}/commands"
        return self._make_request("GET", endpoint)
    
    def _get_command_output(self, qkview_id, command_id):
        """
        Get the output for a specific command
        
        Args:
            qkview_id (str): QKView ID
            command_id (str): Command ID from the available commands list
            
        Returns:
            dict: Command output data or None if failed
        """
        endpoint = f"/qkviews/{qkview_id}/commands/{command_id}"
        return self._make_request("GET", endpoint)
    
    def _decode_command_output(self, encoded_output):
        """
        Decode base64 encoded command output with proper padding
        
        Args:
            encoded_output (str): Base64 encoded command output
            
        Returns:
            str: Decoded command output
        """
        try:
            if not encoded_output:
                return ""
            
            # Remove any whitespace
            encoded_output = encoded_output.strip()
            
            # Add padding if necessary
            # Base64 strings must be a multiple of 4 characters
            padding_needed = 4 - (len(encoded_output) % 4)
            if padding_needed != 4:  # Only add padding if actually needed
                encoded_output += '=' * padding_needed
            
            if self.debug:
                print(f"    DEBUG: Original length: {len(encoded_output.rstrip('='))}, After padding: {len(encoded_output)}")
            
            # Decode base64
            decoded_bytes = base64.b64decode(encoded_output)
            
            # Convert to string, handling potential encoding issues
            try:
                return decoded_bytes.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    # Try latin-1 as fallback
                    return decoded_bytes.decode('latin-1', errors='replace')
                except:
                    # Final fallback - decode with error replacement
                    return decoded_bytes.decode('utf-8', errors='replace')
                
        except Exception as e:
            print(f"  {YELLOW}⚠{NC} Warning: Failed to decode command output: {e}")
            return f"[DECODE ERROR: {e}]\nOriginal base64 data:\n{encoded_output}"
    
    def _sanitize_filename(self, filename):
        """
        Sanitize filename for filesystem compatibility
        
        Args:
            filename (str): Original filename
            
        Returns:
            str: Sanitized filename
        """
        # Replace invalid characters with underscores
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\n', '\r', '\t']
        sanitized = filename
        
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Replace multiple spaces with single space
        sanitized = ' '.join(sanitized.split())
        
        # Remove leading/trailing whitespace and dots (Windows issue)
        sanitized = sanitized.strip(' .')
        
        # Limit length to reasonable filesystem limits (200 chars should be safe)
        if len(sanitized) > 200:
            sanitized = sanitized[:200].rstrip()
        
        # Ensure we don't have an empty filename
        if not sanitized:
            sanitized = "unnamed_command"
        
        return sanitized
    
    def _determine_command_location(self, command_name):
        """
        Determine the appropriate directory location for a command based on the command name
        
        Args:
            command_name (str): Full command name from the API
            
        Returns:
            tuple: (command_type, subtype, filename)
        """
        # Default values
        cmd_type = 'utilities'
        subtype = 'general'
        
        # Convert to lowercase for analysis
        command_lower = command_name.lower().strip()
        
        # List of specific utility commands
        utility_commands = [
            'engineering hotfix changes',
            'engineering hotfix changes (internal)',
            'hotfix changes',
            'hotfix changes (internal)',
            'public ssl certificates',
            'recreate data groups',
            'virtual server traffic'
        ]
        
        # Check if this is a specific utility command
        if command_lower in utility_commands:
            cmd_type = 'utilities'
            subtype = 'general'
        
        # Check if it's a tmsh command (starts with "list" or "show")
        elif command_lower.startswith('list ') or command_lower.startswith('show '):
            cmd_type = 'tmsh'
            
            # Split the command to get the module (second parameter)
            command_parts = command_name.split()
            
            if len(command_parts) >= 2:
                # Get the module (second parameter after list/show)
                module = command_parts[1].lower()
                
                # Map the module to our predefined tmsh subtypes
                if module in ['ltm', '/ltm']:
                    subtype = 'ltm'
                elif module in ['gtm', '/gtm']:
                    subtype = 'gtm'
                elif module in ['apm', '/apm']:
                    subtype = 'apm'
                elif module in ['auth', '/auth']:
                    subtype = 'auth'
                elif module in ['net', '/net']:
                    subtype = 'net'
                elif module in ['sys', '/sys']:
                    subtype = 'sys'
                elif module in ['security', '/security']:
                    subtype = 'security'
                elif module in ['cm', '/cm']:
                    subtype = 'cm'
                elif module in ['ilx', '/ilx']:
                    subtype = 'ilx'
                elif module in ['cli', '/cli']:
                    subtype = 'cli'
                else:
                    # Default tmsh subtype for unknown modules
                    subtype = 'sys'
            else:
                # Default tmsh subtype if we can't parse the module
                subtype = 'sys'
                
        # Everything else is a UNIX command
        else:
            cmd_type = 'unix'
            
            # Determine UNIX subtype based on command content
            if any(config_cmd in command_lower for config_cmd in ['bigip.conf', '/config/', 'mcpd', 'tmm', 'config']):
                subtype = 'Configuration'
            elif any(net_cmd in command_lower for net_cmd in ['netstat', 'ifconfig', 'route', 'arp', 'ss ', 'ip ']):
                subtype = 'Networking'
            elif any(dir_cmd in command_lower for dir_cmd in ['ls ', 'find ', 'du ', 'df ', 'tree', 'pwd']):
                subtype = 'Directory'
            elif any(tmos_cmd in command_lower for tmos_cmd in ['tmsh', 'tmos', '/usr/bin/tmsh']):
                subtype = 'TMOS'
            else:
                subtype = 'Current Data'  # Default UNIX subtype for commands like date, uptime, who, ps, etc.
        
        # Create sanitized filename (without ID)
        filename = self._sanitize_filename(command_name) + '.txt'
        
        return cmd_type, subtype, filename
    
    def _should_skip_command_download(self, qkview_dir, command_id, initial_name):
        """
        Check if we should skip downloading a command based on existing files
        This is called BEFORE making the API call to get the command details
        
        Args:
            qkview_dir (str): Path to QKView directory
            command_id (str): Command ID
            initial_name (str): Initial command name (may be generic)
            
        Returns:
            dict: Skip information with keys: skip, reason, name, type, text_file, json_file
        """
        # We need to check all possible locations where this command might already exist
        # Since we don't know the actual command name yet, we need to search for files
        # that might match this command ID
        
        commands_base = Path(qkview_dir) / "Commands"
        
        # Search through all command directories for files that might match this ID
        for cmd_type in ['tmsh', 'unix', 'utilities']:
            cmd_type_dir = commands_base / cmd_type
            if not cmd_type_dir.exists():
                continue
                
            # Check all subdirectories
            for subdir in cmd_type_dir.iterdir():
                if not subdir.is_dir():
                    continue
                    
                # Look for JSON files that contain this command ID
                for json_file in subdir.glob('*.json'):
                    try:
                        with open(json_file, 'r') as f:
                            json_data = json.load(f)
                        
                        # Check if this JSON file contains our command ID
                        if (json_data.get('metadata', {}).get('id') == command_id or
                            json_data.get('api_response', [{}])[0].get('id') == command_id):
                            
                            # Found a matching JSON file, check if corresponding TXT file exists
                            txt_file = json_file.with_suffix('.txt')
                            if txt_file.exists() and txt_file.stat().st_size > 300:
                                # Get the actual command name from the JSON
                                actual_name = json_data.get('metadata', {}).get('name', initial_name)
                                if not actual_name or actual_name == initial_name:
                                    # Try to get it from the API response
                                    api_response = json_data.get('api_response', [])
                                    if api_response and len(api_response) > 0:
                                        actual_name = api_response[0].get('name', initial_name)
                                
                                return {
                                    'skip': True,
                                    'reason': f'File exists and is adequate size ({txt_file.stat().st_size} bytes)',
                                    'name': actual_name,
                                    'type': f"{cmd_type}/{subdir.name}",
                                    'text_file': str(txt_file),
                                    'json_file': str(json_file)
                                }
                                
                    except Exception:
                        # If we can't read the JSON file, continue searching
                        continue
        
        # No existing file found that matches this command ID
        return {
            'skip': False,
            'reason': 'No existing file found',
            'name': initial_name,
            'type': 'unknown',
            'text_file': None,
            'json_file': None
        }

    def _save_command_output(self, qkview_dir, command_name, base64_output, full_response, command_id):
        """
        Save command output to appropriate location
        
        Args:
            qkview_dir (str): Path to QKView directory
            command_name (str): Actual command name from the API response
            base64_output (str): Base64 encoded command output
            full_response (list): Full API response for JSON storage
            command_id (str): Command ID for unique identification
            
        Returns:
            dict: Information about saved files
        """
        # Determine location based on command name
        cmd_type, subtype, base_filename = self._determine_command_location(command_name)
        
        # Create target directory path
        commands_base = Path(qkview_dir) / "Commands"
        target_dir = commands_base / cmd_type / subtype
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename WITHOUT the command ID (just sanitized command name)
        safe_name = self._sanitize_filename(command_name)
        txt_filename = f"{safe_name}.txt"
        json_filename = f"{safe_name}.json"
        
        txt_file_path = target_dir / txt_filename
        json_file_path = target_dir / json_filename
        
        # Check if file already exists and is large enough (skip download if so)
        if txt_file_path.exists() and txt_file_path.stat().st_size > 300:
            return {
                'text_file': str(txt_file_path),
                'json_file': str(json_file_path) if json_file_path.exists() else None,
                'command_type': f"{cmd_type}/{subtype}",
                'filename': txt_filename,
                'json_filename': json_filename,
                'command_name': command_name,
                'command_id': command_id,
                'skipped': True,
                'reason': f'File exists and is adequate size ({txt_file_path.stat().st_size} bytes)'
            }
        
        # Save raw JSON response for debugging (in same folder as text file)
        json_data = {
            'metadata': {
                'id': command_id,
                'name': command_name,
                'retrieved_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'command_type': f"{cmd_type}/{subtype}",
            },
            'api_response': full_response,
            'base64_output': base64_output  # Keep base64 encoded for reference
        }
        
        with open(json_file_path, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        # Decode and save command output to text file
        decoded_output = self._decode_command_output(base64_output)
        
        with open(txt_file_path, 'w', encoding='utf-8') as f:
            # Add header with command info
            f.write(f"# Command: {command_name}\n")
            f.write(f"# ID: {command_id}\n")
            f.write(f"# Type: {cmd_type}/{subtype}\n")
            f.write(f"# Retrieved: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# " + "="*70 + "\n\n")
            f.write(decoded_output)
        
        return {
            'text_file': str(txt_file_path),
            'json_file': str(json_file_path),
            'command_type': f"{cmd_type}/{subtype}",
            'filename': txt_filename,
            'json_filename': json_filename,
            'command_name': command_name,
            'command_id': command_id,
            'skipped': False
        }
    
    def download_all_commands(self, qkview_id, base_path="QKViews"):
        """
        Download all available commands for a QKView
        
        Args:
            qkview_id (str): QKView ID
            base_path (str): Base directory path
            
        Returns:
            dict: Summary of downloaded commands
        """
        print(f"Downloading command outputs for QKView {qkview_id}...")
        
        # Find the correct directory, or create it if it doesn't exist
        qkview_dir, is_hostname_based = find_qkview_directory(qkview_id, base_path)
        
        if not qkview_dir:
            # Directory doesn't exist, we need to create it using metadata-first approach
            print("  QKView directory not found, creating directory structure...")
            
            # Get QKView details to create proper directory structure
            qkview_details = self.get_qkview_details(qkview_id)
            
            if not qkview_details:
                print(f"{RED}✗{NC} Failed to get QKView details for directory creation")
                return {'success': False, 'error': 'Could not get QKView details'}
            
            # Use the metadata-first initialization to create the directory
            from qkview_directory_utils import initialize_qkview_processing_metadata_first
            
            try:
                hostname, qkview_dir = initialize_qkview_processing_metadata_first(
                    qkview_id, qkview_details, base_path
                )
                print(f"  {GREEN}✓{NC} Created directory structure for {hostname}")
            except Exception as e:
                print(f"{RED}✗{NC} Failed to create directory structure: {e}")
                return {'success': False, 'error': f'Directory creation failed: {e}'}
        
        # Create commands directory structure
        commands_dir = self._create_commands_directory_structure(qkview_dir)
        
        # Initialize logging file
        lastrun_log_file = Path(commands_dir) / "lastrun.log"
        
        def log_api_call(command_id, command_name, action):
            """Log API calls to lastrun.log"""
            try:
                with open(lastrun_log_file, 'a') as f:
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"[{timestamp}] {action}: {command_name} (ID: {command_id})\n")
            except Exception:
                pass  # Don't fail if logging fails
        
        # Clear the log file at the start of each run
        try:
            with open(lastrun_log_file, 'w') as f:
                f.write(f"# Command Download Log for QKView {qkview_id}\n")
                f.write(f"# Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# This log shows all REST API calls made during command processing\n")
                f.write("#" + "="*70 + "\n\n")
        except Exception:
            pass  # Don't fail if logging fails
        
        # Check if we already have the commands list saved
        commands_json_file = Path(commands_dir) / "commands.json"
        available_commands_txt_file = Path(commands_dir) / "available-commands.txt"
        
        if commands_json_file.exists():
            print("  Loading commands from saved file...")
            try:
                with open(commands_json_file, 'r') as f:
                    commands_data = json.load(f)
                
                # Extract the actual response part (not the headers we may have added)
                if 'api_response' in commands_data:
                    available_commands = commands_data['api_response']
                elif 'response' in commands_data:
                    available_commands = commands_data['response']
                else:
                    # Assume the whole file is the response if no wrapper
                    available_commands = commands_data
                    
                print(f"  {GREEN}✓{NC} Loaded commands from existing file")
                
            except Exception as e:
                print(f"{YELLOW}⚠{NC} Could not load existing commands file, fetching from API: {e}")
                # Fall back to API call
                available_commands = self._get_available_commands(qkview_id)
        else:
            # Get available commands from API
            print("  Retrieving available commands...")
            available_commands = self._get_available_commands(qkview_id)
            
            if available_commands:
                # Save the commands list for future use
                commands_data = {
                    'metadata': {
                        'qkview_id': qkview_id,
                        'retrieved_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'total_commands': len(available_commands) if isinstance(available_commands, list) else 'unknown'
                    },
                    'api_response': available_commands
                }
                
                with open(commands_json_file, 'w') as f:
                    json.dump(commands_data, f, indent=2)
                print(f"  {GREEN}✓{NC} Saved commands list to commands.json")
        
        if not available_commands:
            print(f"{RED}✗{NC} Failed to retrieve available commands")
            return {'success': False, 'error': 'Failed to get available commands'}
        
        # Parse available commands - expect a list of command IDs
        commands_list = []
        if isinstance(available_commands, list):
            commands_list = available_commands
        elif isinstance(available_commands, dict):
            if 'commands' in available_commands:
                commands_list = available_commands['commands']
            elif 'data' in available_commands:
                commands_list = available_commands['data']
            else:
                commands_list = [available_commands]
        
        if not commands_list:
            print(f"{YELLOW}⚠{NC} No commands found for QKView {qkview_id}")
            return {'success': True, 'commands_downloaded': 0, 'commands': []}
        
        print(f"  Found {len(commands_list)} available commands")
        
        # Download each command output with overwriting progress
        downloaded_commands = []
        successful_downloads = 0
        skipped_downloads = 0
        actual_command_names = {}  # Store actual command names as we discover them
        
        for i, command_metadata in enumerate(commands_list, 1):
            try:
                # The initial list might just have IDs, or basic metadata
                command_id = command_metadata.get('id', f'unknown_id_{i}')
                initial_name = command_metadata.get('name', f'command_{i}')
                
                # Clear both lines completely before writing new content
                print(f"\r{' ':<120}")  # Clear first line
                print(f"\r{' ':<120}")  # Clear second line  
                print("\033[2A", end="")  # Move cursor back up 2 lines
                
                # First line: Show fetching progress
                fetch_line = f"  [{i}/{len(commands_list)}] Fetching: Command ID {command_id[:12]}..."
                print(f"{fetch_line:<80}")
                
                # Check if we can skip this command based on existing files BEFORE making API call
                # We need to get the command name first to determine the file path
                skip_info = self._should_skip_command_download(qkview_dir, command_id, initial_name)
                
                if skip_info['skip']:
                    # Second line: Show skipped without API call
                    skip_line = f"    Skipped: {skip_info['name'][:50]}{'...' if len(skip_info['name']) > 50 else ''} - {skip_info['reason']}"
                    print(f"{skip_line:<120}")
                    
                    # Store the actual command name we found
                    actual_command_names[command_id] = skip_info['name']
                    
                    # Log the skip (no API call made)
                    log_api_call(command_id, skip_info['name'], "SKIPPED")
                    
                    downloaded_commands.append({
                        'id': command_id,
                        'name': skip_info['name'],
                        'type': skip_info['type'],
                        'text_file': skip_info['text_file'],
                        'json_file': skip_info.get('json_file'),
                        'status': 'skipped',
                        'skipped': True
                    })
                    
                    skipped_downloads += 1
                else:
                    # Log the API call being made
                    log_api_call(command_id, initial_name, "API_CALL_START")
                    
                    # Get the actual command details using the command ID
                    command_response = self._get_command_output(qkview_id, command_id)
                    
                    if command_response and isinstance(command_response, list) and len(command_response) > 0:
                        # Extract the actual command info from the response
                        command_info = command_response[0]  # First item in the list
                        
                        actual_command_name = command_info.get('name', initial_name)
                        command_status = command_info.get('status', 0)
                        base64_output = command_info.get('output', '')
                        
                        # Store the actual command name
                        actual_command_names[command_id] = actual_command_name
                        
                        # Log the successful API response
                        log_api_call(command_id, actual_command_name, "API_CALL_SUCCESS")
                        
                        if base64_output:
                            # Save the command with the actual name and output
                            file_info = self._save_command_output(
                                qkview_dir, 
                                actual_command_name,
                                base64_output,
                                command_response,  # Full response for JSON
                                command_id
                            )
                            
                            # Check if file was skipped during save (shouldn't happen now)
                            if file_info.get('skipped', False):
                                # Second line: Show skipped
                                skip_line = f"    Skipped: {actual_command_name[:50]}{'...' if len(actual_command_name) > 50 else ''} - {file_info['reason']}"
                                print(f"{skip_line:<120}")
                                skipped_downloads += 1
                                log_api_call(command_id, actual_command_name, "SAVED_SKIPPED")
                            else:
                                # Second line: Show saving progress
                                command_display = actual_command_name[:50] + ('...' if len(actual_command_name) > 50 else '')
                                file_display = f"{file_info['command_type']}/{file_info['filename']}"
                                if len(file_display) > 40:
                                    file_display = file_display[:37] + '...'
                                
                                save_line = f"    Saving Command: {command_display} to {file_display}"
                                print(f"{save_line:<120}")
                                log_api_call(command_id, actual_command_name, "DOWNLOADED_AND_SAVED")
                            
                            downloaded_commands.append({
                                'id': command_id,
                                'name': actual_command_name,
                                'type': file_info['command_type'],
                                'text_file': file_info['text_file'],
                                'json_file': file_info['json_file'],
                                'status': command_status,
                                'skipped': file_info.get('skipped', False)
                            })
                            
                            successful_downloads += 1
                        else:
                            # Second line: Show no output warning
                            warning_line = f"    {YELLOW}⚠{NC} No output data for: {actual_command_name[:50]}"
                            print(f"{warning_line:<120}")
                            
                            log_api_call(command_id, actual_command_name, "API_CALL_NO_OUTPUT")
                            
                            downloaded_commands.append({
                                'id': command_id,
                                'name': actual_command_name,
                                'error': 'No output data'
                            })
                    else:
                        # Second line: Show API failure warning
                        warning_line = f"    {YELLOW}⚠{NC} Failed to get command details for ID {command_id[:12]}"
                        print(f"{warning_line:<120}")
                        
                        # Store the initial name since we couldn't get the real one
                        actual_command_names[command_id] = initial_name
                        
                        log_api_call(command_id, initial_name, "API_CALL_FAILED")
                        
                        downloaded_commands.append({
                            'id': command_id,
                            'name': initial_name,
                            'error': 'API request failed'
                        })
                
                # Move cursor up 2 lines to overwrite both lines next iteration (unless it's the last one)
                if i < len(commands_list):
                    print("\033[2A", end="", flush=True)
                
            except Exception as e:
                error_command_id = command_metadata.get('id', f'unknown_{i}') if 'command_metadata' in locals() else f'unknown_{i}'
                
                # Clear both lines completely
                print(f"\r{' ':<120}")  # Clear first line
                print(f"\r{' ':<120}")  # Clear second line  
                print("\033[2A", end="")  # Move cursor back up 2 lines
                
                # First line: Error fetching
                error_fetch_line = f"  [{i}/{len(commands_list)}] Error: Command ID {error_command_id[:12]}..."
                print(f"{error_fetch_line:<80}")
                # Second line: Error details
                error_detail_line = f"    {RED}✗{NC} Error processing command: {str(e)[:70]}"
                print(f"{error_detail_line:<120}")
                
                if i < len(commands_list):
                    print("\033[2A", end="", flush=True)  # Move up 2 lines
                
                if self.debug:
                    # For debug, don't overwrite - show the error permanently
                    print("\033[2B")  # Move down 2 lines
                    print(f"    DEBUG: Command metadata was: {command_metadata}")
                
                # Store the initial name for the error case
                actual_command_names[error_command_id] = f'error_command_{i}'
                
                log_api_call(error_command_id, f'error_command_{i}', f"ERROR: {str(e)}")
                
                downloaded_commands.append({
                    'id': error_command_id,
                    'name': f'error_command_{i}',
                    'error': str(e)
                })
        
        # For the last command, overwrite the two lines with the success message
        if successful_downloads > 0 or skipped_downloads > 0:
            # Clear both lines completely
            print(f"\r{' ':<120}")  # Clear first line
            print(f"\r{' ':<120}")  # Clear second line  
            print("\033[2A", end="")  # Move cursor back up 2 lines
            
            total_processed = successful_downloads + skipped_downloads
            success_line = f"{GREEN}✓{NC} Successfully processed {total_processed} commands for QKView {qkview_id}"
            if skipped_downloads > 0:
                success_line += f" ({successful_downloads} downloaded, {skipped_downloads} skipped)"
            print(f"{success_line:<120}")
            print(f"{' ':<120}")  # Clear the second line
        else:
            # Move cursor down 2 lines to get past the overwritten area and add final newline
            print("\033[2B")  # Move down 2 lines
            print()  # Add a blank line
        
        # Save available commands as text file for easier review with ACTUAL command names
        if not available_commands_txt_file.exists():
            try:
                with open(available_commands_txt_file, 'w') as f:
                    f.write(f"# Available Commands for QKView {qkview_id}\n")
                    f.write(f"# Retrieved: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# Total Commands: {len(commands_list)}\n")
                    f.write("#" + "="*70 + "\n\n")
                    
                    for i, cmd in enumerate(commands_list, 1):
                        cmd_id = cmd.get('id', f'unknown_{i}')
                        
                        # Use the actual command name we discovered, or fallback to initial name
                        actual_name = actual_command_names.get(cmd_id, cmd.get('name', f'command_{i}'))
                        
                        f.write(f"{i:3d}. {actual_name}\n")
                        f.write(f"     ID: {cmd_id}\n")
                        if 'status' in cmd:
                            f.write(f"     Status: {cmd['status']}\n")
                        f.write("\n")
                        
                print(f"  {GREEN}✓{NC} Saved available commands list to available-commands.txt")
            except Exception as e:
                if self.debug:
                    print(f"  DEBUG: Could not save available commands text file: {e}")
        else:
            # Update existing file with actual command names if we discovered new ones
            try:
                with open(available_commands_txt_file, 'w') as f:
                    f.write(f"# Available Commands for QKView {qkview_id}\n")
                    f.write(f"# Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# Total Commands: {len(commands_list)}\n")
                    f.write("#" + "="*70 + "\n\n")
                    
                    for i, cmd in enumerate(commands_list, 1):
                        cmd_id = cmd.get('id', f'unknown_{i}')
                        
                        # Use the actual command name we discovered
                        actual_name = actual_command_names.get(cmd_id, cmd.get('name', f'command_{i}'))
                        
                        f.write(f"{i:3d}. {actual_name}\n")
                        f.write(f"     ID: {cmd_id}\n")
                        if 'status' in cmd:
                            f.write(f"     Status: {cmd['status']}\n")
                        f.write("\n")
                        
                if self.debug:
                    print(f"  DEBUG: Updated available-commands.txt with actual command names")
            except Exception as e:
                if self.debug:
                    print(f"  DEBUG: Could not update available commands text file: {e}")
        
        # Check and cleanup debug directory if it exists and is empty
        debug_dir = Path(qkview_dir) / "Commands" / "debug_responses"
        if debug_dir.exists():
            try:
                # Check if directory is empty
                if not any(debug_dir.iterdir()):
                    # Directory is empty, remove it
                    debug_dir.rmdir()
                    if self.debug:
                        print(f"  Removed empty debug directory: {debug_dir}")
                else:
                    # Directory is not empty, show warning
                    print(f"{YELLOW}⚠{NC} Warning: Debug directory is not empty: {debug_dir}")
                    print(f"  This directory may contain debugging files from previous runs")
            except Exception as e:
                if self.debug:
                    print(f"  DEBUG: Could not cleanup debug directory: {e}")
        
        # Update metadata
        update_qkview_metadata(qkview_id, {
            'processing_status': {'commands': True},
            'commands_info': {
                'total_available': len(commands_list),
                'successfully_downloaded': successful_downloads,
                'skipped_downloads': skipped_downloads,
                'download_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'commands_directory': commands_dir
            }
        }, base_path)
        
        # Summary (simplified since we already showed the success message)
        hostname = Path(qkview_dir).name
        if self.debug:
            print(f"DEBUG: Completed command downloads for {hostname}")
            print(f"DEBUG: Downloaded: {successful_downloads}/{len(commands_list)} commands")
            print(f"DEBUG: Skipped: {skipped_downloads}/{len(commands_list)} commands")
        
        return {
            'success': True,
            'commands_downloaded': successful_downloads,
            'commands_skipped': skipped_downloads,
            'total_commands': len(commands_list),
            'commands': downloaded_commands,
            'commands_directory': commands_dir
        }
    
    def get_commands_summary(self, qkview_id, base_path="QKViews"):
        """
        Get a summary of downloaded commands for a QKView
        
        Args:
            qkview_id (str): QKView ID
            base_path (str): Base directory path
            
        Returns:
            dict: Commands summary
        """
        # Find the correct directory
        qkview_dir, is_hostname_based = find_qkview_directory(qkview_id, base_path)
        
        if not qkview_dir:
            return None
        
        commands_dir = Path(qkview_dir) / "Commands"
        if not commands_dir.exists():
            return None
        
        summary = {
            'qkview_id': qkview_id,
            'commands_directory': str(commands_dir),
            'command_types': {}
        }
        
        # Count commands by type
        for cmd_type in self.command_structure.keys():
            type_dir = commands_dir / cmd_type
            if type_dir.exists():
                type_summary = {
                    'subtypes': {},
                    'total_commands': 0
                }
                
                for subtype in self.command_structure[cmd_type]['subtypes']:
                    subtype_dir = type_dir / subtype
                    if subtype_dir.exists():
                        txt_files = list(subtype_dir.glob('*.txt'))
                        type_summary['subtypes'][subtype] = len(txt_files)
                        type_summary['total_commands'] += len(txt_files)
                
                summary['command_types'][cmd_type] = type_summary
        
        return summary


if __name__ == "__main__":
    # Test the commands module
    from ihealth_auth import F5iHealthAuth, load_credentials_from_files
    
    client_id, client_secret = load_credentials_from_files()
    if not client_id or not client_secret:
        print("No credentials found in files")
        exit(1)
    
    auth = F5iHealthAuth(client_id, client_secret)
    if auth.authenticate():
        commands = F5iHealthCommands(auth)
        
        # Test with a sample QKView ID
        test_qkview_id = "24821984"  # Replace with actual ID
        
        print(f"Testing commands download for QKView {test_qkview_id}")
        
        # Download all commands
        result = commands.download_all_commands(test_qkview_id)
        print(f"Download result: {result}")
        
        # Get summary
        summary = commands.get_commands_summary(test_qkview_id)
        if summary:
            print(f"Commands summary: {json.dumps(summary, indent=2)}")
    else:
        print("Authentication failed")


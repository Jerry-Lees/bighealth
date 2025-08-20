#!/usr/bin/env python3
"""
BigHealth - F5 iHealth API Command Line Tool (Enhanced with Metadata-First)

Main script for interacting with F5 iHealth API with metadata-first processing.
"""

import sys
import os

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
NC = '\033[0m'  # No Color

# Check if we're in a virtual environment and have required dependencies
def check_environment():
    """Check if we're properly set up to run"""
    try:
        import requests
    except ImportError:
        print(f"{YELLOW}▲{NC} Error: Required dependencies not found!")
        print()
        print("It looks like you're not in the BigHealth virtual environment.")
        print("This usually happens when running the script directly after installation.")
        print()
        print("Solution:")
        print("   cd ~/bighealth")
        print("   source bighealth_env/bin/activate")
        print("   python bighealth.py list")
        print()
        print("OR use the helper script:")
        print("   ./scripts/run.sh list")
        print()
        print("For more help, see: https://github.com/Jerry-Lees/bighealth")
        sys.exit(1)

# Check environment before importing our modules
check_environment()

import argparse
import json

# Add modules directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

from ihealth_auth import F5iHealthAuth, load_credentials_from_files, get_credentials_interactive
from ihealth_utils import F5iHealthClient, print_qkview_summary, print_processing_summary
from qkview_directory_utils import list_qkview_directories, find_qkview_directory
from ihealth_qkview_download import F5iHealthQKViewDownload


def get_authenticated_client(verbose=False, debug=False):
    """Get authenticated client - common function for all commands"""
    # Get credentials
    client_id, client_secret = load_credentials_from_files(
        os.path.join('credentials', 'cid'),
        os.path.join('credentials', 'cs')
    )
    
    if not client_id or not client_secret:
        if verbose or debug:
            print("Credential files not found, prompting for input...")
        client_id, client_secret = get_credentials_interactive()
    
    if not client_id or not client_secret:
        print(f"{RED}✗{NC} Client ID and Client Secret are required")
        print("\nTo get credentials:")
        print("1. Log in to https://ihealth2.f5.com")
        print("2. Go to Settings")
        print("3. Generate Client ID and Client Secret")
        print("4. Save them:")
        print("   echo 'your_client_id' > credentials/cid")
        print("   echo 'your_client_secret' > credentials/cs")
        sys.exit(1)
    
    if verbose or debug:
        print(f"Using Client ID: {client_id[:8]}...")
    
    # Authenticate
    print("Authenticating with F5 iHealth API...")
    auth = F5iHealthAuth(client_id, client_secret)
    
    if not auth.authenticate():
        print(f"{RED}✗{NC} Authentication failed")
        sys.exit(1)
    
    print(f"{GREEN}✓{NC} Authentication successful")
    return F5iHealthClient(auth, debug=debug), auth


def list_qkviews_command(args):
    """Handle the list QKViews command - just shows what's available"""
    client, auth = get_authenticated_client(args.verbose, args.debug)
    
    # Get QKViews
    print("Retrieving QKViews...")
    qkview_data = client.list_qkviews()
    
    if qkview_data is None:
        print(f"{RED}✗{NC} Failed to retrieve QKViews")
        sys.exit(1)
    
    # Display results
    if args.json_only:
        print(json.dumps(qkview_data, indent=2))
    else:
        print_qkview_summary(qkview_data, show_raw=args.verbose or args.debug)
        
        if args.verbose or args.debug:
            print(f"\n{GREEN}✓{NC} Token expires at: {auth.token_expires_at}")


def process_qkviews_command(args):
    """Handle processing QKViews with metadata-first approach"""
    client, auth = get_authenticated_client(args.verbose, args.debug)
    
    if args.id:
        # Process specific QKView ID with metadata-first approach
        print(f"Processing QKView {args.id} (metadata-first approach)...")
        
        # Step 1: Get metadata and create directory structure first
        context = client.process_qkview_metadata_first(args.id)
        
        if not context:
            print(f"{RED}✗{NC} Failed to initialize QKView {args.id}")
            sys.exit(1)
        
        hostname = context['hostname']
        qkview_details = context['qkview_details']
        
        print(f"{GREEN}✓{NC} Successfully initialized {hostname} (QKView {args.id})")
        
        # Step 2: Download QKView file (now with metadata available)
        print("Downloading QKView file...")
        try:
            downloader = F5iHealthQKViewDownload(auth)
            download_result = downloader.download_qkview_file(args.id, qkview_details)
            
            if download_result['success']:
                if download_result.get('skipped'):
                    print(f"QKView file skipped: {download_result['reason']}")
                else:
                    print(f"{GREEN}✓{NC} QKView file downloaded successfully")
                    # Show size validation warning if present
                    if 'size_validation' in download_result and not download_result['size_validation']['valid']:
                        print(f"{YELLOW}⚠{NC} WARNING: {download_result['size_validation']['message']}")
            else:
                print(f"{YELLOW}⚠{NC} QKView file download failed: {download_result['error']}")
        except Exception as e:
            print(f"{YELLOW}⚠{NC} QKView file download failed: {e}")
        
        # Step 3: Process diagnostics
        print("Processing diagnostics...")
        try:
            from ihealth_diagnostics import F5iHealthDiagnostics
            diagnostics = F5iHealthDiagnostics(auth)
            files = diagnostics.download_diagnostic_reports(args.id)
            
            if any(files.values()):
                print(f"{GREEN}✓{NC} Diagnostics processed successfully")
            else:
                print(f"{YELLOW}⚠{NC} Diagnostics processing had issues")
        except Exception as e:
            print(f"{YELLOW}⚠{NC} Diagnostics processing failed: {e}")
        
        print(f"\nCompleted processing for {hostname}")
        
        if args.verbose or args.debug:
            print(f"\nProcessing Context:")
            print(json.dumps({k: v for k, v in context.items() if k != 'qkview_details'}, indent=2))
    
    else:
        # Process all QKViews with metadata-first approach
        print("Retrieving QKView list...")
        qkview_data = client.list_qkviews()
        
        if qkview_data is None:
            print(f"{RED}✗{NC} Failed to retrieve QKViews")
            sys.exit(1)
        
        if args.debug:
            print(f"DEBUG: QKView data type: {type(qkview_data)}")
            print(f"DEBUG: QKView data: {qkview_data}")
        
        # Extract QKView IDs from the response
        qkview_ids = []
        if isinstance(qkview_data, dict) and 'id' in qkview_data:
            qkview_ids = qkview_data['id']
            if args.debug:
                print(f"DEBUG: Found QKView IDs in 'id' field: {qkview_ids}")
        elif isinstance(qkview_data, list):
            qkview_ids = qkview_data
            if args.debug:
                print(f"DEBUG: QKView data is a list: {qkview_ids}")
        else:
            if args.debug:
                print(f"DEBUG: Unexpected QKView data structure")
        
        if not qkview_ids:
            print("No QKViews found to process")
            if args.debug:
                print(f"DEBUG: qkview_data was: {qkview_data}")
            return
        
        print(f"\nProcessing {len(qkview_ids)} QKView(s) with metadata-first approach...")
        
        # Import modules for batch processing
        from ihealth_diagnostics import F5iHealthDiagnostics
        diagnostics = F5iHealthDiagnostics(auth)
        downloader = F5iHealthQKViewDownload(auth)
        
        # Track processing results
        processing_contexts = []
        successful_count = 0
        
        # Process each QKView
        for i, qkview_id in enumerate(qkview_ids, 1):
            try:
                print(f"\n[{i}/{len(qkview_ids)}] Processing QKView {qkview_id}...")
                
                # Step 1: Metadata-first initialization
                context = client.process_qkview_metadata_first(qkview_id)
                processing_contexts.append(context)
                
                if not context:
                    print(f"{RED}✗{NC} Failed to initialize QKView {qkview_id}")
                    continue
                
                hostname = context['hostname']
                qkview_details = context['qkview_details']
                
                print(f"  {GREEN}✓{NC} Initialized {hostname}")
                successful_count += 1
                
                # Step 2: Download QKView file
                print("  Downloading QKView file...")
                try:
                    download_result = downloader.download_qkview_file(qkview_id, qkview_details)
                    if download_result['success']:
                        if download_result.get('skipped'):
                            print(f"  QKView file skipped: {download_result['reason']}")
                        else:
                            print(f"  {GREEN}✓{NC} QKView file downloaded: {download_result['filename']}")
                            # Show size validation warning if present
                            if 'size_validation' in download_result and not download_result['size_validation']['valid']:
                                print(f"  {YELLOW}⚠{NC} WARNING: {download_result['size_validation']['message']}")
                    else:
                        print(f"  {YELLOW}⚠{NC} QKView file download failed: {download_result['error']}")
                except Exception as e:
                    print(f"  {YELLOW}⚠{NC} QKView file download failed: {e}")
                
                # Step 3: Process diagnostics
                print("  Processing diagnostics...")
                try:
                    files = diagnostics.download_diagnostic_reports(qkview_id)
                    if any(files.values()):
                        print(f"  {GREEN}✓{NC} Diagnostics processed")
                    else:
                        print(f"  {YELLOW}⚠{NC} Diagnostics had issues")
                except Exception as e:
                    print(f"  {YELLOW}⚠{NC} Diagnostics failed: {e}")
                    
            except Exception as e:
                print(f"{RED}✗{NC} Failed to process QKView {qkview_id}: {e}")
                processing_contexts.append(None)
        
        # Print summary
        print(f"\nCompleted batch processing: {successful_count}/{len(qkview_ids)} successful")
        
        if args.verbose or args.debug:
            print_processing_summary(processing_contexts)
            print(f"\n{GREEN}✓{NC} Token expires at: {auth.token_expires_at}")


def get_diagnostics_command(args):
    """Handle getting diagnostics for QKViews"""
    client, auth = get_authenticated_client(args.verbose, args.debug)
    
    # Import diagnostics module
    from ihealth_diagnostics import F5iHealthDiagnostics
    diagnostics = F5iHealthDiagnostics(auth)
    
    if args.id:
        # Get diagnostics for specific QKView ID
        print(f"Getting diagnostics for QKView {args.id}...")
        
        # Download all diagnostic reports
        files = diagnostics.download_diagnostic_reports(args.id)
        
        if any(files.values()):
            print(f"✓ Successfully downloaded diagnostics for QKView {args.id}")
            if args.verbose or args.debug:
                print("Downloaded files:")
                for file_type, filename in files.items():
                    if filename:
                        print(f"  {file_type}: {filename}")
        else:
            print(f"✗ Failed to download diagnostics for QKView {args.id}")
            sys.exit(1)
    else:
        # Get diagnostics for all QKViews
        print("Retrieving QKView list...")
        qkview_data = client.list_qkviews()
        
        if qkview_data is None:
            print("✗ Failed to retrieve QKViews")
            sys.exit(1)
        
        # Extract QKView IDs from the response
        qkview_ids = []
        if isinstance(qkview_data, dict) and 'id' in qkview_data:
            qkview_ids = qkview_data['id']
        elif isinstance(qkview_data, list):
            qkview_ids = qkview_data
        
        if not qkview_ids:
            print("No QKViews found to process")
            return
        
        print(f"\nGetting diagnostics for {len(qkview_ids)} QKView(s)...")
        
        # Process each QKView
        success_count = 0
        for i, qkview_id in enumerate(qkview_ids, 1):
            try:
                print(f"\n[{i}/{len(qkview_ids)}] Getting diagnostics for QKView {qkview_id}...")
                
                files = diagnostics.download_diagnostic_reports(qkview_id)
                
                if any(files.values()):
                    print(f"✓ Successfully downloaded diagnostics for QKView {qkview_id}")
                    success_count += 1
                else:
                    print(f"▲ No diagnostic files downloaded for QKView {qkview_id}")
                    
            except Exception as e:
                print(f"✗ Failed to get diagnostics for QKView {qkview_id}: {e}")
        
        print(f"\nCompleted diagnostics download: {success_count}/{len(qkview_ids)} successful")
        
        if args.verbose or args.debug:
            print(f"✓ Token expires at: {auth.token_expires_at}")


def list_local_command(args):
    """List locally created QKView directories (supports both hostname and ID-based)"""
    qkview_dirs = list_qkview_directories()
    
    if not qkview_dirs:
        print("No QKView directories found locally.")
        print("Use 'python bighealth.py process' to create them.")
    else:
        print(f"\nFound {len(qkview_dirs)} local QKView directories:")
        print("="*70)
        
        for dir_name, qkview_id, is_hostname_based in qkview_dirs:
            print(f"\n{dir_name} {'(hostname-based)' if is_hostname_based else '(legacy ID-based)'}")
            print(f"   QKView ID: {qkview_id}")
            
            # Find the actual directory path
            if is_hostname_based:
                qkview_path = os.path.join("QKViews", dir_name)
            else:
                qkview_path = os.path.join("QKViews", str(qkview_id))
            
            # Check if metadata exists
            metadata_file = os.path.join(qkview_path, "metadata.json")
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    created_time = metadata.get('created_timestamp', 'Unknown')
                    if created_time != 'Unknown':
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                            created_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                    
                    print(f"   Created: {created_time}")
                    print(f"   Status: {metadata.get('processing_status', {})}")
                    
                    # Show hostname info
                    hostname = metadata.get('hostname', 'Unknown')
                    if hostname != 'Unknown':
                        print(f"   Hostname: {hostname}")
                    
                    # Show QKView file info if available
                    if 'qkview_file' in metadata:
                        qkview_file = metadata['qkview_file']
                        print(f"   QKView File: {qkview_file.get('filename', 'Unknown')}")
                        if 'file_size' in qkview_file:
                            size_mb = qkview_file['file_size'] / (1024 * 1024)
                            print(f"   File Size: {qkview_file['file_size']:,} bytes ({size_mb:.1f} MB)")
                except:
                    print("   Status: ▲ Metadata file corrupted")
            else:
                print("   Status: ▲ No metadata file")
            
            # Check for QKView files
            if os.path.exists(qkview_path):
                qkview_files = [f for f in os.listdir(qkview_path) if f.endswith('.qkview')]
                if qkview_files:
                    print(f"   QKView Files: {', '.join(qkview_files)}")


def main():
    parser = argparse.ArgumentParser(
        description='BigHealth - F5 iHealth API Tool (Enhanced with Metadata-First)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Commands:
    list                        List available QKViews from API (read-only)
    process                     Process QKViews with metadata-first approach
    get diagnostics             Download diagnostic reports (PDF/CSV) for QKViews
    local                       List local QKView directories

Enhanced Features:
    • Metadata-first processing for better reliability
    • Hostname-based directory structure
    • Smart QKView file downloading with size validation
    • Improved error handling and progress reporting

Examples:
    python bighealth.py list                         # List QKViews
    python bighealth.py list --json-only             # List with JSON output
    python bighealth.py process                      # Process all QKViews (metadata-first)
    python bighealth.py process --id 24821984        # Process specific QKView
    python bighealth.py get diagnostics              # Get diagnostics for all QKViews
    python bighealth.py get diagnostics --id 24821984 # Get diagnostics for specific QKView
    python bighealth.py local                        # Show local directories
        '''
    )
    
    # Global options
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('-vvv', '--debug', action='store_true',
                       help='Enable debug output (very verbose)')
    parser.add_argument('--version', action='version', version='BigHealth 0.2.0-metadata-first')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command - read-only, just shows what's available
    list_parser = subparsers.add_parser('list', help='List QKViews from API (read-only)')
    list_parser.add_argument('--json-only', action='store_true',
                           help='Output only raw JSON response')
    
    # Process command - metadata-first approach
    process_parser = subparsers.add_parser('process', help='Process QKViews with metadata-first approach')
    process_parser.add_argument('--id', type=str, 
                              help='Process specific QKView ID (otherwise processes all)')
    
    # Get command - for getting specific data types
    get_parser = subparsers.add_parser('get', help='Get specific data from QKViews')
    get_subparsers = get_parser.add_subparsers(dest='get_type', help='Data type to get')
    
    # Get diagnostics subcommand
    diagnostics_parser = get_subparsers.add_parser('diagnostics', help='Download diagnostic reports')
    diagnostics_parser.add_argument('--id', type=str,
                                   help='Get diagnostics for specific QKView ID (otherwise gets all)')
    
    # Local command - shows local directories
    local_parser = subparsers.add_parser('local', help='List local QKView directories')
    
    args = parser.parse_args()
    
    # If no command specified, default to list
    if not args.command:
        args.command = 'list'
        args.json_only = False
    
    # Route to appropriate handler
    if args.command == 'list':
        list_qkviews_command(args)
    elif args.command == 'process':
        process_qkviews_command(args)
    elif args.command == 'get':
        if hasattr(args, 'get_type') and args.get_type == 'diagnostics':
            get_diagnostics_command(args)
        else:
            print("Available get commands: diagnostics")
            print("Usage: python bighealth.py get diagnostics [--id QKVIEW_ID]")
    elif args.command == 'local':
        list_local_command(args)
    else:
        print("Available commands: list, process, get, local")
        print("For help: python bighealth.py --help")


if __name__ == "__main__":
    main()


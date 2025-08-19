#!/usr/bin/env python3
"""
BigHealth - F5 iHealth API Command Line Tool

Main script for interacting with F5 iHealth API.
"""

import sys
import os
import argparse
import json

# Add modules directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

from ihealth_auth import F5iHealthAuth, load_credentials_from_files, get_credentials_interactive
from ihealth_utils import F5iHealthClient, print_qkview_summary
from qkview_directory_utils import list_qkview_directories, initialize_qkview_processing


def get_authenticated_client(verbose=False):
    """Get authenticated client - common function for all commands"""
    # Get credentials
    client_id, client_secret = load_credentials_from_files(
        os.path.join('credentials', 'cid'),
        os.path.join('credentials', 'cs')
    )
    
    if not client_id or not client_secret:
        if verbose:
            print("Credential files not found, prompting for input...")
        client_id, client_secret = get_credentials_interactive()
    
    if not client_id or not client_secret:
        print("✗ Client ID and Client Secret are required")
        print("\nTo get credentials:")
        print("1. Log in to https://ihealth2.f5.com")
        print("2. Go to Settings")
        print("3. Generate Client ID and Client Secret")
        print("4. Save them:")
        print("   echo 'your_client_id' > credentials/cid")
        print("   echo 'your_client_secret' > credentials/cs")
        sys.exit(1)
    
    if verbose:
        print(f"Using Client ID: {client_id[:8]}...")
    
    # Authenticate
    print("Authenticating with F5 iHealth API...")
    auth = F5iHealthAuth(client_id, client_secret)
    
    if not auth.authenticate():
        print("✗ Authentication failed")
        sys.exit(1)
    
    return F5iHealthClient(auth), auth


def list_qkviews_command(args):
    """Handle the list QKViews command - just shows what's available"""
    client, auth = get_authenticated_client(args.verbose)
    
    # Get QKViews
    print("Retrieving QKViews...")
    qkview_data = client.list_qkviews()
    
    if qkview_data is None:
        print("✗ Failed to retrieve QKViews")
        sys.exit(1)
    
    # Display results
    if args.json_only:
        print(json.dumps(qkview_data, indent=2))
    else:
        print_qkview_summary(qkview_data, show_raw=args.verbose)
        
        if args.verbose:
            print(f"\n✓ Token expires at: {auth.token_expires_at}")


def process_qkviews_command(args):
    """Handle processing QKViews - creates directories and processes data"""
    client, auth = get_authenticated_client(args.verbose)
    
    if args.id:
        # Process specific QKView ID
        print(f"Processing QKView {args.id}...")
        qkview_details = client.process_qkview(args.id, create_directories=True)
        
        if qkview_details:
            print(f"✓ Successfully processed QKView {args.id}")
            
            # Auto-process diagnostics as part of processing
            print("Processing diagnostics...")
            try:
                from ihealth_diagnostics import F5iHealthDiagnostics
                diagnostics = F5iHealthDiagnostics(auth)
                files = diagnostics.download_diagnostic_reports(args.id)
                
                if any(files.values()):
                    print("✓ Diagnostics processed successfully")
                else:
                    print("⚠ Diagnostics processing had issues")
            except Exception as e:
                print(f"⚠ Diagnostics processing failed: {e}")
            
            if args.verbose:
                print(json.dumps(qkview_details, indent=2))
        else:
            print(f"✗ Failed to process QKView {args.id}")
            sys.exit(1)
    else:
        # Process all QKViews
        print("Retrieving QKViews...")
        qkview_data = client.list_qkviews()
        
        if qkview_data is None:
            print("✗ Failed to retrieve QKViews")
            sys.exit(1)
        
        if args.verbose:
            print(f"DEBUG: QKView data type: {type(qkview_data)}")
            print(f"DEBUG: QKView data: {qkview_data}")
        
        # Extract QKView IDs from the response
        qkview_ids = []
        if isinstance(qkview_data, dict) and 'id' in qkview_data:
            qkview_ids = qkview_data['id']
            if args.verbose:
                print(f"DEBUG: Found QKView IDs in 'id' field: {qkview_ids}")
        elif isinstance(qkview_data, list):
            qkview_ids = qkview_data
            if args.verbose:
                print(f"DEBUG: QKView data is a list: {qkview_ids}")
        else:
            if args.verbose:
                print(f"DEBUG: Unexpected QKView data structure")
        
        if not qkview_ids:
            print("No QKViews found to process")
            print(f"DEBUG: qkview_data was: {qkview_data}")
            return
        
        print(f"\nProcessing {len(qkview_ids)} QKView(s)...")
        
        # Import diagnostics module for batch processing
        from ihealth_diagnostics import F5iHealthDiagnostics
        diagnostics = F5iHealthDiagnostics(auth)
        
        # Process each QKView
        for i, qkview_id in enumerate(qkview_ids, 1):
            try:
                print(f"\n[{i}/{len(qkview_ids)}] Processing QKView {qkview_id}...")
                
                # Get detailed info and create directories
                qkview_details = client.get_qkview_details(qkview_id)
                
                if qkview_details:
                    initialize_qkview_processing(qkview_id, qkview_details)
                    print(f"✓ Successfully processed QKView {qkview_id}")
                    
                    # Process diagnostics as part of full processing
                    print("  Processing diagnostics...")
                    try:
                        files = diagnostics.download_diagnostic_reports(qkview_id)
                        if any(files.values()):
                            print("  ✓ Diagnostics processed")
                        else:
                            print("  ⚠ Diagnostics had issues")
                    except Exception as e:
                        print(f"  ⚠ Diagnostics failed: {e}")
                else:
                    print(f"⚠ Could not get details for QKView {qkview_id}")
                    
            except Exception as e:
                print(f"✗ Failed to process QKView {qkview_id}: {e}")
        
        print(f"\n✓ Completed processing {len(qkview_ids)} QKView(s)")
        
        if args.verbose:
            print(f"✓ Token expires at: {auth.token_expires_at}")


def get_diagnostics_command(args):
    """Handle getting diagnostics for QKViews"""
    client, auth = get_authenticated_client(args.verbose)
    
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
            if args.verbose:
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
                    print(f"⚠ No diagnostic files downloaded for QKView {qkview_id}")
                    
            except Exception as e:
                print(f"✗ Failed to get diagnostics for QKView {qkview_id}: {e}")
        
        print(f"\n✓ Completed diagnostics download: {success_count}/{len(qkview_ids)} successful")
        
        if args.verbose:
            print(f"✓ Token expires at: {auth.token_expires_at}")


def list_local_command(args):
    """List locally created QKView directories"""
    qkview_dirs = list_qkview_directories()
    
    if not qkview_dirs:
        print("No QKView directories found locally.")
        print("Use 'python bighealth.py process' to create them.")
    else:
        print(f"\nFound {len(qkview_dirs)} local QKView directories:")
        print("="*50)
        for qkview_id in qkview_dirs:
            print(f"QKView ID: {qkview_id}")
            qkview_path = os.path.join("QKViews", qkview_id)
            
            # Check if metadata exists
            metadata_file = os.path.join(qkview_path, "metadata.json")
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    print(f"  Created: {metadata.get('created_timestamp', 'Unknown')}")
                    print(f"  Status: {metadata.get('processing_status', {})}")
                except:
                    print("  Status: Metadata file corrupted")
            else:
                print("  Status: No metadata file")
            print()


def main():
    parser = argparse.ArgumentParser(
        description='BigHealth - F5 iHealth API Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Commands:
    list                        List available QKViews from API (read-only)
    process                     Process QKViews - create directories and download data
    get diagnostics             Download diagnostic reports (PDF/CSV) for QKViews
    local                       List local QKView directories

Examples:
    python bighealth.py list                         # Just list QKViews
    python bighealth.py list --json-only             # List with JSON output
    python bighealth.py process                      # Process all QKViews (includes diagnostics)
    python bighealth.py process --id 24821984        # Process specific QKView
    python bighealth.py get diagnostics              # Get diagnostics for all QKViews
    python bighealth.py get diagnostics --id 24821984 # Get diagnostics for specific QKView
    python bighealth.py local                        # Show local directories
        '''
    )
    
    # Global options
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--version', action='version', version='BigHealth 0.1.0')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command - read-only, just shows what's available
    list_parser = subparsers.add_parser('list', help='List QKViews from API (read-only)')
    list_parser.add_argument('--json-only', action='store_true',
                           help='Output only raw JSON response')
    
    # Process command - does the work, creates directories and processes all data
    process_parser = subparsers.add_parser('process', help='Process QKViews - create directories and download all data')
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


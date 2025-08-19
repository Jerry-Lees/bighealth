# BigHealth - F5 iHealth API Tool

A modular Python command-line tool for interacting with the F5 iHealth API. BigHealth allows you to automate the download and organization of diagnostic data, configuration files, logs, and other information from your F5 BIG-IP QKViews.

## 🎯 Features

- **OAuth2 Authentication** - Modern API authentication with automatic token refresh
- **Modular Architecture** - Organized around F5 iHealth web interface menu structure
- **Automatic Directory Organization** - Creates structured directories for each QKView
- **Comprehensive Diagnostics** - Downloads PDF, CSV, and JSON diagnostic reports for issues found
- **Hostname-based File Naming** - Uses actual device hostnames for intuitive file organization
- **Progress Tracking** - Visual feedback and metadata tracking for all operations
- **Secure Credential Storage** - Git-ignored credential files for security

## 📋 Prerequisites

### Automated Installation
If using the automated installer script, no prerequisites needed! The script handles everything automatically.

### Manual Installation
- Python 3.7+
- F5 iHealth account with API access
- `requests` library

## 🚀 Quick Start

### Automated Installation (Recommended)

The easiest way to install BigHealth is using our cross-platform installer script:

```bash
# One-command installation for Linux and macOS
curl -sSL https://raw.githubusercontent.com/Jerry-Lees/bighealth/main/install.sh | bash
```

**Supported Systems:**
- **Linux**: Ubuntu/Debian, Fedora/RHEL/CentOS, openSUSE, Arch Linux
- **macOS**: All versions (with automatic Homebrew setup)

The installer will:
- ✅ Detect your operating system and package manager
- ✅ Install Python 3 and all required dependencies
- ✅ Download BigHealth from GitHub
- ✅ Set up an isolated Python virtual environment
- ✅ Guide you through F5 iHealth API credential setup
- ✅ Create helper scripts for easy daily use
- ✅ Test the installation to ensure everything works

### Manual Installation

If you prefer to install manually:

#### 1. Clone and Setup

```bash
git clone https://github.com/Jerry-Lees/bighealth.git
cd bighealth
pip install -r requirements.txt
```

#### 2. Get F5 iHealth API Credentials

1. Log in to [F5 iHealth](https://ihealth2.f5.com)
2. Navigate to **Settings**
3. Click **Generate Client ID and Client Secret**
4. Copy both values

#### 3. Configure Credentials

```bash
echo "your_client_id" > credentials/cid
echo "your_client_secret" > credentials/cs
chmod 600 credentials/cid credentials/cs
```

#### 4. Test Your Setup

```bash
# List available QKViews
python bighealth.py list

# Process everything (creates directories + downloads diagnostics)
python bighealth.py process
```

## 📖 Command Reference

### Commands Overview

| Command | Description | What It Does |
|---------|-------------|--------------|
| `list` | List available QKViews (read-only) | Shows QKViews in your iHealth account |
| `process` | Full processing pipeline | Creates directories + downloads diagnostics for all QKViews |
| `get diagnostics` | Download diagnostic reports only | Downloads PDF/CSV/JSON diagnostic reports |
| `local` | Show local QKView directories | Lists locally processed QKViews and their status |

### Global Options

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Enable verbose output (shows progress details) |
| `-vvv, --debug` | Enable debug output (very verbose, shows API responses) |
| `--version` | Show version information |
| `-h, --help` | Show help message |

### Command Details

#### `list` - List QKViews (Read-Only)

Lists QKViews available in your F5 iHealth account without making any changes.

```bash
# Basic listing
python bighealth.py list

# Verbose output with token info
python bighealth.py -v list

# JSON output only (for scripting)
python bighealth.py list --json-only

# Debug mode (shows API responses)
python bighealth.py -vvv list
```

**Options:**
- `--json-only` - Output raw JSON response instead of formatted display

**Example Output:**
```
F5 IHEALTH QKVIEW LISTING
================================================================================
FOUND 4 QKVIEW ID(S) in 'id':
================================================================================
QKVIEW ID #1: 24821984
QKVIEW ID #2: 24821980
QKVIEW ID #3: 24821972
QKVIEW ID #4: 24821968
```

#### `process` - Full Processing Pipeline

Creates directory structures and downloads all available data for QKViews. This is the "do everything" command.

```bash
# Process all QKViews
python bighealth.py process

# Process specific QKView
python bighealth.py process --id 24821984

# Process with verbose output
python bighealth.py -v process

# Process with debug output
python bighealth.py -vvv process --id 24821984
```

**Options:**
- `--id QKVIEW_ID` - Process only the specified QKView ID

**What It Creates:**
- Directory structure for each QKView
- Downloads diagnostic reports (PDF, CSV, JSON)
- Creates metadata and documentation files
- Updates processing status

#### `get diagnostics` - Download Diagnostic Reports

Downloads diagnostic reports for issues found on devices. Gets PDF, CSV, and JSON formats.

```bash
# Download diagnostics for all QKViews
python bighealth.py get diagnostics

# Download diagnostics for specific QKView
python bighealth.py get diagnostics --id 24821984

# Download with verbose output
python bighealth.py -v get diagnostics --id 24821984
```

**Options:**
- `--id QKVIEW_ID` - Download diagnostics for specific QKView only

**Files Downloaded:**
- `hostname.pdf` - Visual diagnostic report of issues found
- `hostname.csv` - Spreadsheet-friendly data of issues found
- `diagnostics_hit.json` - JSON data for programmatic access
- `diagnostic_summary.json` - Summary with issue counts by severity

#### `local` - Show Local Status

Lists locally processed QKView directories and their processing status.

```bash
# Show local directories
python bighealth.py local

# Show with verbose output  
python bighealth.py -v local
```

**Example Output:**
```
Found 4 local QKView directories:
==================================================
QKView ID: 24821984
  Created: 2025-08-19T13:45:12.123456
  Status: {'diagnostics': True}

QKView ID: 24821980
  Created: 2025-08-19T13:46:15.789012
  Status: {'diagnostics': True}
```

## 📁 Directory Structure

BigHealth automatically creates organized directories for each QKView:

```
QKViews/
├── 24821984/                          # QKView ID
│   ├── metadata.json                  # Processing metadata and status
│   ├── Diagnostics/
│   │   ├── bigip-lab01.lees-family.io.pdf    # Issues found (PDF format)
│   │   ├── bigip-lab01.lees-family.io.csv    # Issues found (CSV format)
│   │   ├── diagnostics_hit.json             # Issues found (JSON for scripting)
│   │   └── diagnostic_summary.json          # Issue summary by severity
│   ├── LTM/                           # Local Traffic Manager (future)
│   ├── GTM/                           # Global Traffic Manager (future)
│   ├── APM/                           # Access Policy Manager (future)
│   ├── ASM/                           # Application Security Manager (future)
│   ├── iRules/                        # iRule scripts (future)
│   ├── System/                        # Hardware/platform info (future)
│   ├── Configuration/                 # Config files (future)
│   ├── Logs/                          # Log files (future)
│   └── Docs/
│       ├── README.md                  # Directory documentation
│       └── api_response.json          # Raw API response
├── 24821980/                          # Another QKView
│   └── ... (same structure)
└── 24821972/                          # Another QKView
    └── ... (same structure)
```

## 🔧 Configuration

### Credential Files

BigHealth looks for API credentials in these files:

- `credentials/cid` - F5 iHealth API Client ID
- `credentials/cs` - F5 iHealth API Client Secret

These files are automatically ignored by git for security.

### Environment Variables (Alternative)

You can also use environment variables:

```bash
export F5_IHEALTH_CLIENT_ID="your_client_id"
export F5_IHEALTH_CLIENT_SECRET="your_client_secret"
```

## 🏗️ Architecture

### Core Modules

- **`bighealth.py`** - Main command-line interface and argument parsing
- **`modules/ihealth_auth.py`** - OAuth2 authentication and session management
- **`modules/ihealth_utils.py`** - Base API client and common utilities
- **`modules/qkview_directory_utils.py`** - Directory structure management

### Feature Modules

- **`modules/ihealth_diagnostics.py`** - Diagnostic reports and health checks ✅ **Complete**
- **`modules/ihealth_status.py`** - System/hardware status (planned)
- **`modules/ihealth_config_explorer.py`** - Configuration analysis (planned)
- **`modules/ihealth_commands.py`** - BIG-IP command outputs (planned)
- **`modules/ihealth_graphs.py`** - Performance visualizations (planned)
- **`modules/ihealth_files.py`** - File operations (planned)
- **`modules/ihealth_iapps.py`** - iApp analysis (planned)
- **`modules/ihealth_log_search.py`** - Log searching (planned)

## 📊 Current Implementation Status

| Feature | Status | Description |
|---------|--------|-------------|
| **Authentication** | ✅ Complete | OAuth2 with automatic token refresh |
| **QKView Listing** | ✅ Complete | List and enumerate QKViews |
| **Directory Management** | ✅ Complete | Automated directory creation and organization |
| **Diagnostics** | ✅ Complete | PDF/CSV/JSON diagnostic reports for issues found |
| **Status Tracking** | ✅ Complete | Metadata and processing status |
| System Status | 🚧 Planned | Hardware/software status information |
| Configuration Explorer | 🚧 Planned | Config file analysis and comparison |
| Commands | 🚧 Planned | BIG-IP command output access |
| Graphs | 🚧 Planned | Performance graphs and visualizations |
| Files | 🚧 Planned | File browsing and download operations |
| iApps | 🚧 Planned | iApp template and service analysis |
| Log Search | 🚧 Planned | Log file searching and analysis |

## 🔍 File Types Created

### Diagnostic Files

| File | Format | Contains |
|------|--------|----------|
| `hostname.pdf` | PDF | Visual diagnostic report of issues found on device |
| `hostname.csv` | CSV | Spreadsheet-friendly data of issues found |
| `diagnostics_hit.json` | JSON | Structured diagnostic data for scripting/automation |
| `diagnostic_summary.json` | JSON | Issue counts by severity (critical, high, medium, low) |

### Metadata Files

| File | Format | Contains |
|------|--------|----------|
| `metadata.json` | JSON | Processing timestamps, status, file inventory |
| `README.md` | Markdown | Human-readable directory documentation |
| `api_response.json` | JSON | Raw API response for debugging |

## 🔒 Security

- **Credential Protection**: API credentials stored in git-ignored files with 600 permissions
- **OAuth2 Security**: Uses modern OAuth2 flow with bearer tokens
- **Token Management**: Automatic token refresh prevents credential exposure
- **No Logging**: Credentials are never logged or displayed in output
- **HTTPS Only**: All API communication uses encrypted connections

## 💡 Usage Examples

### Daily Operations

```bash
# Activate BigHealth environment (if manually installed)
cd ~/bighealth
source bighealth_env/bin/activate

# OR use helper scripts (available after automated installation)
./scripts/run.sh list

# Quick check of available QKViews
python bighealth.py list

# Full processing of all QKViews (typical daily use)
python bighealth.py process

# Check what's been processed locally
python bighealth.py local
```

### Troubleshooting Specific Device

```bash
# Process specific problematic device
python bighealth.py process --id 24821984

# Get just diagnostics for quick analysis
python bighealth.py get diagnostics --id 24821984

# Review diagnostic summary
cat QKViews/24821984/Diagnostics/diagnostic_summary.json
```

### Scripting and Automation

```bash
# Get raw JSON for parsing in scripts
python bighealth.py list --json-only > qkviews.json

# Process with detailed logging for automation
python bighealth.py -v process > processing.log 2>&1

# Debug API issues
python bighealth.py -vvv get diagnostics --id 24821984
```

## 🐛 Troubleshooting

### Common Issues

**Installation Problems**
```bash
# Re-run the automated installer
curl -sSL https://raw.githubusercontent.com/Jerry-Lees/bighealth/main/install.sh | bash

# Or check system requirements manually
python3 --version  # Should be 3.7+
pip3 --version     # Should be available
```

**Authentication Failed (401)**
```bash
# Check your credentials
cat credentials/cid
cat credentials/cs

# Regenerate credentials in F5 iHealth web interface
# Or use the helper script (if installed via automated installer)
./scripts/setup_credentials.sh

# Ensure files have correct permissions
chmod 600 credentials/cid credentials/cs
```

**No QKViews Found**
```bash
# Verify you have QKViews uploaded to iHealth
python bighealth.py -vvv list
```

**JSON Parsing Errors**
```bash
# Usually transient API issues, try again
# Check debug output for details
python bighealth.py -vvv list
```

**Permission Denied**
```bash
# Fix credential file permissions
chmod 600 credentials/cid credentials/cs

# Ensure QKViews directory is writable
ls -la QKViews/
```

**Module Import Errors**
```bash
# If using manual installation, ensure you're in the correct directory
ls -la modules/
python -c "import sys; print(sys.path)"

# If using automated installation, activate the environment
source bighealth_env/bin/activate
# OR use helper scripts
./scripts/activate.sh
```

**Virtual Environment Issues (Manual Installation)**
```bash
# Recreate virtual environment
rm -rf bighealth_env
python3 -m venv bighealth_env
source bighealth_env/bin/activate
pip install -r requirements.txt
```

### Debug Commands

```bash
# Show detailed API responses
python bighealth.py -vvv list

# Check authentication details
python bighealth.py -v process --id 24821984

# Verify directory structure
python bighealth.py local

# Test credentials (automated installation)
./scripts/setup_credentials.sh

# Activate environment manually (automated installation)
source bighealth_env/bin/activate
```

## 📚 API Reference

### F5 iHealth API

This tool uses the F5 iHealth REST API:

- **Base URL**: `https://ihealth2-api.f5.com/qkview-analyzer/api`
- **Authentication**: `https://identity.account.f5.com/oauth2/ausp95ykc80HOU7SQ357/v1/token`
- **Documentation**: [F5 iHealth API Docs](https://clouddocs.f5.com/api/ihealth/)

### API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/qkviews` | GET | List all QKViews |
| `/qkviews/{id}` | GET | Get QKView details |
| `/qkviews/{id}/diagnostics?set=hit` | GET | Get diagnostic issues (JSON) |
| `/qkviews/{id}/diagnostics.pdf?set=hit` | GET | Get diagnostic issues (PDF) |
| `/qkviews/{id}/diagnostics.csv?set=hit` | GET | Get diagnostic issues (CSV) |

### Authentication Flow

1. **Client Credentials** → OAuth2 token request
2. **Bearer Token** → Used for all API calls  
3. **Token Refresh** → Automatic renewal before expiration
4. **Session Management** → Persistent authenticated session

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-module`)
3. Make your changes following the existing patterns
4. Test your changes with real QKViews
5. Commit your changes (`git commit -am 'Add new module'`)
6. Push to the branch (`git push origin feature/new-module`)
7. Create a Pull Request

### Development Guidelines

- **Follow existing patterns** - Use the same structure as `ihealth_diagnostics.py`
- **Inherit from F5iHealthClient** - All modules should extend the base client
- **Use `save_data_to_qkview()`** - For saving data to the directory structure
- **Update metadata** - Track processing status in `metadata.json`
- **Add error handling** - Graceful failure with informative messages
- **Document thoroughly** - Include docstrings and usage examples

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- F5 Networks for the iHealth API
- F5 DevCentral community for API examples and documentation
- Contributors and beta testers

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/bighealth/issues)
- **Documentation**: This README and inline code documentation
- **F5 iHealth**: [F5 Support Portal](https://support.f5.com)

---

**Note**: This tool is not officially supported by F5 Networks. It's a community-developed tool for automating F5 iHealth API interactions.

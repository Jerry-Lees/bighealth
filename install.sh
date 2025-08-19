#!/bin/bash

# BigHealth - F5 iHealth API Tool Installer
# Cross-platform installation script for Ubuntu/Debian, Fedora/RHEL, and macOS
# Sets up all prerequisites and guides through credential configuration

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Global variables
OS_TYPE=""
DISTRO=""
PACKAGE_MANAGER=""
PYTHON_CMD=""
PIP_CMD=""

# ASCII Art Banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                          BigHealth                            ║"
    echo "║               F5 iHealth API Tool Installer                   ║"
    echo "║                                                               ║"
    echo "║     Cross-platform setup for Linux and macOS systems        ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Progress indicator
print_step() {
    echo -e "\n${BLUE}[STEP $1]${NC} $2"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${PURPLE}ℹ${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root"
        print_info "Please run as a regular user. The script will use sudo when needed."
        exit 1
    fi
}

# Detect operating system and distribution
detect_os() {
    print_step "1" "Detecting operating system"
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS_TYPE="linux"
        
        # Detect Linux distribution
        if [[ -f /etc/os-release ]]; then
            source /etc/os-release
            case $ID in
                ubuntu|debian|linuxmint|pop)
                    DISTRO="debian"
                    PACKAGE_MANAGER="apt"
                    ;;
                fedora|rhel|centos|rocky|almalinux)
                    DISTRO="redhat"
                    PACKAGE_MANAGER="dnf"
                    # Check if dnf exists, fallback to yum
                    if ! command -v dnf &> /dev/null; then
                        PACKAGE_MANAGER="yum"
                    fi
                    ;;
                opensuse*|sles)
                    DISTRO="opensuse"
                    PACKAGE_MANAGER="zypper"
                    ;;
                arch|manjaro)
                    DISTRO="arch"
                    PACKAGE_MANAGER="pacman"
                    ;;
                *)
                    print_warning "Unknown Linux distribution: $ID"
                    print_info "Trying generic Linux approach..."
                    DISTRO="generic"
                    ;;
            esac
            print_success "Detected: $PRETTY_NAME"
        else
            print_warning "Cannot detect Linux distribution"
            DISTRO="generic"
        fi
        
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS_TYPE="macos"
        DISTRO="macos"
        local macos_version=$(sw_vers -productVersion)
        print_success "Detected: macOS $macos_version"
        
    else
        print_error "Unsupported operating system: $OSTYPE"
        print_info "This script supports Linux and macOS only"
        exit 1
    fi
}

# Detect Python command
detect_python() {
    print_info "Detecting Python installation..."
    
    # Try different Python commands
    for cmd in python3 python python3.11 python3.10 python3.9 python3.8; do
        if command -v "$cmd" &> /dev/null; then
            local version=$($cmd --version 2>&1)
            if [[ $version =~ Python\ 3\.[8-9]|Python\ 3\.1[0-9] ]]; then
                PYTHON_CMD="$cmd"
                print_success "Found compatible Python: $version ($cmd)"
                break
            fi
        fi
    done
    
    # Detect pip command
    for cmd in pip3 pip; do
        if command -v "$cmd" &> /dev/null; then
            PIP_CMD="$cmd"
            break
        fi
    done
}

# Update system packages
update_system() {
    print_step "2" "Updating system packages"
    
    case $PACKAGE_MANAGER in
        apt)
            print_info "Updating package lists..."
            sudo apt update
            print_info "Upgrading existing packages..."
            sudo apt upgrade -y
            ;;
        dnf)
            print_info "Updating packages with dnf..."
            sudo dnf update -y
            ;;
        yum)
            print_info "Updating packages with yum..."
            sudo yum update -y
            ;;
        zypper)
            print_info "Updating packages with zypper..."
            sudo zypper refresh
            sudo zypper update -y
            ;;
        pacman)
            print_info "Updating packages with pacman..."
            sudo pacman -Syu --noconfirm
            ;;
        *)
            if [[ $OS_TYPE == "macos" ]]; then
                print_info "macOS detected - skipping system update"
                print_info "Please ensure you have the latest Xcode Command Line Tools"
            else
                print_warning "Unknown package manager - skipping system update"
            fi
            ;;
    esac
    
    print_success "System packages updated"
}

# Install Homebrew on macOS
install_homebrew() {
    if [[ $OS_TYPE == "macos" ]] && ! command -v brew &> /dev/null; then
        print_info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH for Apple Silicon Macs
        if [[ -f /opt/homebrew/bin/brew ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
        
        print_success "Homebrew installed"
    fi
}

# Install Python and dependencies
install_python() {
    print_step "3" "Installing Python and dependencies"
    
    case $OS_TYPE in
        linux)
            case $PACKAGE_MANAGER in
                apt)
                    print_info "Installing Python and tools..."
                    sudo apt install -y \
                        python3 \
                        python3-pip \
                        python3-dev \
                        python3-venv \
                        python3-setuptools \
                        git \
                        curl \
                        wget \
                        unzip \
                        ca-certificates
                    ;;
                dnf)
                    print_info "Installing Python and tools..."
                    sudo dnf install -y \
                        python3 \
                        python3-pip \
                        python3-devel \
                        python3-virtualenv \
                        git \
                        curl \
                        wget \
                        unzip \
                        ca-certificates
                    ;;
                yum)
                    print_info "Installing Python and tools..."
                    sudo yum install -y \
                        python3 \
                        python3-pip \
                        python3-devel \
                        git \
                        curl \
                        wget \
                        unzip \
                        ca-certificates
                    ;;
                zypper)
                    print_info "Installing Python and tools..."
                    sudo zypper install -y \
                        python3 \
                        python3-pip \
                        python3-devel \
                        python3-virtualenv \
                        git \
                        curl \
                        wget \
                        unzip \
                        ca-certificates
                    ;;
                pacman)
                    print_info "Installing Python and tools..."
                    sudo pacman -S --noconfirm \
                        python \
                        python-pip \
                        git \
                        curl \
                        wget \
                        unzip \
                        ca-certificates
                    ;;
                *)
                    print_warning "Unknown package manager - attempting generic installation"
                    ;;
            esac
            ;;
        macos)
            install_homebrew
            if command -v brew &> /dev/null; then
                print_info "Installing Python and tools via Homebrew..."
                brew install python git curl wget
            else
                print_warning "Homebrew not available - using system Python"
            fi
            ;;
    esac
    
    # Re-detect Python after installation
    detect_python
    
    if [[ -z "$PYTHON_CMD" ]]; then
        print_error "Python 3.8+ not found after installation"
        print_info "Please install Python 3.8 or later manually"
        exit 1
    fi
    
    if [[ -z "$PIP_CMD" ]]; then
        print_error "pip not found after installation"
        print_info "Please install pip manually"
        exit 1
    fi
    
    print_success "Python environment ready"
    print_info "Using Python: $PYTHON_CMD"
    print_info "Using pip: $PIP_CMD"
}

# Clone BigHealth repository
clone_repository() {
    print_step "4" "Downloading BigHealth"
    
    local install_dir="$HOME/bighealth"
    
    if [[ -d "$install_dir" ]]; then
        print_warning "BigHealth directory already exists at $install_dir"
        echo -n "Do you want to remove it and reinstall? (y/N): "
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            rm -rf "$install_dir"
            print_info "Removed existing installation"
        else
            print_info "Using existing directory"
            cd "$install_dir"
            git pull origin main
            print_success "Updated existing installation"
            return
        fi
    fi
    
    print_info "Cloning BigHealth repository..."
    git clone https://github.com/Jerry-Lees/bighealth.git "$install_dir"
    cd "$install_dir"
    
    print_success "BigHealth downloaded to $install_dir"
}

# Set up Python virtual environment
setup_virtualenv() {
    print_step "5" "Setting up Python virtual environment"
    
    print_info "Creating virtual environment..."
    $PYTHON_CMD -m venv bighealth_env
    
    # Determine activation script path
    local activate_script=""
    if [[ $OS_TYPE == "macos" ]] || [[ $OS_TYPE == "linux" ]]; then
        activate_script="bighealth_env/bin/activate"
    else
        print_error "Unknown OS type for virtual environment setup"
        exit 1
    fi
    
    print_info "Activating virtual environment..."
    source "$activate_script"
    
    print_info "Upgrading pip..."
    python -m pip install --upgrade pip
    
    print_info "Installing Python requirements..."
    pip install -r requirements.txt
    
    print_success "Virtual environment configured"
}

# Set up credentials
setup_credentials() {
    print_step "6" "Setting up F5 iHealth API credentials"
    
    echo -e "\n${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                   CREDENTIAL SETUP                              ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}\n"
    
    print_info "To use BigHealth, you need F5 iHealth API credentials."
    print_info "Follow these steps to get your credentials:\n"
    
    echo -e "${YELLOW}1.${NC} Open your web browser and go to: ${BLUE}https://ihealth2.f5.com${NC}"
    echo -e "${YELLOW}2.${NC} Log in with your F5 account"
    echo -e "${YELLOW}3.${NC} Navigate to ${BLUE}Settings${NC}"
    echo -e "${YELLOW}4.${NC} Click ${BLUE}Generate Client ID and Client Secret${NC}"
    echo -e "${YELLOW}5.${NC} Copy both values (they will only be shown once!)\n"
    
    # Create credentials directory
    mkdir -p credentials
    
    # Get Client ID
    echo -n "Enter your F5 iHealth Client ID: "
    read -r client_id
    
    if [[ -z "$client_id" ]]; then
        print_error "Client ID cannot be empty"
        print_info "You can set credentials later by running: $PWD/scripts/setup_credentials.sh"
        return 1
    fi
    
    # Get Client Secret (hidden input)
    echo -n "Enter your F5 iHealth Client Secret (input will be hidden): "
    read -rs client_secret
    echo
    
    if [[ -z "$client_secret" ]]; then
        print_error "Client Secret cannot be empty"
        print_info "You can set credentials later by running: $PWD/scripts/setup_credentials.sh"
        return 1
    fi
    
    # Save credentials
    echo "$client_id" > credentials/cid
    echo "$client_secret" > credentials/cs
    
    # Set secure permissions
    chmod 600 credentials/cid credentials/cs
    
    print_success "Credentials saved securely"
    print_info "Credential files:"
    print_info "  Client ID: $PWD/credentials/cid"
    print_info "  Client Secret: $PWD/credentials/cs"
}

# Create helper scripts
create_helper_scripts() {
    print_step "7" "Creating helper scripts"
    
    mkdir -p scripts
    
    # Determine shell activation script
    local activate_cmd=""
    if [[ $OS_TYPE == "macos" ]] || [[ $OS_TYPE == "linux" ]]; then
        activate_cmd="source bighealth_env/bin/activate"
    fi
    
    # Create activation script
    cat > scripts/activate.sh << EOF
#!/bin/bash
# Activate BigHealth environment
cd "\$(dirname "\$0")/.."
$activate_cmd
echo "BigHealth environment activated!"
echo "Usage examples:"
echo "  python bighealth.py list"
echo "  python bighealth.py process"
echo "  python bighealth.py get diagnostics"
EOF
    
    # Create credential setup script
    cat > scripts/setup_credentials.sh << 'EOF'
#!/bin/bash
# Set up F5 iHealth API credentials
cd "$(dirname "$0")/.."

echo "F5 iHealth API Credential Setup"
echo "================================"
echo
echo "To get your credentials:"
echo "1. Go to https://ihealth2.f5.com"
echo "2. Log in with your F5 account"
echo "3. Navigate to Settings"
echo "4. Click 'Generate Client ID and Client Secret'"
echo "5. Copy both values"
echo

mkdir -p credentials

echo -n "Enter your F5 iHealth Client ID: "
read -r client_id

echo -n "Enter your F5 iHealth Client Secret (hidden): "
read -rs client_secret
echo

if [[ -n "$client_id" && -n "$client_secret" ]]; then
    echo "$client_id" > credentials/cid
    echo "$client_secret" > credentials/cs
    chmod 600 credentials/cid credentials/cs
    echo "✓ Credentials saved successfully!"
else
    echo "✗ Error: Both Client ID and Secret are required"
    exit 1
fi
EOF
    
    # Create run script
    cat > scripts/run.sh << EOF
#!/bin/bash
# Run BigHealth with environment activated
cd "\$(dirname "\$0")/.."
$activate_cmd
python bighealth.py "\$@"
EOF
    
    # Create macOS-specific scripts if on macOS
    if [[ $OS_TYPE == "macos" ]]; then
        # Create .command file for double-click execution
        cat > "BigHealth.command" << EOF
#!/bin/bash
cd "\$(dirname "\$0")"
$activate_cmd
echo "BigHealth F5 iHealth API Tool"
echo "============================"
echo "Available commands:"
echo "  list     - List QKViews"
echo "  process  - Process all QKViews"
echo "  get diagnostics - Download diagnostics"
echo "  local    - Show local data"
echo
echo -n "Enter command (or 'exit' to quit): "
read -r cmd
case \$cmd in
    list|process|local)
        python bighealth.py \$cmd
        ;;
    "get diagnostics")
        python bighealth.py get diagnostics
        ;;
    exit)
        exit 0
        ;;
    *)
        python bighealth.py \$cmd
        ;;
esac
echo
echo "Press any key to exit..."
read -n 1
EOF
        chmod +x "BigHealth.command"
        print_success "Created macOS .command file for double-click execution"
    fi
    
    # Make scripts executable
    chmod +x scripts/*.sh
    
    print_success "Helper scripts created"
}

# Test installation
test_installation() {
    print_step "8" "Testing installation"
    
    # Determine activation command
    local activate_cmd=""
    if [[ $OS_TYPE == "macos" ]] || [[ $OS_TYPE == "linux" ]]; then
        activate_cmd="source bighealth_env/bin/activate"
    fi
    
    # Activate environment
    eval "$activate_cmd"
    
    print_info "Testing BigHealth installation..."
    
    # Test import
    if python -c "import requests" 2>/dev/null; then
        print_success "Python dependencies are working"
    else
        print_error "Python dependencies test failed"
        return 1
    fi
    
    # Test BigHealth
    if python bighealth.py --version 2>/dev/null; then
        print_success "BigHealth is working"
    else
        print_error "BigHealth test failed"
        return 1
    fi
    
    # Test credentials if they exist
    if [[ -f credentials/cid && -f credentials/cs ]]; then
        print_info "Testing API credentials..."
        if timeout 30 python bighealth.py list 2>/dev/null; then
            print_success "API credentials are working"
        else
            print_warning "API test failed or timed out - check your credentials"
            print_info "You can update credentials by running: $PWD/scripts/setup_credentials.sh"
        fi
    else
        print_warning "No credentials found - skipping API test"
    fi
    
    print_success "Installation test completed"
}

# Print usage instructions
print_usage() {
    echo -e "\n${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                    INSTALLATION COMPLETE!                       ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}\n"
    
    print_success "BigHealth has been successfully installed!"
    
    echo -e "\n${YELLOW}📁 Installation Directory:${NC}"
    echo -e "   $PWD\n"
    
    echo -e "${YELLOW}🚀 Quick Start:${NC}"
    if [[ $OS_TYPE == "macos" ]]; then
        echo -e "   ${BLUE}cd $PWD${NC}"
        echo -e "   ${BLUE}source bighealth_env/bin/activate${NC}"
        echo -e "   ${BLUE}python bighealth.py list${NC}"
        echo -e "   ${BLUE}# OR double-click BigHealth.command${NC}\n"
    else
        echo -e "   ${BLUE}cd $PWD${NC}"
        echo -e "   ${BLUE}source bighealth_env/bin/activate${NC}"
        echo -e "   ${BLUE}python bighealth.py list${NC}\n"
    fi
    
    echo -e "${YELLOW}📝 Available Commands:${NC}"
    echo -e "   ${BLUE}python bighealth.py list${NC}                    # List QKViews"
    echo -e "   ${BLUE}python bighealth.py process${NC}                 # Process all QKViews"
    echo -e "   ${BLUE}python bighealth.py get diagnostics${NC}         # Download diagnostics"
    echo -e "   ${BLUE}python bighealth.py local${NC}                   # Show local data\n"
    
    echo -e "${YELLOW}🛠 Helper Scripts:${NC}"
    echo -e "   ${BLUE}./scripts/activate.sh${NC}                      # Activate environment"
    echo -e "   ${BLUE}./scripts/run.sh list${NC}                      # Run BigHealth commands"
    echo -e "   ${BLUE}./scripts/setup_credentials.sh${NC}             # Update credentials\n"
    
    echo -e "${YELLOW}📖 Documentation:${NC}"
    echo -e "   ${BLUE}README.md${NC}                                  # Full documentation"
    echo -e "   ${BLUE}https://github.com/Jerry-Lees/bighealth${NC}    # GitHub repository\n"
    
    echo -e "${YELLOW}💻 System Information:${NC}"
    echo -e "   ${BLUE}OS:${NC} $OS_TYPE ($DISTRO)"
    echo -e "   ${BLUE}Python:${NC} $PYTHON_CMD"
    echo -e "   ${BLUE}Package Manager:${NC} $PACKAGE_MANAGER\n"
    
    echo -e "${YELLOW}🔧 Troubleshooting:${NC}"
    echo -e "   ${BLUE}python bighealth.py -vvv list${NC}              # Debug mode"
    echo -e "   ${BLUE}./scripts/setup_credentials.sh${NC}             # Fix credentials\n"
}

# Create desktop shortcut (Linux only)
create_desktop_shortcut() {
    if [[ $OS_TYPE == "linux" ]] && [[ -d "$HOME/Desktop" ]]; then
        echo -n "Create desktop shortcut? (y/N): "
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            cat > "$HOME/Desktop/BigHealth.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=BigHealth
Comment=F5 iHealth API Tool
Exec=gnome-terminal -- bash -c "cd $PWD && source bighealth_env/bin/activate && python bighealth.py list; exec bash"
Icon=utilities-terminal
Terminal=false
Categories=Development;
EOF
            chmod +x "$HOME/Desktop/BigHealth.desktop"
            print_success "Desktop shortcut created"
        fi
    fi
}

# Main installation function
main() {
    print_banner
    
    echo -e "${YELLOW}This script will install BigHealth and all its dependencies.${NC}"
    echo -e "${YELLOW}Supported systems:${NC}"
    echo -e "  • Ubuntu/Debian and derivatives"
    echo -e "  • Fedora/RHEL/CentOS and derivatives"
    echo -e "  • openSUSE"
    echo -e "  • Arch Linux"
    echo -e "  • macOS (with Homebrew)\n"
    
    echo -e "${YELLOW}The installation will:${NC}"
    echo -e "  • Detect your operating system"
    echo -e "  • Update your system packages"
    echo -e "  • Install Python 3 and required tools"
    echo -e "  • Download BigHealth from GitHub"
    echo -e "  • Set up an isolated Python virtual environment"
    echo -e "  • Install required Python packages"
    echo -e "  • Help you configure F5 iHealth API credentials"
    echo -e "  • Create helper scripts for easy usage\n"
    
    echo -n "Continue with installation? (Y/n): "
    read -r response
    if [[ "$response" =~ ^[Nn]$ ]]; then
        print_info "Installation cancelled"
        exit 0
    fi
    
    # Run installation steps
    check_root
    detect_os
    update_system
    install_python
    clone_repository
    setup_virtualenv
    
    # Try to set up credentials (continue if failed)
    if ! setup_credentials; then
        print_warning "Credential setup skipped - you can configure them later"
    fi
    
    create_helper_scripts
    test_installation
    create_desktop_shortcut
    print_usage
    
    echo -e "\n${GREEN}🎉 Installation completed successfully!${NC}"
    echo -e "${GREEN}Happy F5 troubleshooting! 🚀${NC}\n"
}

# Handle script interruption
trap 'echo -e "\n${RED}Installation interrupted!${NC}"; exit 1' INT TERM

# Run main function
main "$@"


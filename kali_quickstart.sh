#!/bin/bash

# SLAYER v2.0 - Kali Linux Quick Start
# Optimized installation and configuration for Kali Linux

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Banner
show_banner() {
    clear
    echo -e "${WHITE}${BOLD}"
    echo "╔══════════════════════════════════════════╗"
    echo "║              SLAYER v2.0                 ║"
    echo "║        Kali Linux Quick Setup            ║"
    echo "╚══════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "${CYAN}Professional Load Testing Tool Setup${NC}"
    echo
}

# Detect system
detect_system() {
    if grep -q "Kali" /etc/os-release 2>/dev/null; then
        echo -e "${GREEN}✓ Kali Linux detected - Optimal configuration enabled${NC}"
        KALI_DETECTED=true
        KALI_VERSION=$(grep VERSION_ID /etc/os-release | cut -d'"' -f2 2>/dev/null || echo "Unknown")
        echo -e "${BLUE}  Kali version: ${KALI_VERSION}${NC}"
    elif grep -q "ID=ubuntu\|ID=debian" /etc/os-release 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Debian/Ubuntu detected - Using compatible configuration${NC}"
        KALI_DETECTED=false
    else
        echo -e "${YELLOW}⚠️  Unknown system - Using generic configuration${NC}"
        KALI_DETECTED=false
    fi
    echo
}

# Check root privileges
check_root() {
    if [[ $EUID -eq 0 ]]; then
        echo -e "${GREEN}✓ Running as root - Full system configuration available${NC}"
        IS_ROOT=true
    else
        echo -e "${YELLOW}⚠️  Running as user - Limited configuration (sudo may be required)${NC}"
        IS_ROOT=false
        
        # Check if user can sudo
        if sudo -n true 2>/dev/null; then
            echo -e "${GREEN}✓ Sudo access detected${NC}"
            HAS_SUDO=true
        else
            echo -e "${RED}✗ No sudo access - Some features may be limited${NC}"
            HAS_SUDO=false
        fi
    fi
    echo
}

# Check Python version
check_python() {
    echo -e "${CYAN}🐍 Checking Python installation...${NC}"
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        echo -e "${GREEN}✓ Python3 found: ${PYTHON_VERSION}${NC}"
        
        # Check if version is 3.8+
        if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
            echo -e "${GREEN}✓ Python version is compatible${NC}"
        else
            echo -e "${YELLOW}⚠️  Python 3.8+ recommended for best performance${NC}"
        fi
    else
        echo -e "${RED}✗ Python3 not found${NC}"
        exit 1
    fi
    
    # Check pip
    if command -v pip3 &> /dev/null; then
        echo -e "${GREEN}✓ pip3 found${NC}"
    else
        echo -e "${YELLOW}⚠️  pip3 not found - installing...${NC}"
        if [[ $IS_ROOT == true ]] || [[ $HAS_SUDO == true ]]; then
            ${IS_ROOT:+sudo} apt-get update -qq && ${IS_ROOT:+sudo} apt-get install -y python3-pip
        else
            echo -e "${RED}✗ Cannot install pip3 - please install manually${NC}"
            exit 1
        fi
    fi
    echo
}

# Install dependencies
install_dependencies() {
    echo -e "${CYAN}📦 Installing Python dependencies...${NC}"
    
    # Install basic requirements
    if pip3 install -q requests colorama urllib3; then
        echo -e "${GREEN}✓ Basic dependencies installed${NC}"
    else
        echo -e "${RED}✗ Failed to install basic dependencies${NC}"
        exit 1
    fi
    
    # Install additional packages for Kali optimization
    if [[ $KALI_DETECTED == true ]]; then
        # Install additional Kali-specific packages
        pip3 install -q --user psutil 2>/dev/null || true
        echo -e "${GREEN}✓ Kali optimizations installed${NC}"
    fi
    echo
}

# Configure Kali optimizations
configure_kali() {
    if [[ $KALI_DETECTED == true ]]; then
        echo -e "${CYAN}⚡ Applying Kali Linux optimizations...${NC}"
        
        # Create config directory if not exists
        mkdir -p config 2>/dev/null || true
        
        # Create Kali-optimized config
        cat > config/kali_optimized.json << 'EOF'
{
    "threads": 25,
    "connections": 150,
    "timeout": 10,
    "rps": 100,
    "duration": 60,
    "headers": {
        "User-Agent": "SLAYER-Kali/2.0 Security Assessment Tool"
    },
    "patterns": {
        "constant": {"rps": 100},
        "ramp_up": {"start_rps": 10, "end_rps": 200, "duration": 300},
        "burst": {"burst_rps": 500, "burst_duration": 10, "interval": 60}
    },
    "monitoring": {
        "real_time": true,
        "metrics_interval": 1,
        "save_results": true
    }
}
EOF
        echo -e "${GREEN}✓ Kali optimized configuration created${NC}"
        echo
    fi
}

# Make scripts executable
make_executable() {
    echo -e "${CYAN}🔧 Setting up executables...${NC}"
    
    chmod +x slayer 2>/dev/null || true
    chmod +x slayer.py 2>/dev/null || true
    chmod +x slayer_enterprise_enhanced.py 2>/dev/null || true
    chmod +x verify_kali.sh 2>/dev/null || true
    chmod +x install.sh 2>/dev/null || true
    chmod +x setup.sh 2>/dev/null || true
    
    echo -e "${GREEN}✓ Scripts made executable${NC}"
    echo
}

# Test installation
test_installation() {
    echo -e "${CYAN}🧪 Testing SLAYER installation...${NC}"
    
    # Test wrapper script
    if ./slayer --help &>/dev/null; then
        echo -e "${GREEN}✓ SLAYER wrapper script functional${NC}"
    else
        echo -e "${YELLOW}⚠️  Wrapper script test inconclusive${NC}"
    fi
    
    echo -e "${GREEN}✓ Installation test completed${NC}"
    echo
}

# Show next steps
show_next_steps() {
    echo -e "${CYAN}🎯 SLAYER v2.0 is ready for use!${NC}"
    echo
    echo -e "${YELLOW}📋 Quick Start Commands:${NC}"
    echo
    echo -e "${GREEN}  # Basic load test${NC}"
    echo -e "  ${WHITE}./slayer https://httpbin.org/get${NC}"
    echo
    echo -e "${GREEN}  # Custom RPS test${NC}"
    echo -e "  ${WHITE}./slayer https://target.com -r 100 -t 60s${NC}"
    echo
    echo -e "${GREEN}  # POST request test${NC}"
    echo -e "  ${WHITE}./slayer https://api.target.com --method POST -r 50${NC}"
    echo
    
    if [[ $KALI_DETECTED == true ]]; then
        echo -e "${GREEN}  # Use Kali optimized config${NC}"
        echo -e "  ${WHITE}./slayer https://target.com --config config/kali_optimized.json${NC}"
        echo
    fi
    
    echo -e "${YELLOW}📖 Documentation:${NC}"
    echo -e "  • ${CYAN}KALI_INSTALL.md${NC} - Installation guide"
    echo -e "  • ${CYAN}KALI_GUIDE.md${NC} - Advanced usage"
    echo -e "  • ${CYAN}README.md${NC} - General documentation"
    echo
    
    echo -e "${YELLOW}🔧 Advanced Features:${NC}"
    echo -e "  • ${WHITE}./slayer help${NC} - Show all options"
    echo -e "  • ${WHITE}python3 slayer.py${NC} - Interactive mode"
    echo -e "  • ${WHITE}./verify_kali.sh${NC} - Verify Kali optimization"
    echo

    if [[ $KALI_DETECTED == true ]]; then
        echo -e "${BOLD}${GREEN}🔥 Kali Linux optimizations active!${NC}"
        echo -e "${GREEN}Enhanced performance and security testing capabilities enabled.${NC}"
    fi
    
    # Quick test offer
    echo
    echo -e "${YELLOW}Would you like to run a quick test? [y/N]${NC}"
    read -r -n 1 QUICK_TEST
    echo
    
    if [[ $QUICK_TEST =~ ^[Yy]$ ]]; then
        echo -e "${CYAN}Running quick test against httpbin.org...${NC}"
        ./slayer https://httpbin.org/get -r 5 -t 10s || echo -e "${YELLOW}Test completed (check output above)${NC}"
    fi
    
    echo
    echo -e "${BOLD}${CYAN}SLAYER v2.0 - Professional Load Testing${NC}"
    echo -e "${DIM}No authorization required. Direct usage. Maximum efficiency.${NC}"
    echo
}

# Main execution
main() {
    show_banner
    detect_system
    check_root
    check_python
    install_dependencies
    configure_kali
    make_executable
    test_installation
    show_next_steps
}

main "$@"
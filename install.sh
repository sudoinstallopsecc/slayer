#!/bin/bash

# SLAYER - Script de Instalacion Optimizado para Kali Linux
# Instalacion completa con todas las dependencias y configuracion especifica

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${PURPLE}=========================================="
echo -e "  🚀 SLAYER - Instalacion para Kali Linux"
echo -e "==========================================${NC}"
echo ""

# Detectar sistema operativo y distribucion
OS="$(uname -s)"
DISTRO="unknown"

case "${OS}" in
    Linux*)
        MACHINE=Linux
        # Detectar distribucion especifica
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            DISTRO="$ID"
        elif [ -f /etc/debian_version ]; then
            DISTRO="debian"
        elif [ -f /etc/redhat-release ]; then
            DISTRO="rhel"
        fi
        ;;
    Darwin*)
        MACHINE=Mac
        DISTRO="macos"
        ;;
    *)
        MACHINE="UNKNOWN:${OS}"
        ;;
esac

echo -e "${CYAN}[+] Sistema detectado: ${MACHINE} (${DISTRO})${NC}"

# Verificar si es Kali Linux
KALI_DETECTED=false
if [ -f "/etc/os-release" ]; then
    if grep -q "kali" /etc/os-release; then
        KALI_DETECTED=true
        echo -e "${GREEN}[+] ¡Kali Linux detectado! Aplicando configuracion optimizada${NC}"
    fi
fi

echo ""

# Verificar Python
echo "[+] Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "[!] Python 3 no encontrado. Por favor instala Python 3.8 o superior."
    echo ""
    echo "En Kali Linux/Debian/Ubuntu:"
    echo "  sudo apt update && sudo apt install python3 python3-pip"
    echo ""
    echo "En Fedora/RHEL:"
    echo "  sudo dnf install python3 python3-pip"
    echo ""
    echo "En macOS:"
    echo "  brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "[+] Python ${PYTHON_VERSION} encontrado"

# Verificar version minima de Python (3.8)
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')

if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MAJOR" -eq 3 -a "$PYTHON_MINOR" -lt 8 ]; then
    echo "[!] Se requiere Python 3.8 o superior (detectado: ${PYTHON_VERSION})"
    exit 1
fi

# Instalar dependencias del sistema específicas para Kali Linux
if [ "$KALI_DETECTED" = true ]; then
    echo -e "${YELLOW}[+] Instalando dependencias del sistema para Kali Linux...${NC}"
    
    # Actualizar repositorios
    sudo apt update -qq
    
    # Dependencias esenciales del sistema para Kali
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-dev \
        python3-venv \
        build-essential \
        libffi-dev \
        libssl-dev \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
        libjpeg-dev \
        libfreetype6-dev \
        liblcms2-dev \
        libwebp-dev \
        tcl8.6-dev \
        tk8.6-dev \
        python3-tk \
        curl \
        wget \
        git \
        redis-server \
        dnsutils \
        net-tools \
        nmap \
        ca-certificates \
        gnupg \
        lsb-release
    
    echo -e "${GREEN}[+] Dependencias del sistema instaladas correctamente${NC}"
    
    # Configurar Redis (opcional para cache distribuido)
    if systemctl is-enabled redis-server >/dev/null 2>&1; then
        echo -e "${CYAN}[+] Redis ya está configurado${NC}"
    else
        echo -e "${YELLOW}[+] Configurando Redis para cache distribuido...${NC}"
        sudo systemctl enable redis-server
        sudo systemctl start redis-server
    fi
fi

# Verificar pip
echo -e "${CYAN}[+] Verificando pip...${NC}"
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}[!] pip3 no encontrado. Instalando...${NC}"
    python3 -m ensurepip --default-pip || {
        echo -e "${RED}[!] No se pudo instalar pip. Instalando desde repositorios...${NC}"
        if [ "$KALI_DETECTED" = true ]; then
            sudo apt install -y python3-pip
        else
            echo -e "${RED}[!] Por favor instala pip3 manualmente.${NC}"
            exit 1
        fi
    }
fi

echo -e "${GREEN}[+] pip encontrado${NC}"
echo ""

# Configurar entorno virtual automáticamente en Kali
CREATE_VENV="s"
if [ "$KALI_DETECTED" = true ]; then
    echo -e "${CYAN}[+] Creando entorno virtual automáticamente (recomendado para Kali)...${NC}"
else
    echo -e "${YELLOW}[?] ¿Deseas crear un entorno virtual? (recomendado) [s/N]${NC}"
    read -r CREATE_VENV
fi

if [[ "$CREATE_VENV" =~ ^[Ss]$ ]]; then
    echo -e "${CYAN}[+] Creando entorno virtual...${NC}"
    python3 -m venv venv
    
    echo -e "${CYAN}[+] Activando entorno virtual...${NC}"
    source venv/bin/activate
    
    echo -e "${GREEN}[+] Entorno virtual activado${NC}"
    echo ""
fi

# Actualizar pip
echo -e "${CYAN}[+] Actualizando pip...${NC}"
python3 -m pip install --upgrade pip setuptools wheel

# Instalar dependencias básicas
echo ""
echo -e "${CYAN}[+] Instalando dependencias básicas (slayer.py)...${NC}"
pip3 install requests urllib3 certifi

echo -e "${GREEN}[+] Dependencias básicas instaladas correctamente${NC}"
echo ""

# Configuración automática para Kali Linux
INSTALL_ENTERPRISE="s"
if [ "$KALI_DETECTED" = true ]; then
    echo -e "${CYAN}[+] Instalando automáticamente la versión Enterprise completa para Kali Linux...${NC}"
else
    echo -e "${YELLOW}[?] ¿Deseas instalar la versión Enterprise completa? [s/N]${NC}"
    echo -e "    ${BLUE}(Incluye: async, cache Redis, métricas, dashboard, distribución, etc.)${NC}"
    read -r INSTALL_ENTERPRISE
fi

if [[ "$INSTALL_ENTERPRISE" =~ ^[Ss]$ ]]; then
    echo ""
    echo -e "${CYAN}[+] Instalando dependencias Enterprise...${NC}"
    
    # Instalar con retry en caso de fallos de red
    for i in {1..3}; do
        if pip3 install -r requirements.txt; then
            break
        else
            echo -e "${YELLOW}[!] Intento $i fallido, reintentando...${NC}"
            sleep 2
        fi
    done
    
    echo -e "${GREEN}[+] Dependencias Enterprise instaladas correctamente${NC}"
    
    # Configuraciones específicas para Kali Linux
    if [ "$KALI_DETECTED" = true ]; then
        echo -e "${CYAN}[+] Aplicando configuraciones específicas para Kali Linux...${NC}"
        
        # Crear directorio de configuración
        mkdir -p ~/.slayer
        
        # Configuración específica de Kali
        cat > ~/.slayer/kali_config.json << 'EOF'
{
    "kali_optimized": true,
    "default_user_agent": "SLAYER-Kali-LoadTester/4.0",
    "enable_stealth_mode": true,
    "default_rate_limit": 50,
    "enable_distributed_mode": true,
    "redis_host": "127.0.0.1",
    "redis_port": 6379,
    "dashboard_host": "0.0.0.0",
    "dashboard_port": 8080,
    "pentesting_mode": {
        "respect_robots_txt": true,
        "default_timeout": 10,
        "max_redirects": 5,
        "verify_ssl": true
    }
}
EOF
        
        echo -e "${GREEN}[+] Configuración de Kali creada en ~/.slayer/kali_config.json${NC}"
    fi
fi

# Configurar permisos y ejecutables
echo -e "${CYAN}[+] Configurando permisos y archivos ejecutables...${NC}"
chmod +x slayer.py 2>/dev/null || true
chmod +x slayer_enterprise_enhanced.py 2>/dev/null || true

# Crear enlaces simbólicos para facilidad de uso en Kali
if [ "$KALI_DETECTED" = true ] && [[ "$INSTALL_ENTERPRISE" =~ ^[Ss]$ ]]; then
    echo -e "${CYAN}[+] Creando enlaces simbólicos para Kali Linux...${NC}"
    
    # Crear directorio en PATH si no existe
    sudo mkdir -p /usr/local/bin
    
    # Crear script wrapper para slayer
    sudo tee /usr/local/bin/slayer > /dev/null << 'EOF'
#!/bin/bash
# SLAYER wrapper para Kali Linux
SLAYER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )/../../..$(pwd)" && pwd)"
if [ -f "$SLAYER_DIR/venv/bin/activate" ]; then
    source "$SLAYER_DIR/venv/bin/activate"
fi
python3 "$SLAYER_DIR/slayer_enterprise_enhanced.py" "$@"
EOF
    
    sudo chmod +x /usr/local/bin/slayer
    echo -e "${GREEN}[+] Comando 'slayer' disponible globalmente${NC}"
fi

# Verificar instalación
echo -e "${CYAN}[+] Verificando instalación...${NC}"
if python3 -c "import requests, aiohttp" 2>/dev/null; then
    echo -e "${GREEN}[+] Verificación exitosa: Todas las dependencias instaladas correctamente${NC}"
else
    echo -e "${YELLOW}[!] Algunas dependencias pueden faltar, pero la instalación básica está completa${NC}"
fi

echo ""
echo -e "${PURPLE}=========================================="
echo -e "  ✅ Instalación Completada Exitosamente"
echo -e "==========================================${NC}"
echo ""
echo -e "${YELLOW}📋 COMANDOS DISPONIBLES:${NC}"
echo ""
echo -e "${CYAN}Versión básica (simple):${NC}"
echo -e "  ${GREEN}python3 slayer.py${NC}"
echo ""

if [[ "$INSTALL_ENTERPRISE" =~ ^[Ss]$ ]]; then
    echo -e "${CYAN}Versión Enterprise (recomendada):${NC}"
    echo -e "  ${GREEN}python3 slayer_enterprise_enhanced.py load-test --url https://httpbin.org/get${NC}"
    echo ""
    echo -e "${CYAN}Autorizar un objetivo:${NC}"
    echo -e "  ${GREEN}python3 slayer_enterprise_enhanced.py authorize --url https://ejemplo.com${NC}"
    echo ""
    echo -e "${CYAN}Generar configuración personalizada:${NC}"
    echo -e "  ${GREEN}python3 slayer_enterprise_enhanced.py generate-config${NC}"
    echo ""
    
    if [ "$KALI_DETECTED" = true ]; then
        echo -e "${CYAN}Comando global en Kali (después de reiniciar terminal):${NC}"
        echo -e "  ${GREEN}slayer load-test --url https://ejemplo.com --rps 100${NC}"
        echo ""
    fi
    
    echo -e "${CYAN}Dashboard web en tiempo real:${NC}"
    echo -e "  ${GREEN}Automáticamente disponible en http://localhost:8080${NC}"
    echo ""
fi

echo -e "${CYAN}📖 Documentación:${NC}"
echo -e "  ${GREEN}cat README.md${NC} - Guía completa"
echo -e "  ${GREEN}cat QUICKSTART.md${NC} - Inicio rápido"
echo ""
echo -e "${CYAN}🧪 Ejecutar tests:${NC}"
echo -e "  ${GREEN}python3 -m pytest tests/ -v${NC}"
echo ""

if [[ "$CREATE_VENV" =~ ^[Ss]$ ]]; then
    echo -e "${YELLOW}📝 NOTA IMPORTANTE:${NC}"
    echo -e "  Has creado un entorno virtual en: ${CYAN}$(pwd)/venv${NC}"
    echo -e "  Para activarlo en el futuro, ejecuta:"
    echo -e "    ${GREEN}source $(pwd)/venv/bin/activate${NC}"
    echo ""
fi

if [ "$KALI_DETECTED" = true ]; then
    echo -e "${PURPLE}🐉 CONFIGURACIÓN ESPECÍFICA DE KALI:${NC}"
    echo -e "  • Configuración optimizada guardada en: ${CYAN}~/.slayer/kali_config.json${NC}"
    echo -e "  • Redis configurado para cache distribuido"
    echo -e "  • Modo pentesting habilitado con límites éticos"
    echo -e "  • Dashboard accesible desde toda la red local"
    echo ""
    echo -e "${YELLOW}⚠️  RECORDATORIOS IMPORTANTES PARA KALI:${NC}"
    echo -e "  • Solo usa esta herramienta contra objetivos que posees o tienes autorización"
    echo -e "  • Siempre verifica la autorización antes de ejecutar pruebas"
    echo -e "  • Mantén límites de velocidad apropiados"
    echo -e "  • Documenta todos los tests para auditorías"
    echo ""
fi

echo -e "${GREEN}🚀 ¡Disfruta de SLAYER en Kali Linux!${NC}"
echo ""

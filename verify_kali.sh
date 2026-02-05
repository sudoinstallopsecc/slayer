#!/bin/bash
# SLAYER - Script de verificación y diagnóstico para Kali Linux

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

clear

echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗"
echo -e "║                                                                              ║"
echo -e "║  🔍 SLAYER Enterprise - Verificación del Sistema para Kali Linux           ║"
echo -e "║                                                                              ║"
echo -e "╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Variables de estado
ERRORS=0
WARNINGS=0

# Función para mostrar resultado
show_result() {
    local test_name="$1"
    local result="$2"
    local details="$3"
    
    if [ "$result" = "OK" ]; then
        echo -e "${GREEN}[✓] $test_name${NC}"
        if [ ! -z "$details" ]; then
            echo -e "    ${CYAN}$details${NC}"
        fi
    elif [ "$result" = "WARNING" ]; then
        echo -e "${YELLOW}[⚠] $test_name${NC}"
        if [ ! -z "$details" ]; then
            echo -e "    ${YELLOW}$details${NC}"
        fi
        ((WARNINGS++))
    else
        echo -e "${RED}[✗] $test_name${NC}"
        if [ ! -z "$details" ]; then
            echo -e "    ${RED}$details${NC}"
        fi
        ((ERRORS++))
    fi
    echo ""
}

# Detectar Kali Linux
echo -e "${CYAN}🐉 Verificando entorno Kali Linux...${NC}"
echo ""

if [ -f "/etc/os-release" ] && grep -q "kali" /etc/os-release; then
    KALI_VERSION=$(grep VERSION_ID /etc/os-release | cut -d'"' -f2)
    show_result "Kali Linux detectado" "OK" "Versión: $KALI_VERSION"
else
    show_result "Kali Linux no detectado" "WARNING" "El script está optimizado para Kali Linux"
fi

# Verificar Python
echo -e "${CYAN}🐍 Verificando Python...${NC}"
echo ""

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        show_result "Python $PYTHON_VERSION" "OK" "Versión compatible encontrada"
    else
        show_result "Python $PYTHON_VERSION" "ERROR" "Se requiere Python 3.8 o superior"
    fi
else
    show_result "Python 3 no encontrado" "ERROR" "Instalar con: sudo apt install python3"
fi

if command -v pip3 &> /dev/null; then
    PIP_VERSION=$(pip3 --version | awk '{print $2}')
    show_result "pip3 $PIP_VERSION" "OK" "Gestor de paquetes Python disponible"
else
    show_result "pip3 no encontrado" "ERROR" "Instalar con: sudo apt install python3-pip"
fi

# Verificar entorno virtual
echo -e "${CYAN}📦 Verificando entorno virtual...${NC}"
echo ""

if [ -f "venv/bin/activate" ]; then
    show_result "Entorno virtual encontrado" "OK" "Directorio: $(pwd)/venv"
    
    # Probar activación
    if source venv/bin/activate 2>/dev/null; then
        VENV_PYTHON=$(which python)
        show_result "Activación del entorno virtual" "OK" "Python activo: $VENV_PYTHON"
    else
        show_result "Error al activar entorno virtual" "ERROR" "Recrear con: python3 -m venv venv"
    fi
else
    show_result "Entorno virtual no encontrado" "WARNING" "Crear con: python3 -m venv venv"
fi

# Verificar dependencias principales
echo -e "${CYAN}📚 Verificando dependencias Python...${NC}"
echo ""

# Activar entorno virtual si está disponible
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate 2>/dev/null
fi

# Dependencias básicas
BASIC_DEPS=("requests" "urllib3" "certifi")
for dep in "${BASIC_DEPS[@]}"; do
    if python3 -c "import $dep" 2>/dev/null; then
        VERSION=$(python3 -c "import $dep; print($dep.__version__)" 2>/dev/null || echo "desconocida")
        show_result "$dep instalado" "OK" "Versión: $VERSION"
    else
        show_result "$dep no encontrado" "ERROR" "Instalar con: pip3 install $dep"
    fi
done

# Dependencias enterprise
ENTERPRISE_DEPS=("aiohttp" "websockets" "redis" "click" "rich")
echo -e "${CYAN}🚀 Verificando dependencias Enterprise...${NC}"
echo ""

for dep in "${ENTERPRISE_DEPS[@]}"; do
    if python3 -c "import $dep" 2>/dev/null; then
        VERSION=$(python3 -c "import $dep; print($dep.__version__)" 2>/dev/null || echo "desconocida")
        show_result "$dep instalado" "OK" "Versión: $VERSION"
    else
        show_result "$dep no encontrado" "WARNING" "Instalar con: pip3 install -r requirements.txt"
    fi
done

# Verificar servicios del sistema específicos de Kali
echo -e "${CYAN}⚙️ Verificando servicios del sistema...${NC}"
echo ""

# Redis (para cache distribuido)
if command -v redis-cli &> /dev/null; then
    if systemctl is-active redis-server >/dev/null 2>&1; then
        REDIS_VERSION=$(redis-cli --version | awk '{print $2}')
        show_result "Redis activo" "OK" "Versión: $REDIS_VERSION"
    else
        show_result "Redis instalado pero inactivo" "WARNING" "Iniciar con: sudo systemctl start redis-server"
    fi
else
    show_result "Redis no instalado" "WARNING" "Instalar con: sudo apt install redis-server"
fi

# Herramientas de red
if command -v nmap &> /dev/null; then
    NMAP_VERSION=$(nmap --version | head -n1 | awk '{print $3}')
    show_result "Nmap disponible" "OK" "Versión: $NMAP_VERSION - Integración de reconocimiento"
else
    show_result "Nmap no encontrado" "WARNING" "Instalar con: sudo apt install nmap"
fi

if command -v dig &> /dev/null; then
    show_result "DNS utilities (dig) disponible" "OK" "Para verificación de autorización DNS"
else
    show_result "DNS utilities no encontradas" "WARNING" "Instalar con: sudo apt install dnsutils"
fi

# Verificar archivos de SLAYER
echo -e "${CYAN}📁 Verificando archivos de SLAYER...${NC}"
echo ""

REQUIRED_FILES=(
    "slayer.py"
    "slayer_enterprise_enhanced.py"
    "requirements.txt"
    "install.sh"
    "setup.sh"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        show_result "$file encontrado" "OK"
    else
        show_result "$file no encontrado" "ERROR" "Archivo requerido faltante"
    fi
done

# Verificar archivos específicos de Kali
KALI_FILES=(
    "slayer"
    "kali_quickstart.sh"
    "config/kali_optimized.json"
    "KALI_GUIDE.md"
)

for file in "${KALI_FILES[@]}"; do
    if [ -f "$file" ]; then
        show_result "$file (Kali)" "OK" "Archivo específico de Kali encontrado"
    else
        show_result "$file (Kali)" "WARNING" "Archivo específico de Kali faltante"
    fi
done

# Verificar permisos
echo -e "${CYAN}🔐 Verificando permisos...${NC}"
echo ""

EXECUTABLE_FILES=("slayer.py" "slayer_enterprise_enhanced.py" "install.sh" "setup.sh" "slayer" "kali_quickstart.sh")

for file in "${EXECUTABLE_FILES[@]}"; do
    if [ -f "$file" ] && [ -x "$file" ]; then
        show_result "$file ejecutable" "OK"
    elif [ -f "$file" ]; then
        show_result "$file sin permisos de ejecución" "WARNING" "Corregir con: chmod +x $file"
    fi
done

# Verificar directorios
echo -e "${CYAN}📂 Verificando estructura de directorios...${NC}"
echo ""

REQUIRED_DIRS=("logs" "reports" "config" "slayer_enterprise" "tests")

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        show_result "Directorio $dir" "OK"
    else
        show_result "Directorio $dir faltante" "WARNING" "Crear con: mkdir -p $dir"
    fi
done

# Verificar configuración de usuario
echo -e "${CYAN}👤 Verificando configuración de usuario...${NC}"
echo ""

if [ -d "$HOME/.slayer" ]; then
    show_result "Directorio de configuración de usuario" "OK" "Ubicación: $HOME/.slayer"
else
    show_result "Directorio de configuración de usuario" "WARNING" "Crear con: mkdir -p ~/.slayer"
fi

if [ -w "/var/log" ]; then
    show_result "Permisos de escritura en /var/log" "OK" "Para logs del sistema"
else
    show_result "Sin permisos en /var/log" "WARNING" "Configurar con: sudo mkdir -p /var/log/slayer && sudo chown $USER:$USER /var/log/slayer"
fi

# Prueba funcional básica
echo -e "${CYAN}🧪 Realizando prueba funcional básica...${NC}"
echo ""

# Probar importación de módulos principales
if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from slayer_enterprise.testing.authorization import TargetAuthorization
    from slayer_enterprise.testing.patterns import TrafficPatternEngine
    from slayer_enterprise.testing.metrics import LoadTestMetrics
    print('Módulos importados correctamente')
except ImportError as e:
    print(f'Error de importación: {e}')
    sys.exit(1)
" 2>/dev/null; then
    show_result "Importación de módulos Enterprise" "OK" "Todos los módulos cargados correctamente"
else
    show_result "Error en importación de módulos" "ERROR" "Ejecutar: pip3 install -r requirements.txt"
fi

# Prueba de conectividad básica (si hay internet)
if python3 -c "
import requests
try:
    response = requests.get('https://httpbin.org/get', timeout=5)
    if response.status_code == 200:
        print('Conexión OK')
    else:
        print('Error de HTTP')
        exit(1)
except:
    print('Sin conexión')
    exit(1)
" 2>/dev/null; then
    show_result "Conectividad de red" "OK" "httpbin.org accesible para pruebas"
else
    show_result "Conectividad de red" "WARNING" "Sin acceso a internet o bloqueado"
fi

# Mostrar resumen final
echo ""
echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗"
echo -e "║                              RESUMEN FINAL                                  ║"
echo -e "╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}🎉 ¡PERFECTO! SLAYER Enterprise está completamente configurado para Kali Linux${NC}"
    echo ""
    echo -e "${CYAN}✅ Próximos pasos recomendados:${NC}"
    echo -e "   ${GREEN}1. ./slayer help${NC} - Ver comandos específicos de Kali"
    echo -e "   ${GREEN}2. ./slayer authorize https://httpbin.org${NC} - Probar autorización"
    echo -e "   ${GREEN}3. ./slayer quick-test https://httpbin.org/get${NC} - Prueba rápida"
    echo ""
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  SLAYER está funcional con $WARNINGS advertencia(s) menores${NC}"
    echo ""
    echo -e "${CYAN}✅ Puedes usar SLAYER, pero considera resolver las advertencias para funcionalidad completa${NC}"
    echo ""
else
    echo -e "${RED}❌ SLAYER tiene $ERRORS error(es) que deben corregirse antes del uso${NC}"
    echo ""
    echo -e "${CYAN}🔧 Acciones recomendadas:${NC}"
    if [ $ERRORS -gt 0 ]; then
        echo -e "   ${RED}1. Ejecutar: ./install.sh${NC} - Reinstalar dependencias"
        echo -e "   ${RED}2. Ejecutar: pip3 install -r requirements.txt${NC} - Instalar paquetes Python"
    fi
    if [ $WARNINGS -gt 0 ]; then
        echo -e "   ${YELLOW}3. Revisar advertencias arriba y aplicar correcciones sugeridas${NC}"
    fi
fi

echo ""
echo -e "${CYAN}📚 Documentación específica de Kali: ${GREEN}cat KALI_GUIDE.md${NC}"
echo -e "${CYAN}🚀 Inicio rápido interactivo: ${GREEN}./kali_quickstart.sh${NC}"
echo ""

exit $ERRORS
#!/bin/bash
# Setup script optimizado para SLAYER Enterprise en Kali Linux

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${PURPLE}🚀 SLAYER Enterprise Setup para Kali Linux"
echo -e "============================================${NC}"
echo ""

# Detectar si es Kali Linux
KALI_DETECTED=false
if [ -f "/etc/os-release" ] && grep -q "kali" /etc/os-release; then
    KALI_DETECTED=true
    echo -e "${GREEN}[+] ¡Kali Linux detectado! Aplicando configuración optimizada${NC}"
fi

# Check Python version
echo -e "${CYAN}Verificando versión de Python...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python $python_version encontrado${NC}"

# Verificar version mínima (3.8+)
python_major=$(python3 -c 'import sys; print(sys.version_info[0])')
python_minor=$(python3 -c 'import sys; print(sys.version_info[1])')

if [ "$python_major" -lt 3 ] || [ "$python_major" -eq 3 -a "$python_minor" -lt 8 ]; then
    echo -e "${RED}[!] Se requiere Python 3.8 o superior (detectado: $python_version)${NC}"
    exit 1
fi

# Create virtual environment
echo ""
echo -e "${CYAN}Creando entorno virtual...${NC}"
python3 -m venv venv
echo -e "${GREEN}✓ Entorno virtual creado${NC}"

# Activate virtual environment
echo ""
echo -e "${CYAN}Activando entorno virtual...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Entorno virtual activado${NC}"

# Upgrade pip
echo ""
echo -e "${CYAN}Actualizando pip...${NC}"
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo -e "${GREEN}✓ Pip actualizado${NC}"

# Install dependencies
echo ""
echo -e "${CYAN}Instalando dependencias...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencias instaladas${NC}"

# Configuraciones específicas para Kali Linux
if [ "$KALI_DETECTED" = true ]; then
    echo ""
    echo -e "${YELLOW}[+] Aplicando configuración específica para Kali Linux...${NC}"
    
    # Crear directorios de configuración
    mkdir -p ~/.slayer
    mkdir -p ~/.slayer/profiles
    mkdir -p ~/.slayer/cache
    mkdir -p logs
    mkdir -p reports
    
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
        "verify_ssl": true,
        "ethical_limits": true
    },
    "logging": {
        "level": "INFO",
        "file": "logs/slayer_kali.log",
        "max_size_mb": 100,
        "backup_count": 5
    }
}
EOF
    
    echo -e "${GREEN}✓ Configuración de Kali creada${NC}"
fi

# Run tests
echo ""
echo -e "${CYAN}Ejecutando tests...${NC}"
if python -m pytest tests/ -v --tb=short 2>/dev/null; then
    echo -e "${GREEN}✓ Todos los tests pasaron${NC}"
else
    echo -e "${YELLOW}! Algunos tests fallaron, pero el setup básico está completo${NC}"
fi

# Crear script de inicio rápido para Kali
if [ "$KALI_DETECTED" = true ]; then
    echo ""
    echo -e "${CYAN}[+] Creando scripts de inicio rápido...${NC}"
    
    # Script de inicio rápido
    cat > slayer_kali.sh << 'EOF'
#!/bin/bash
# Script de inicio rápido de SLAYER para Kali Linux

# Colores
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Activar entorno virtual si existe
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓ Entorno virtual activado${NC}"
fi

# Verificar servicios necesarios
echo -e "${CYAN}[+] Verificando servicios...${NC}"
if systemctl is-active redis-server >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis está ejecutándose${NC}"
else
    echo -e "${YELLOW}[!] Iniciando Redis...${NC}"
    sudo systemctl start redis-server
fi

# Mostrar opciones
echo ""
echo -e "${CYAN}🚀 SLAYER Enterprise para Kali Linux${NC}"
echo "================================"
echo ""
echo "Comandos disponibles:"
echo "  load-test    - Ejecutar prueba de carga"
echo "  authorize    - Autorizar un objetivo"
echo "  generate-config - Crear configuración personalizada"
echo ""
echo "Ejemplos:"
echo "  python3 slayer_enterprise_enhanced.py load-test --url https://httpbin.org/get --rps 50"
echo "  python3 slayer_enterprise_enhanced.py authorize --url https://ejemplo.com"
echo ""

# Ejecutar comando si se proporciona
if [ $# -gt 0 ]; then
    python3 slayer_enterprise_enhanced.py "$@"
fi
EOF
    
    chmod +x slayer_kali.sh
    echo -e "${GREEN}✓ Script slayer_kali.sh creado${NC}"
fi

# Show stats
echo ""
echo -e "${PURPLE}===================================="
echo -e "✅ Setup Completado Exitosamente!"
echo -e "====================================${NC}"
echo ""
echo -e "${YELLOW}📋 Próximos pasos:${NC}"
echo -e "${CYAN}1. Activar venv:${NC} source venv/bin/activate"
echo -e "${CYAN}2. Probar CLI:${NC} python slayer_enterprise_enhanced.py --help"

if [ "$KALI_DETECTED" = true ]; then
    echo -e "${CYAN}3. Inicio rápido en Kali:${NC} ./slayer_kali.sh load-test --url https://httpbin.org/get"
else
    echo -e "${CYAN}3. Ejecutar ejemplo:${NC} python examples/basic_usage.py"
fi

echo -e "${CYAN}4. Leer docs:${NC} cat QUICKSTART.md"
echo ""

if [ "$KALI_DETECTED" = true ]; then
    echo -e "${GREEN}🎯 SLAYER Enterprise v4.0 optimizado para Kali Linux está listo!${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  Recordatorios importantes:${NC}"
    echo -e "  • Solo usa contra objetivos que posees o tienes autorización"
    echo -e "  • La configuración de Kali está en: ~/.slayer/kali_config.json"
    echo -e "  • Dashboard disponible en: http://localhost:8080"
    echo -e "  • Logs guardados en: logs/slayer_kali.log"
else
    echo -e "${GREEN}🎯 SLAYER Enterprise v4.0 está listo!${NC}"
fi

echo ""

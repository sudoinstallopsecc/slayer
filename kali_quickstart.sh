#!/bin/bash
# SLAYER - Guía de inicio rápido específica para Kali Linux

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
echo -e "║  🐉 SLAYER Enterprise - Guía Rápida para Kali Linux                        ║"
echo -e "║                                                                              ║"
echo -e "╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}📋 COMANDOS BÁSICOS:${NC}"
echo ""

echo -e "${YELLOW}1. Autorizar un objetivo (OBLIGATORIO):${NC}"
echo -e "   ${GREEN}python3 slayer_enterprise_enhanced.py authorize --url https://tuservidor.com${NC}"
echo ""

echo -e "${YELLOW}2. Prueba de carga básica:${NC}"
echo -e "   ${GREEN}python3 slayer_enterprise_enhanced.py load-test \\${NC}"
echo -e "   ${GREEN}     --url https://tuservidor.com/api \\${NC}"
echo -e "   ${GREEN}     --rps 50 \\${NC}"
echo -e "   ${GREEN}     --duration 60${NC}"
echo ""

echo -e "${YELLOW}3. Generar configuración personalizada:${NC}"
echo -e "   ${GREEN}python3 slayer_enterprise_enhanced.py generate-config --output mi_config.json${NC}"
echo ""

echo -e "${YELLOW}4. Usar configuración personalizada:${NC}"
echo -e "   ${GREEN}python3 slayer_enterprise_enhanced.py load-test --config mi_config.json${NC}"
echo ""

echo -e "${CYAN}🎯 PATRONES DE TRÁFICO AVANZADOS:${NC}"
echo ""

echo -e "${YELLOW}Rampa gradual (0 → 100 RPS en 5 minutos):${NC}"
echo -e "   ${GREEN}python3 slayer_enterprise_enhanced.py load-test \\${NC}"
echo -e "   ${GREEN}     --url https://tuservidor.com \\${NC}"
echo -e "   ${GREEN}     --rps 100 \\${NC}"
echo -e "   ${GREEN}     --duration 300 \\${NC}"
echo -e "   ${GREEN}     --pattern ramp_up${NC}"
echo ""

echo -e "${YELLOW}Patrón de ráfagas (spikes periódicos):${NC}"
echo -e "   ${GREEN}python3 slayer_enterprise_enhanced.py load-test \\${NC}"
echo -e "   ${GREEN}     --url https://tuservidor.com \\${NC}"
echo -e "   ${GREEN}     --rps 50 \\${NC}"
echo -e "   ${GREEN}     --duration 300 \\${NC}"
echo -e "   ${GREEN}     --pattern burst${NC}"
echo ""

echo -e "${CYAN}📊 MONITOREO EN TIEMPO REAL:${NC}"
echo ""
echo -e "• Dashboard web automático: ${GREEN}http://localhost:8080${NC}"
echo -e "• Métricas en tiempo real con gráficos interactivos"
echo -e "• Monitoreo de SLOs (Service Level Objectives)"
echo -e "• Alertas automáticas de rendimiento"
echo ""

echo -e "${CYAN}🔒 CONFIGURACIÓN DE SEGURIDAD EN KALI:${NC}"
echo ""
echo -e "• Configuración: ${GREEN}~/.slayer/kali_config.json${NC}"
echo -e "• Logs: ${GREEN}logs/slayer_kali.log${NC}"
echo -e "• Cache: ${GREEN}~/.slayer/cache/${NC}"
echo ""

echo -e "${YELLOW}⚠️  IMPORTANTE - USO ÉTICO:${NC}"
echo -e "• ${RED}Solo usa contra servidores que posees o tienes autorización explícita${NC}"
echo -e "• ${YELLOW}Siempre verifica autorización antes de ejecutar pruebas${NC}"
echo -e "• ${CYAN}Usa límites apropiados de velocidad (RPS)${NC}"
echo -e "• ${BLUE}Documenta todas las pruebas para auditorías${NC}"
echo ""

echo -e "${CYAN}🛠️  COMANDOS DE DIAGNÓSTICO:${NC}"
echo ""
echo -e "${YELLOW}Verificar instalación:${NC}"
echo -e "   ${GREEN}python3 -c \"from slayer_enterprise.testing import *; print('✓ Todos los módulos cargados')\"${NC}"
echo ""

echo -e "${YELLOW}Verificar Redis (para cache distribuido):${NC}"
echo -e "   ${GREEN}redis-cli ping${NC}"
echo ""

echo -e "${YELLOW}Estado de servicios:${NC}"
echo -e "   ${GREEN}systemctl status redis-server${NC}"
echo ""

echo -e "${CYAN}📚 ARCHIVOS DE DOCUMENTACIÓN:${NC}"
echo ""
echo -e "• ${GREEN}README.md${NC} - Documentación completa"
echo -e "• ${GREEN}QUICKSTART.md${NC} - Guía de inicio rápido"
echo -e "• ${GREEN}GUIA_USO.md${NC} - Manual de usuario"
echo -e "• ${GREEN}examples/${NC} - Ejemplos de uso"
echo ""

echo -e "${GREEN}¿Quieres ejecutar una prueba rápida contra httpbin.org? [s/N]${NC}"
read -r QUICK_TEST

if [[ "$QUICK_TEST" =~ ^[Ss]$ ]]; then
    echo ""
    echo -e "${CYAN}[+] Ejecutando prueba rápida...${NC}"
    python3 slayer_enterprise_enhanced.py load-test \
        --url https://httpbin.org/get \
        --rps 10 \
        --duration 30 \
        --auto-confirm \
        --force
fi

echo ""
echo -e "${PURPLE}🚀 ¡Listo para usar SLAYER en Kali Linux!${NC}"
echo ""
# SLAYER Enterprise - Guía Específica para Kali Linux

## 🐉 Optimización Completa para Kali Linux

SLAYER Enterprise ha sido especialmente optimizado para Kali Linux, incluyendo configuraciones específicas, integración con herramientas de pentesting, y scripts de instalación automatizada.

## 📦 Instalación Rápida en Kali

```bash
# 1. Clonar el repositorio
git clone https://github.com/kndys123/slayer.git
cd slayer

# 2. Instalación automática optimizada para Kali
./install.sh

# 3. Configuración específica de Kali (opcional)
./setup.sh
```

## 🚀 Uso Rápido con Script Wrapper

### Comando Simplificado
```bash
# Usar el wrapper específico de Kali
./slayer help                    # Ver ayuda específica de Kali
./slayer authorize <url>         # Autorizar objetivo
./slayer quick-test <url>        # Prueba rápida (10 RPS, 30s)
./slayer load-test <url> --rps 50 --duration 120
./slayer profile moderate <url>  # Usar perfil predefinido
```

### Ejemplos Prácticos
```bash
# Autorizar y probar httpbin.org (seguro para pruebas)
./slayer authorize https://httpbin.org
./slayer quick-test https://httpbin.org/get

# Prueba de carga con patrón de rampa
./slayer load-test https://httpbin.org/get \
  --rps 50 \
  --duration 300 \
  --pattern ramp_up \
  --dashboard

# Usar perfil predefinido
./slayer profile light https://httpbin.org/get
```

## 🔧 Configuración Específica de Kali

### Archivos de Configuración
- **`~/.slayer/kali_config.json`** - Configuración principal
- **`config/kali_optimized.json`** - Configuración optimizada
- **`/var/log/slayer/`** - Directorio de logs
- **`~/slayer_reports/`** - Reportes generados

### Configuración de Red para Kali
```json
{
  "network": {
    "default_user_agent": "SLAYER-Kali-LoadTester/4.0 (Kali Linux)",
    "max_concurrent_connections": 100,
    "default_timeout": 30,
    "enable_stealth_mode": true
  },
  "security": {
    "ethical_mode": true,
    "require_authorization": true,
    "max_rps_without_auth": 10
  }
}
```

## 🛡️ Características de Seguridad para Pentesting

### Modo Ético Activado por Defecto
- ✅ Verificación obligatoria de autorización
- ✅ Límites automáticos de velocidad
- ✅ Respeto automático a robots.txt
- ✅ Logging completo para auditorías
- ✅ Parada automática ante alta tasa de errores

### Integración con Herramientas de Kali
```bash
# Integración con Nmap (detecta servicios web)
nmap -sV -p 80,443 target.com && ./slayer authorize https://target.com

# Exportar resultados para Burp Suite
./slayer load-test https://target.com --rps 10 --duration 60

# Compatible con OWASP ZAP para análisis posterior
```

## 📊 Dashboard y Monitoreo

### Dashboard Web en Tiempo Real
- **URL**: http://localhost:8080
- **Características**:
  - Métricas en tiempo real
  - Gráficos de RPS y response time
  - Alertas de SLO
  - Estado del sistema
  - Exportación de datos

### Métricas Específicas para Pentesting
```bash
# Iniciar solo dashboard para monitoreo
./slayer dashboard

# Ver métricas en terminal
python3 slayer_enterprise_enhanced.py load-test \
  --url https://target.com \
  --rps 25 \
  --duration 120 \
  --no-dashboard  # Solo métricas en terminal
```

## 🎯 Perfiles de Testing Predefinidos

### Perfiles Optimizados para Kali
```bash
# Perfil Ligero - Para reconocimiento inicial
./slayer profile light https://target.com
# 10 RPS, 30 segundos, patrón constante

# Perfil Moderado - Para testing general
./slayer profile moderate https://target.com  
# 100 RPS, 5 minutos, patrón rampa

# Perfil de Estrés - Para límites máximos
./slayer profile stress https://target.com
# 500 RPS, 10 minutos, patrón burst
```

### Configuración Personalizada
```bash
# Generar configuración base
./slayer config

# Editar configuración
nano kali_custom.json

# Usar configuración personalizada
./slayer load-test --config kali_custom.json
```

## 🔍 Características Avanzadas

### Patrones de Tráfico Específicos
```bash
# Patrón de reconocimiento suave
./slayer load-test https://target.com \
  --rps 5 \
  --duration 600 \
  --pattern wave

# Simulación de usuarios reales
./slayer load-test https://target.com \
  --pattern realistic_user \
  --duration 300
```

### Throttling Inteligente
- **Adaptativo**: Ajusta automáticamente la velocidad según respuesta del servidor
- **Circuit Breaker**: Protección automática ante fallos
- **Back-off Strategies**: Múltiples estrategias de retroceso
- **Emergency Stop**: Parada automática ante problemas críticos

### Testing Distribuido
```bash
# Coordinador master (en Kali principal)
python3 slayer_enterprise_enhanced.py distributed-coordinator --port 8765

# Workers adicionales (en otros sistemas)
python3 slayer_enterprise_enhanced.py distributed-worker \
  --coordinator kali-master:8765
```

## 🚨 Uso Ético y Legal

### ⚠️ IMPORTANTE - Leer Antes de Usar
```
Solo utiliza SLAYER contra:
✅ Servidores que posees
✅ Sistemas con autorización explícita por escrito  
✅ Entornos de testing dedicados
✅ Servicios públicos de prueba (httpbin.org, etc.)

❌ NUNCA uses contra:
❌ Servidores de terceros sin autorización
❌ Infraestructura crítica
❌ Servicios de producción sin planificación
❌ Sistemas gubernamentales o militares
```

### Verificación de Autorización
```bash
# Siempre autoriza primero
./slayer authorize https://target.com

# El sistema verificará:
# 1. DNS TXT record con token
# 2. Archivo en /.well-known/slayer-loadtest-authorization.txt
# 3. Header HTTP X-SLAYER-LoadTest-Auth
```

## 🛠️ Troubleshooting en Kali

### Problemas Comunes
```bash
# Si Redis no funciona
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Si faltan dependencias
sudo apt update
sudo apt install python3-dev python3-pip build-essential

# Si hay problemas de permisos
sudo mkdir -p /var/log/slayer
sudo chown $USER:$USER /var/log/slayer

# Verificar instalación
python3 -c "from slayer_enterprise.testing import *; print('✓ OK')"
```

### Logs y Depuración
```bash
# Ver logs en tiempo real
tail -f /var/log/slayer/kali.log

# Logs de auditoría
tail -f /var/log/slayer/audit.log

# Debug mode
./slayer load-test https://target.com --debug
```

## 📚 Recursos Adicionales

### Documentación Específica
- **Inicio Rápido**: `./kali_quickstart.sh`
- **Ejemplos**: `cat examples/kali_examples.py`
- **Configuración**: `cat config/kali_optimized.json`

### Comunidad y Soporte
- **GitHub Issues**: Para reportar bugs específicos de Kali
- **Wiki**: Documentación extendida y casos de uso
- **Examples**: Directorio con ejemplos específicos para pentesting

## 🎓 Casos de Uso en Pentesting

### Reconocimiento de Carga
```bash
# Identificar límites del servidor
./slayer load-test https://target.com \
  --pattern ramp_up \
  --rps 200 \
  --duration 300

# Encontrar puntos de ruptura
./slayer stress-test https://target.com
```

### Testing de APIs
```bash
# Probar endpoints específicos
./slayer load-test https://api.target.com/v1/users \
  --rps 50 \
  --duration 120

# Testing con datos POST
python3 slayer_enterprise_enhanced.py load-test \
  --config post_testing.json
```

### Análisis de Rendimiento
```bash
# Identificar cuellos de botella
./slayer load-test https://target.com \
  --dashboard \
  --pattern wave \
  --duration 600

# Monitorear SLOs específicos
```

---

**🐉 SLAYER Enterprise está optimizado y listo para Kali Linux**

*Recuerda siempre usar esta herramienta de manera ética y responsable.*
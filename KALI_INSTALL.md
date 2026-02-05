# SLAYER v2.0 - Instalación Rápida para Kali Linux

¡SLAYER ha sido completamente rediseñado para profesionales de pentesting!

## 🚀 Instalación Ultra-Rápida

```bash
# Clonar repositorio
git clone https://github.com/kndys123/slayer.git
cd slayer

# Instalación automática para Kali
./kali_quickstart.sh
```

## ⚡ Uso Inmediato

```bash
# Prueba básica
./slayer https://httpbin.org/get

# Test de rendimiento
./slayer https://target.com -r 100 -t 60s

# Test con método POST
./slayer https://api.target.com --method POST -r 50
```

## 🎯 Características Principales

### ✨ **Sin Autorizaciones** 
- Eliminadas todas las barreras de autorización
- Acceso directo y sin fricción
- Perfecto para pruebas rápidas de pentesting

### 🎨 **Interfaz Moderna**
- Banner minimalista "SLAYER"
- Sintaxis directa inspirada en HTTPie y wrk
- Barras de progreso en tiempo real
- Métricas profesionales de rendimiento

### 📊 **Métricas en Tiempo Real**
- RPS (Requests Per Second)
- Latency promedio y percentiles
- Tasa de errores
- Análisis de rendimiento completo

### 🛠️ **Integración con herramientas**
- Compatible con wrk para benchmarking avanzado
- Configuraciones optimizadas para Kali Linux
- Workflows de seguridad integrados

## 🔧 Configuración Optimizada para Kali

### Configuración Automática
```bash
# Verificar compatibilidad con Kali
./verify_kali.sh

# Usar configuración optimizada
./slayer https://target.com --config config/kali_optimized.json
```

### Configuración Manual
```json
{
  "threads": 20,
  "connections": 100,
  "timeout": 10,
  "user_agents": ["Kali/Slayer", "Security/Test"],
  "headers": {
    "X-Test-Tool": "SLAYER",
    "User-Agent": "Security-Assessment"
  }
}
```

## 📈 Casos de Uso en Pentesting

### 1. Test de Disponibilidad
```bash
./slayer https://target.com -r 10 -t 30s
```

### 2. Stress Testing
```bash
./slayer https://api.target.com -r 500 --threads 50
```

### 3. Análisis de Endpoints
```bash
./slayer https://target.com/api/users --method GET -r 100
./slayer https://target.com/api/login --method POST -r 50
```

### 4. Test de Rate Limiting
```bash
./slayer https://api.target.com -r 1000 -t 10s
```

## 🎯 Sintaxis Simplificada

### Comandos Básicos
```bash
# URL directo (50 RPS por 60 segundos)
./slayer https://example.com

# RPS personalizado
./slayer https://example.com -r 200

# Duración personalizada
./slayer https://example.com -t 120s

# Hilos concurrentes
./slayer https://example.com --threads 25
```

### Métodos HTTP
```bash
./slayer https://api.com --method GET
./slayer https://api.com --method POST
./slayer https://api.com --method PUT
./slayer https://api.com --method DELETE
```

### Patrones de Tráfico
```bash
./slayer https://example.com --pattern constant
./slayer https://example.com --pattern ramp_up
./slayer https://example.com --pattern burst
```

## 🔍 Análisis de Resultados

SLAYER v2.0 proporciona análisis detallado:

- **RPS Real**: Requests per second alcanzados
- **Latencia**: Promedio, P50, P95, P99
- **Códigos de Estado**: Distribución 2xx, 4xx, 5xx
- **Errores de Red**: Timeouts, conexiones fallidas
- **Throughput**: Bytes transferidos

## 🛡️ Consideraciones de Seguridad

### Uso Ético
- Solo usar en sistemas autorizados
- Respetar límites de rate limiting
- Monitorear impacto en servicios

### Best Practices
```bash
# Comenzar con cargas bajas
./slayer https://target.com -r 5 -t 10s

# Incrementar gradualmente
./slayer https://target.com -r 25 -t 30s

# Análisis completo
./slayer https://target.com -r 100 -t 60s --dashboard
```

## 📦 Dependencias

SLAYER v2.0 tiene dependencias mínimas:
- Python 3.8+
- pip packages: requests, colorama
- Opcional: wrk para benchmarking avanzado

## 🔄 Actualización

```bash
cd slayer
git pull origin main
./setup.sh
```

## 🆘 Soporte

- **GitHub Issues**: https://github.com/kndys123/slayer/issues
- **Documentación**: Ver KALI_GUIDE.md para uso avanzado
- **Ejemplos**: Ver examples/ para casos específicos

---

**SLAYER v2.0** - Herramienta profesional de load testing optimizada para Kali Linux y workflows de seguridad.

🔥 **Rediseño completo. Sin barreras. Máximo rendimiento.**
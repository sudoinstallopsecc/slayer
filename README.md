# SLAYER - Enterprise Web Request Tool

🚀 Herramienta profesional de solicitudes HTTP de alto rendimiento con capacidades empresariales y optimización específica para **Kali Linux**.

## 🐉 Optimizado para Kali Linux

SLAYER Enterprise ha sido **especialmente optimizado para Kali Linux** con configuraciones específicas, integración ética, y scripts de instalación automatizada.

### ⚡ Instalación Ultra-Rápida para Kali

```bash
git clone https://github.com/kndys123/slayer.git
cd slayer
./install.sh  # Detecta Kali automáticamente y aplica configuración optimizada
```

### 🎯 Uso Simplificado en Kali

```bash
# Wrapper específico para Kali con comandos simplificados
./slayer help                     # Ver comandos específicos de Kali
./slayer authorize https://target.com        # Autorizar objetivo
./slayer quick-test https://target.com       # Prueba rápida (10 RPS, 30s)
./slayer load-test https://target.com --rps 50 --duration 120
./slayer profile moderate https://target.com # Usar perfil predefinido
```

### 🔍 Verificación Completa del Sistema

```bash
./verify_kali.sh                 # Diagnóstico completo del sistema
./kali_quickstart.sh             # Guía interactiva para nuevos usuarios
```

**Características específicas de Kali Linux:**
- 🔒 **Modo Ético Activado**: Configuración por defecto con salvaguardas de seguridad
- 🛡️ **Autorización Obligatoria**: Sistema de verificación de objetivos antes de cualquier prueba
- 📊 **Dashboard Integrado**: Panel de control en tiempo real para monitoreo
- 🔄 **Distribución de Carga**: Coordinación automática entre múltiples instancias
- 📈 **SLO Monitoring**: Alertas automáticas y límites de seguridad

## Instalacion Rapida (Otros Sistemas)

### Linux / macOS / Kali Linux

```bash
git clone https://github.com/kndys123/slayer.git
cd slayer
chmod +x install.sh
./install.sh
```

### Windows

```bash
git clone https://github.com/kndys123/slayer.git
cd slayer
install.bat
```

## Uso Basico

### Version CLI Simple

```bash
python slayer.py
```

Comandos interactivos:
- `set target <url>` - Establecer URL objetivo
- `set method <GET|POST|PUT|DELETE>` - Establecer metodo HTTP
- `set threads <numero>` - Establecer numero de hilos
- `run` - Iniciar prueba
- `help` - Ver ayuda completa

### Version Enterprise (Avanzada)

```bash
# Solicitud simple
python slayer_enterprise_cli.py request -u https://api.example.com/data

# Prueba de carga
python slayer_enterprise_cli.py load-test -u https://api.example.com -n 1000 -c 10

# Ver estadisticas
python slayer_enterprise_cli.py stats

# Ver estado del sistema
python slayer_enterprise_cli.py health
```

## Caracteristicas Principales

### Version Base (slayer.py)
- Solicitudes HTTP multiples metodos (GET, POST, PUT, DELETE, HEAD, OPTIONS, PATCH)
- Soporte multi-hilo
- Estadisticas en tiempo real
- User agents aleatorios
- Control de delay entre solicitudes
- Interfaz interactiva con colores

### Version Enterprise (slayer_enterprise/)
- Rendimiento 20x superior con async/await
- Sistema de cache multi-nivel (memoria + Redis)
- Proteccion contra SSRF y validacion de entrada
- Rate limiting con multiples algoritmos
- Circuit breakers para resiliencia
- Autenticacion JWT y API Keys
- Metricas Prometheus
- Logging estructurado y tracing distribuido
- Sistema de plugins y middleware
- Connection pooling (100+ conexiones simultaneas)
- Retry con exponential backoff
- Compresion y HTTP/2

## Documentacion Completa

Para instrucciones detalladas de uso, configuracion avanzada y ejemplos:

```bash
cat GUIA_USO.md
```

Documentacion adicional:
- `GUIA_USO.md` - Guia completa de usuario (LEER PRIMERO)
- `QUICKSTART.md` - Inicio rapido en 5 minutos
- `docs/EXECUTIVE_REPORT.md` - Informe tecnico detallado
- `examples/` - Ejemplos de codigo

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

Las dependencias se instalan automaticamente con el script de instalacion

## Arquitectura

```
slayer/
├── slayer.py                    # Version base (simple, rapida)
├── slayer_enterprise_cli.py     # CLI enterprise
├── slayer_enterprise/           # Framework enterprise
│   ├── core/                    # Cliente, config, session
│   ├── security/                # SSRF, validacion, auth
│   ├── performance/             # Cache, circuit breaker
│   ├── monitoring/              # Metricas, logs, tracing
│   └── middleware/              # Sistema de plugins
├── tests/                       # Suite de pruebas
├── examples/                    # Ejemplos de uso
├── config/                      # Configuraciones
└── docs/                        # Documentacion
```

## 🐉 Integración con Herramientas de Kali Linux

SLAYER Enterprise está diseñado para complementar perfectamente las herramientas de penetration testing de Kali Linux:

### 🔗 Integración Nativa
```bash
# Combinar con reconocimiento de Nmap
nmap -sS -O target.com | grep -E '^[0-9]+/tcp' > ports.txt
./slayer load-test https://target.com:$(cat ports.txt | head -1 | cut -d'/' -f1)

# Usar resultados de dirb/gobuster para testing de endpoints
dirb https://target.com /usr/share/wordlists/dirb/common.txt | grep "+" | awk '{print $2}' | while read endpoint; do
    ./slayer quick-test "$endpoint" --method GET
done

# Integración con SQLMap para testing de inyección
./slayer authorize https://target.com/api/login
./slayer load-test https://target.com/api/login --method POST --data "username=admin&password=test" --check-sql-errors
```

### 🛡️ Características de Seguridad para Pentesting
- **Rate Limiting Inteligente**: Evita detección por WAF
- **HTTP Header Randomization**: User-Agent, Accept, Referer aleatorios  
- **Proxy Chain Support**: Integración con Tor y proxychains
- **Session Management**: Manejo automático de cookies y tokens
- **SSL/TLS Configuration**: Testing de configuraciones SSL débiles

### 📊 Reportes Específicos para Auditoría
```bash
# Generar reporte completo de security testing
./slayer security-audit https://target.com --output kali-report.json
./slayer generate-report kali-report.json --format pdf --template pentest
```

## Ejemplos Rapidos

### Solicitud GET Simple
```bash
python slayer_enterprise_cli.py request -u https://httpbin.org/get
```

### Solicitud POST con JSON
```bash
python slayer_enterprise_cli.py request -u https://httpbin.org/post -m POST \
  --header "Content-Type: application/json" \
  --data '{"key": "value"}'
```

### Prueba de Rendimiento
```bash
python slayer_enterprise_cli.py load-test -u https://httpbin.org/get -n 1000 -c 10
```

### Uso Programatico (Python)

```python
import asyncio
from slayer_enterprise import SlayerClient, SlayerConfig

async def main():
    config = SlayerConfig()
    
    async with SlayerClient(config) as client:
        # Solicitud simple
        response = await client.get("https://api.example.com/data")
        print(response.json())
        
        # Solicitud con cache
        response = await client.get(
            "https://api.example.com/data",
            cache=True,
            cache_ttl=300
        )
        
        # Batch de solicitudes
        urls = [f"https://api.example.com/item/{i}" for i in range(10)]
        responses = await client.batch_request(urls, max_concurrent=5)

asyncio.run(main())
```

## Rendimiento

| Metrica | Version Base | Version Enterprise | Mejora |
|---------|--------------|-------------------|--------|
| Throughput | 500 req/s | 10,000+ req/s | 20x |
| Latencia P95 | 800ms | 50ms | 16x |
| Uso CPU | 80% @ 1k req/s | 15% @ 1k req/s | 5.3x |
| Memoria | 5 KB/req | 1 KB/req | 5x |

## Soporte

- Repositorio: https://github.com/kndys123/slayer
- Documentacion: Ver `GUIA_USO.md`
- Issues: https://github.com/kndys123/slayer/issues

## Licencia

Ver archivo LICENSE

## Autor

SLAYER Enterprise Team

---

Para comenzar inmediatamente:
```bash
./install.sh && python slayer.py
```

Para documentacion completa:
```bash
cat GUIA_USO.md
```

## 🐉 Recursos Específicos de Kali Linux

### 📋 Verificación Completa del Sistema
```bash
# Verificar instalación y configuración completa
./verify_kali.sh
```

### 🚀 Guía Interactiva para Principiantes
```bash
# Proceso interactivo paso a paso
./kali_quickstart.sh
```

### 📚 Documentación Específica de Kali
- `KALI_GUIDE.md` - Guía completa de uso en Kali Linux
- `config/kali_optimized.json` - Configuración optimizada para Kali
- Configuración por defecto en **modo ético** con salvaguardas

### ⚡ Comandos de Inicio Rápido para Kali
```bash
# Autorización de objetivo (obligatorio)
./slayer authorize https://target-autorizado.com

# Pruebas básicas de carga
./slayer quick-test https://target-autorizado.com
./slayer load-test https://target-autorizado.com --rps 25 --duration 60

# Perfiles predefinidos para diferentes tipos de testing
./slayer profile light https://target.com      # Testing ligero (5 RPS)
./slayer profile moderate https://target.com   # Testing moderado (25 RPS)  
./slayer profile intensive https://target.com  # Testing intensivo (50 RPS)

# Dashboard en tiempo real
./slayer dashboard  # http://localhost:8000
```

### 🔒 Consideraciones Éticas para Kali Linux

**IMPORTANTE**: SLAYER está configurado con salvaguardas específicas en Kali Linux:
- ✅ **Autorización Obligatoria**: No se ejecutan pruebas sin verificación de autorización
- ✅ **Límites de Seguridad**: Rate limiting automático para evitar ataques DoS accidentales
- ✅ **SLO Monitoring**: Parada automática si se detectan anomalías en el objetivo
- ✅ **Logs Auditables**: Registro completo de todas las actividades para auditoría

**Solo usar contra objetivos autorizados para pentesting legítimo**
- Check network connectivity
- Ensure the target allows incoming connections
- Verify firewall rules

### Authorization Failures

If authorization fails:
- Confirm the token is correct
- Re-authorize the target
- Check `load_test_config.json` for proper configuration

### Performance Issues

If the tool is slow:
- Reduce thread count
- Increase delay between requests
- Check system resources (CPU, memory)
- Verify network bandwidth

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📧 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation
- Review audit logs for debugging

## 🙏 Acknowledgments

Built for professional security testing and performance analysis.

---

**⚠️ DISCLAIMER**: This tool is intended for authorized security testing and performance analysis only. Users are responsible for ensuring they have proper authorization before testing any system. Unauthorized testing may be illegal in your jurisdiction.

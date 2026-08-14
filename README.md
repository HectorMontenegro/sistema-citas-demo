<p align="center">
  <img src="docs/images/citabot-cover.png" alt="CitaBot: automatización de citas web" width="560">
</p>

<h1 align="center">CitaBot</h1>

<p align="center">
  Automatización de solicitudes y programación simulada de citas web.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white">
  <img alt="MySQL" src="https://img.shields.io/badge/MySQL-8.x-4479A1?logo=mysql&logoColor=white">
  <img alt="Selenium" src="https://img.shields.io/badge/Selenium-4.x-43B02A?logo=selenium&logoColor=white">
  <img alt="Tests" src="https://img.shields.io/badge/tests-14%20passed-success">
</p>

## ¿Qué problema resuelve?

Cuando las solicitudes llegan por distintos medios, revisar disponibilidad,
procesarlas una por una y comunicar el resultado puede convertirse en una tarea
repetitiva y difícil de controlar. CitaBot centraliza ese recorrido: recibe la
solicitud, la registra, ejecuta el proceso de forma secuencial y conserva el
estado de cada operación.

Es un proyecto independiente que demuestra cómo convertir un proceso manual en
un flujo automatizado, trazable y desplegable. La edición pública reemplaza la
plataforma original por un portal local simulado, por lo que puede revisarse sin
cuentas reales ni dependencia de servicios externos.

## Funcionalidades principales

- Recepción de solicitudes mediante una API Flask protegida con token local.
- Validación de datos y rechazo explícito de contraseñas de terceros.
- Cola persistente en MySQL con procesamiento secuencial.
- Estados `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED` y `CANCELLED`.
- Automatización con Selenium sobre un portal local incluido en el proyecto.
- Reintentos limitados, control de cancelación y registro de eventos.
- Integración opcional con Google Forms mediante Apps Script.
- Notificación local del resultado y trazabilidad del proceso.

## Tecnologías

**Backend y automatización**

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?logo=flask&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-43B02A?logo=selenium&logoColor=white)

**Datos e integración**

![MySQL](https://img.shields.io/badge/MySQL-4479A1?logo=mysql&logoColor=white)
![Google Forms](https://img.shields.io/badge/Google%20Forms-7248B9?logo=googleforms&logoColor=white)

**Infraestructura y calidad**

![Linux](https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![Clouding.io](https://img.shields.io/badge/Clouding.io-Cloud-1565C0)
![Git](https://img.shields.io/badge/Git-F05032?logo=git&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?logo=pytest&logoColor=white)

## Cómo funciona

```mermaid
flowchart LR
    A[Google Forms o cliente HTTP] --> B[API Flask]
    B --> C[(Cola MySQL)]
    C --> D[Worker Python]
    D --> E[Selenium]
    E --> F[Portal local simulado]
    F --> D
    D --> C
    C --> G[Eventos y trazabilidad]
    D --> H[Notificación local]
```

1. La API recibe una solicitud ficticia con correo de contacto y rango de fechas.
2. MySQL la registra como `PENDING`.
3. El worker toma una única solicitud y la cambia a `PROCESSING`.
4. Selenium consulta y selecciona una fecha en el portal local simulado.
5. El sistema vuelve a comprobar si la solicitud fue cancelada antes de confirmar.
6. El resultado y sus eventos quedan registrados para consulta posterior.

La solución separa API, dominio, persistencia, procesamiento, automatización y
notificaciones. El detalle se encuentra en la
[documentación de arquitectura](docs/ARCHITECTURE.md).

## Puesta en marcha

### Requisitos

- Python 3.11 o superior.
- Docker y Docker Compose.
- Google Chrome.

### Instalación

```bash
git clone https://github.com/HectorMontenegro/sistema-citas-demo.git
cd sistema-citas-demo
cp .env.example .env
docker compose up -d mysql
python -m venv .venv
python -m pip install -e ".[dev]"
```

Completa los valores `CHANGE_ME` de `.env` con datos locales. Después inicia la
API y el portal simulado:

```bash
python -m appointment_demo.api
```

Registra una solicitud de prueba:

```bash
curl -X POST http://127.0.0.1:5000/api/requests \
  -H "Content-Type: application/json" \
  -H "X-Demo-Token: TU_TOKEN_LOCAL" \
  -d '{"contact_email":"demo@example.test","preferred_from":"2026-09-01","preferred_to":"2026-11-30"}'
```

Finalmente, ejecuta una iteración del worker:

```bash
python -m appointment_demo.worker --once
```

## Despliegue del prototipo

El prototipo original se ejecutó de manera continua en un servidor Linux de
Clouding.io. La captura documenta la experiencia de configuración y operación
de infraestructura; el servidor mostrado está desactivado y la edición pública
se ejecuta en un entorno local simulado.

<p align="center">
  <img src="docs/images/cloud-prototype-server.png" alt="Servidor Linux utilizado para desplegar el prototipo" width="760">
</p>

## Calidad y seguridad

```bash
pytest
ruff check .
ruff format --check .
bandit -r src
```

- 14 pruebas automatizadas aprobadas.
- Ruff sin errores de estilo o formato.
- Bandit sin vulnerabilidades detectadas en `src`.
- Escaneo de secretos sin credenciales encontradas.

La edición pública no incluye direcciones, selectores, credenciales, cookies ni
sesiones de plataformas externas. Selenium rechaza cualquier destino distinto
de loopback y las notificaciones se registran localmente, sin envío SMTP real.
Consulta [uso y límites](ETHICAL_USE.md) y [seguridad](SECURITY.md).

## Estructura

```text
sistema-citas-demo/
├── src/appointment_demo/     # API, dominio, persistencia, worker y Selenium
├── sql/schema.sql            # Cola, estados y auditoría
├── google_apps_script/       # Integración opcional con Google Forms
├── tests/                    # Pruebas de API, servicio y publicación segura
├── docs/                     # Arquitectura y evidencias visuales
├── docker-compose.yml        # MySQL reproducible
└── .github/workflows/        # Validación automática del proyecto
```

## Próximas mejoras

- Panel local para consultar solicitudes y eventos.
- Métricas de tiempos, reintentos y resultados.
- Pruebas de integración automatizadas con MySQL y Chrome.
- Autenticación para operar únicamente sobre sistemas propios o autorizados.

## Autor

**Hector Samir Montenegro Villalobos**<br>
Estudiante de Ingeniería de Sistemas interesado en desarrollo de software,
automatización de procesos y arquitectura de soluciones.

Este repositorio es una adaptación pública para portafolio. No representa un
servicio activo de citas ni una afiliación con plataformas externas.

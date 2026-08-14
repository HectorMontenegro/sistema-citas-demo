# Arquitectura y decisiones de seguridad

## Flujo

1. La API recibe una solicitud sin credenciales de terceros.
2. MySQL la registra como `PENDING` y crea un evento de auditoria.
3. El worker toma una fila de forma atomica y la pasa a `PROCESSING`.
4. Selenium busca una fecha dentro del rango en el portal local simulado.
5. Antes de confirmar, el worker vuelve a consultar si existe cancelacion.
6. El resultado queda como `COMPLETED`, vuelve a `PENDING` para un reintento
   limitado o termina como `FAILED`/`CANCELLED`.

## Estados

| Estado | Significado |
| --- | --- |
| `PENDING` | Espera ser procesada. |
| `PROCESSING` | Fue tomada de forma exclusiva por un worker. |
| `COMPLETED` | La confirmacion simulada termino correctamente. |
| `FAILED` | Alcanzo el maximo de intentos o fallo definitivamente. |
| `CANCELLED` | Fue cancelada antes de la confirmacion. |

## Controles incorporados

- Parametros SQL en lugar de concatenacion de entradas.
- Token comparado en tiempo constante.
- Respuestas de error genericas; los detalles quedan solo en logs.
- Rechazo de campos como `password`, `credentials` o `portal_url`.
- Seleccion atomica con `FOR UPDATE SKIP LOCKED`.
- Si no puede verificarse una cancelacion, el flujo falla de forma segura.
- Maximo de intentos configurable y sin ciclos de espera de horas.
- Allowlist inmutable de hosts locales para el adaptador Selenium.
- Separacion entre dominio, persistencia, automatizacion y notificaciones.

## Delimitacion

El producto se encuentra en estado de **prototipo demostrable**. Prueba la
arquitectura en un entorno controlado, pero no es un servicio de citas real ni
esta preparado para operar contra sistemas de terceros.

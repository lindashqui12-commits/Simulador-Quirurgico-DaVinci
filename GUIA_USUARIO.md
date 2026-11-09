# Guía de usuario — Simulador Da Vinci

## Preparación
1. Conectar el receptor USB del Logitech F710; selector en **X**. Verificar con `Win + R` → `joy.cpl`.
2. Abrir CoppeliaSim y cargar la escena de los dos PSM con paciente, tejido y aguja.
3. Abrir Orthanc en `http://localhost:8042` para recibir las imágenes DICOM.
4. Ejecutar `src/simulador_da_vinci.py` o la aplicación Windows compilada.
5. Registrar **datos ficticios**: nombre, ID, fecha de nacimiento, sexo y descripción del estudio.

## Controles previstos en la versión más reciente
| Control | Acción |
|---|---|
| Joystick izquierdo | Desplazamiento X/Y del instrumento seleccionado |
| Joystick derecho vertical | Desplazamiento Z |
| LB / RB | Seleccionar PSM1 / PSM2 |
| Y | Acercar el instrumento a la aguja |
| A | Sujetar aguja (solo a distancia admisible) |
| B | Soltar aguja |
| X | Validar/completar puntada |
| Start | Intentar aceptar avisos informativos OK; **verificar en esta instalación** |
| Back | Reiniciar sutura (puede solicitar confirmación) |
| Cruceta abajo, mantener 2 s | HOME, restaurar posiciones articulares iniciales |
| RT | Capturar imagen y enviar a Orthanc |

## Práctica
1. Comprobar que la simulación esté detenida para los movimientos articulares controlados por Python; las cámaras podrían no actualizarse en ese estado.
2. Seleccionar PSM1 con LB, pulsar Y para aproximar el brazo a la aguja y A para sujetarla.
3. Mover con los joysticks hacia los objetivos visuales y pulsar X cuando el sistema acepte la proximidad.
4. Pulsar RT para generar PNG + DICOM y enviar el DICOM al PACS.
5. Abrir Orthanc, buscar el ID del paciente simulado y comprobar estudio/serie/instancia.

## Solución de problemas
- **No se mueve el control:** comprobar `joy.cpl`, batería/receptor y estado de simulación; verificar lectura con `pygame`.
- **Cámaras negras:** los sensores suelen requerir renderizado activo; revisar sensor, escena y estado de simulación.
- **Aguja no encontrada:** comprobar las rutas `/Needle_40mm`, `/Needle_40mm/needle_respondable` y `/Needle_40mm/needle_tip`.
- **Orthanc no recibe:** verificar `http://localhost:8042`, credenciales y que el archivo `.dcm` se haya guardado en `capturas/`.
- **Start no acepta OK:** la gestión de diálogos modales puede bloquear el sondeo de pygame; usar ratón como alternativa y registrar la incidencia.
- **Brazos desconfigurados:** no guardar la escena alterada; recuperar copia y calibrar HOME al inicio.

**Aviso:** demostración académica, sin datos personales reales ni uso clínico.

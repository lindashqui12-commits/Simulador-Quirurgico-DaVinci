# Documento técnico — Simulador quirúrgico Da Vinci

## 1. Objetivo
Desarrollar un entorno académico de entrenamiento en sutura asistida por dos brazos robóticos PSM con interfaz de usuario, mando físico, cámaras virtuales y registro de imágenes DICOM en un PACS.

## 2. Arquitectura
`Logitech F710 → pygame → PySide6 / controlador XYZ (Python) → ZMQ Remote API (puerto 41000) → CoppeliaSim → sensores de visión → PNG / DICOM Secondary Capture → Orthanc REST /instances`

## 3. Entorno
- Windows 11; Python 3.12; PySide6; pygame 2.6.1; NumPy; `coppeliasim-zmqremoteapi-client`.
- CoppeliaSim 4.10, dos brazos PSM1 y PSM2, juntas J1–J7, herramientas TipOrient/TipOrient2.
- Escena con paciente, camilla, médico, phantom de tejido, aguja y sensores `Camara_Sutura`, `Camara_General`, `Camara_Medico`.
- Orthanc local por HTTP puerto 8042; autenticación configurable mediante variables de entorno.

## 4. Antecedentes y origen del proyecto

El presente proyecto surge de la necesidad de desarrollar una herramienta de simulación interactiva para la práctica de procedimientos quirúrgicos asistidos por sistemas robóticos, específicamente mediante la manipulación de instrumentos y la realización de suturas.

Como punto de partida, se utilizó el repositorio de código abierto **dynamic-dvrk-coppeliasim-simulator**, desarrollado por **marcofer** y disponible en GitHub:

**Repositorio original:** https://github.com/marcofer/dynamic-dvrk-coppeliasim-simulator

Este repositorio proporcionó la base de simulación del sistema robótico dVRK (*da Vinci Research Kit*) en CoppeliaSim, incluyendo los modelos de los brazos quirúrgicos PSM1 y PSM2, sus articulaciones y componentes de simulación.

A partir de esta base, se desarrollaron modificaciones e integraciones para transformar el modelo robótico en un entorno de entrenamiento quirúrgico interactivo.

### 5. Desarrollo e integraciones realizadas

Durante el proyecto se implementaron las siguientes funcionalidades:

1. **Análisis del modelo robótico:** identificación de los componentes, articulaciones, jerarquías y referencias espaciales de los brazos PSM1 y PSM2.
2. **Comunicación con Python:** integración de CoppeliaSim mediante ZMQ Remote API para consultar posiciones y controlar articulaciones.
3. **Interfaz gráfica:** desarrollo de una aplicación con Python y PySide6 para visualizar el entorno y controlar los instrumentos.
4. **Control físico:** integración del Logitech F710 para realizar movimientos en los ejes X, Y y Z, seleccionar brazos y ejecutar acciones de sutura.
5. **Escenario quirúrgico:** incorporación de elementos visuales como paciente, camilla, médico, tejido de práctica y cámaras virtuales.
6. **Sutura guiada:** implementación de puntos de referencia, representación visual de puntadas y validación por proximidad.
7. **Gestión de pacientes:** registro de información ficticia para identificar las prácticas quirúrgicas.
8. **Integración DICOM/PACS:** captura de imágenes, generación de archivos DICOM y envío al servidor Orthanc.
9. **Aplicación de escritorio:** preparación del sistema para su ejecución en Windows mediante una aplicación independiente.

### 6. Reconocimiento de autoría

Se reconoce al autor del repositorio original por proporcionar la base de simulación robótica utilizada en el proyecto.

El desarrollo académico presentado corresponde a las modificaciones, adaptaciones e integraciones realizadas sobre dicha base. Los componentes originales conservan la atribución y las condiciones de licencia que les correspondan.

## 7. Comunicación y control
El cliente Python usa la API remota ZMQ para leer y modificar estados articulares, obtener posiciones y leer imágenes de sensores. El control cartesiano utiliza una aproximación numérica del Jacobiano para mover la punta en incrementos. Las articulaciones dinámicas J1/J2 presentaron inestabilidad al ejecutar la simulación; por ello se priorizó control con simulación detenida. La sutura se representa visualmente y la proximidad del instrumento al objetivo determina la validación; no hay modelo de penetración de tejido.

## 8. Captura e interoperabilidad
El programa toma el último fotograma RGB disponible de `Camara_Sutura`, lo guarda como PNG y genera DICOM Secondary Capture (modalidad `OT`, codificación RGB de 8 bits). Incluye `PatientName`, `PatientID`, `PatientBirthDate`, `PatientSex`, `StudyDescription`, `StudyInstanceUID`, `SeriesInstanceUID` y `SOPInstanceUID`. Las capturas de una misma sesión comparten estudio/serie y tienen identificador de instancia individual. Envía el archivo con `POST /instances`, `Content-Type: application/dicom`.

## 9. Seguridad, alcance y limitaciones
- Solo datos ficticios; no se validó como dispositivo médico ni simulador clínico.
- Sin planificación de trayectorias ni garantía de evitar colisiones.
- La disponibilidad de cámara con simulación detenida depende del manejo explícito de sensores.
- Start/OK requiere validación funcional en Windows; diálogos modales pueden interrumpir la lectura del mando.
- La comunicación Orthanc HTTP local no equivale a infraestructura segura para información clínica real.
- La escena de origen y sus componentes pueden tener licencias independientes; revisar antes de publicarlos.

## 10. Pruebas y evidencias
| Prueba | Evidencia | Estado |
|---|---|---|
| Lectura de F710 | `joy.cpl`, pygame detectó 6 ejes, 11 botones, 1 hat | Comprobado por usuario |
| Movimiento XYZ | Control F710 movió los brazos | Comprobado por usuario |
| Restauración escena | Se recuperaron sutura y posiciones | Comprobado por usuario |
| Registro de paciente y flujo GUI | Reportado funcional | Reportado por usuario |
| Captura y envío a Orthanc | Captura funcional reportada, verificar instancia y metadatos en PACS | Pendiente de evidencia documental |
| Start para OK | Usuario reportó fallo | Pendiente de corrección/prueba |
| App Windows `.exe` | BAT y código disponibles | Compilación/ejecución final por verificar |

## 11. Trabajo futuro
Soporte físico para aguja, HOME persistente, corrección robusta de Start/OK, renderizado de cámaras durante movimiento, métricas de entrenamiento y prueba end-to-end documentada en Orthanc.

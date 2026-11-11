# Simulador quirúrgico Da Vinci — Sutura guiada

Proyecto académico de simulación robótica en **CoppeliaSim** con interfaz **Python/PySide6**, control **Logitech F710** y exportación de capturas **DICOM Secondary Capture** hacia **Orthanc**.

> **Estado:** prototipo académico. Los movimientos XYZ, el agarre de la aguja y las puntadas son aproximaciones de simulación; no representan cirugía real ni validación clínica. Las cámaras pueden requerir la simulación activa y su funcionamiento depende de la escena y la configuración de CoppeliaSim.

## Funciones implementadas
- Escena de dos instrumentos PSM1/PSM2 con paciente, camilla, médico, tejido y aguja.
- GUI PySide6, selección de brazos, movimientos XYZ y sutura guiada con tolerancia.
- Control inalámbrico Logitech F710 y restauración HOME según la versión.
- Registro de paciente **ficticio** al comenzar la práctica.
- Captura PNG y DICOM desde la cámara de sutura y envío HTTP POST a Orthanc (`/instances`).

## Requisitos
- Windows 11 (entorno de desarrollo probado), Python 3.12 y CoppeliaSim 4.10 con la escena cargada.
- Logitech F710 (modo X), receptor USB, Orthanc local opcional para el envío.
- Paquetes indicados en `requirements.txt`.

## Instalación rápida
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src\simulador_da_vinci.py
```
Abrir primero CoppeliaSim y cargar **la escena del proyecto** (archivo no incluido: debe añadirse a `escena/` si su licencia permite redistribución). Para recibir estudios, iniciar Orthanc en `http://127.0.0.1:8042`. Si tiene autenticación, definir `ORTHANC_USER`, `ORTHANC_PASSWORD` y, si aplica, `ORTHANC_URL` en el entorno local; nunca publicar credenciales.

## Archivos
- [`GUIA_USUARIO.md`](GUIA_USUARIO.md): operación paso a paso y botones.
- [`documento_tecnico.md`](documento_tecnico.md): arquitectura, API, DICOM y limitaciones.
- [`LICENSE.md`](LICENSE.md): **plantilla MIT pendiente de nombre legal del autor**.
- [`informe/INFORME.md`](informe/INFORME.md): informe académico editable.
- [`video/GUION_VIDEO.md`](video/GUION_VIDEO.md): guion de demostración de 3–5 minutos.
- [`ejemplos_dicom/`](ejemplos_dicom/): tres imágenes **sintéticas**, no capturas reales de CoppeliaSim.

## Compilar para Windows
Con el proyecto en una carpeta que contenga `.venv`, copiar `scripts/CREAR_APP_DAVINCI.bat` a la raíz junto con `simulador_da_vinci_app.py` (desde `src/`) y ejecutar el BAT. El resultado esperado es `dist/DaVinci_Simulador/DaVinci_Simulador.exe`. La compilación requiere Windows y PyInstaller.

## Licencias y atribuciones
La licencia MIT propuesta cubre únicamente el código propio del autor. La escena dVRK/CoppeliaSim y cualquier material de terceros mantienen sus respectivas licencias y requieren atribución y permiso de redistribución.

## Créditos y referencias

El modelo robótico utilizado como base proviene del repositorio [dynamic-dvrk-coppeliasim-simulator](https://github.com/marcofer/dynamic-dvrk-coppeliasim-simulator), desarrollado por **marcofer**.

El presente proyecto incorpora desarrollos adicionales en Python, control físico mediante Logitech F710, interfaz gráfica, simulación guiada de sutura y comunicación DICOM con Orthanc PACS.

# Guía de usuario — Simulador Da Vinci

## 1. Introducción

Esta guía describe el procedimiento para instalar y ejecutar el **Simulador Quirúrgico Da Vinci**, desarrollado en Python y CoppeliaSim.

El sistema permite controlar dos brazos robóticos PSM1 y PSM2, realizar prácticas virtuales de sutura mediante un control Logitech F710, visualizar cámaras del entorno quirúrgico y generar imágenes DICOM para su almacenamiento en Orthanc PACS.

Para utilizar el simulador es necesario descargar el repositorio, instalar las herramientas requeridas y establecer la comunicación entre Python y CoppeliaSim.

## 2. Programas necesarios

Antes de iniciar, instalar los siguientes programas:

| Programa | Función |
|---|---|
| Python 3.12 | Ejecutar el código del simulador. |
| CoppeliaSim Edu V4.10.0 | Abrir y visualizar el escenario quirúrgico. |
| Git | Descargar el repositorio mediante PowerShell. |
| Windows PowerShell | Ejecutar los comandos de instalación e inicio. |
| Orthanc PACS | Recibir y almacenar las imágenes DICOM. |
| Logitech F710 | Control físico de los instrumentos robóticos. |

Enlaces de descarga:

- [Python](https://www.python.org/downloads/)
- [CoppeliaSim](https://www.coppeliarobotics.com/)
- [Git para Windows](https://git-scm.com/downloads/win)
- [Orthanc](https://www.orthanc-server.com/)

**Nota:** Se recomienda utilizar Python 3.12 y CoppeliaSim V4.10.0, versiones empleadas durante el desarrollo del proyecto.

## 3. Descargar el repositorio desde PowerShell

### Paso 1. Abrir PowerShell

En Windows, buscar **PowerShell** en el menú Inicio y abrirlo.

### Paso 2. Seleccionar una carpeta de trabajo

Por ejemplo, para trabajar desde Documentos:

```powershell
cd "$HOME\Documents"
```

### Paso 3. Descargar el proyecto

Copiar y ejecutar el siguiente comando:

```powershell
git clone https://github.com/lindashqui12-commits/Simulador-Quirurgico-DaVinci.git
```

Este comando descarga los archivos del repositorio a la computadora.

### Paso 4. Entrar a la carpeta del proyecto

```powershell
cd Simulador-Quirurgico-DaVinci
```

## 4. Configurar Python

### Paso 1. Comprobar que Python está instalado

```powershell
py -3.12 --version
```

Si aparece una versión de Python 3.12, continuar.

### Paso 2. Crear un entorno virtual

```powershell
py -3.12 -m venv .venv
```

El entorno virtual permite instalar las bibliotecas necesarias sin modificar otras instalaciones de Python.

### Paso 3. Instalar las dependencias

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

Posteriormente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Este comando instala las bibliotecas declaradas en el proyecto, necesarias para la interfaz gráfica, el control Logitech, la comunicación con CoppeliaSim y la generación de imágenes DICOM.

## 5. Abrir la escena en CoppeliaSim

### Paso 1. Iniciar CoppeliaSim

Abrir **CoppeliaSim Edu V4.10.0**.

### Paso 2. Cargar el escenario quirúrgico

En el menú principal seleccionar:

**File → Open scene**

Buscar y abrir:

`escena/dyn_dVRK_2arms.ttt`

La escena debe contener los dos brazos robóticos PSM1 y PSM2, el escenario quirúrgico, las cámaras y los objetos de práctica.

**Importante:** si el archivo `.ttt` no está incluido en el repositorio descargado, será necesario obtener la escena correspondiente siguiendo las instrucciones de `escena/LEEME.md`.

### Paso 3. Verificar el escenario

Comprobar que los brazos robóticos y los elementos del escenario se visualizan correctamente.

Para la versión de control cartesiano utilizada en este proyecto, se recomienda mantener inicialmente la simulación detenida, debido a las limitaciones de estabilidad observadas durante las pruebas con articulaciones dinámicas.

### Paso 4. Verificar la comunicación ZMQ

El simulador utiliza **ZMQ Remote API** para establecer comunicación entre Python y CoppeliaSim.

La configuración del cliente debe coincidir con el puerto del servidor ZMQ de CoppeliaSim. En la versión de código revisada se utiliza el puerto `23000`.

CoppeliaSim debe permanecer abierto mientras se ejecuta la aplicación Python.

## 6. Conectar el control Logitech F710

1. Conectar el receptor inalámbrico USB del Logitech F710 a la computadora.
2. Colocar el interruptor posterior del control en posición **X (XInput)**.
3. Encender o activar el control.
4. Verificar que Windows lo reconozca.

Para comprobar su funcionamiento, presionar `Win + R`, escribir `joy.cpl` y abrir las propiedades del controlador.

El programa utiliza la biblioteca `pygame` para interpretar los movimientos de los joysticks y las pulsaciones de los botones.

## 7. Ejecutar el simulador desde PowerShell

Una vez descargado el proyecto, instaladas las dependencias y abierta la escena de CoppeliaSim, regresar a PowerShell.

### Paso 1. Ubicarse en el repositorio

```powershell
cd "$HOME\Documents\Simulador-Quirurgico-DaVinci"
```

### Paso 2. Ejecutar la aplicación

Este comando inicia el código principal documentado del simulador.

Para ejecutar la variante preparada para la aplicación de Windows, se puede utilizar:

```powershell
.\.venv\Scripts\python.exe .\src\simulador_da_vinci_app.py
```

### Paso 3. Registrar un paciente

Al iniciar correctamente la aplicación, aparecerá una ventana de registro.

Ingresar los datos ficticios del paciente, como nombre, identificador y fecha de nacimiento, y aceptar para continuar.

### Paso 4. Utilizar la interfaz

La aplicación mostrará las cámaras del escenario, los controles y las funciones para interactuar con los brazos PSM1 y PSM2.

El usuario podrá seleccionar un brazo, manipular los instrumentos y realizar la práctica guiada de sutura.

## 8. Configurar Orthanc PACS

Para utilizar la función de almacenamiento DICOM, iniciar Orthanc en la computadora.

Abrir en el navegador:

http://localhost:8042

Verificar que la interfaz de Orthanc esté disponible.

El simulador utiliza la API REST de Orthanc para enviar los archivos DICOM mediante solicitudes HTTP al endpoint `/instances`.

Al capturar una imagen, el programa genera un archivo DICOM Secondary Capture y realiza el envío al servidor configurado.

Si Orthanc requiere autenticación, será necesario configurar las credenciales correspondientes en la aplicación.

## 9. Orden recomendado de ejecución

Para iniciar correctamente una práctica:

1. Conectar el Logitech F710.
2. Iniciar Orthanc, si se utilizará la captura DICOM.
3. Abrir CoppeliaSim.
4. Cargar la escena `dyn_dVRK_2arms.ttt`.
5. Abrir PowerShell en la carpeta del repositorio.
6. Ejecutar el archivo Python del simulador.
7. Registrar un paciente ficticio.
8. Verificar las cámaras y la comunicación con los brazos.
9. Iniciar la práctica de sutura.
10. Capturar imágenes y comprobar su recepción en Orthanc.

## 10. Solución de problemas frecuentes

| Problema | Posible solución |
|---|---|
| `python` o `py` no reconocido | Instalar Python 3.12 y comprobar su disponibilidad. |
| `ModuleNotFoundError` | Instalar las dependencias desde `requirements.txt` usando el entorno virtual. |
| Error de conexión con CoppeliaSim | Verificar que CoppeliaSim esté abierto y que el puerto ZMQ coincida. |
| No se detecta Logitech | Revisar receptor USB, modo XInput y detección en `joy.cpl`. |
| No aparecen las cámaras | Comprobar que se abrió la escena correcta y que existen los sensores esperados. |
| Orthanc no recibe imágenes | Verificar que el servidor esté iniciado, su dirección, puerto y autenticación. |
| No se encuentra la escena `.ttt` | Revisar la carpeta `escena` y las instrucciones de `LEEME.md`. |

## 11. Consideraciones de uso

El simulador fue desarrollado con fines académicos y de entrenamiento virtual.

No constituye un dispositivo médico certificado ni debe utilizarse para planificar o ejecutar procedimientos quirúrgicos reales.

Las imágenes DICOM generadas corresponden a capturas de un entorno simulado y deben asociarse únicamente con pacientes ficticios.

______________________________________________________________________________________________

# Preparación
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

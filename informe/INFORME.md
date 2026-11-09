# INFORME DE MINI PROYECTO — SIMULADOR QUIRÚRGICO DA VINCI

## Carátula
**Universidad:** Mariano Gálvez de Guatemala  
**Facultad / carrera:** Ingeniería Biomédica  
**Curso:** Sistemas Inteligentes 
**Proyecto:** Simulador de sutura asistida por dos brazos robóticos tipo Da Vinci  
**Autor(es):** Linda Pantaleón 
**Docente:** Edgar 
**Lugar y fecha:** Guatemala, noviembre de 2026

## Introducción
La simulación quirúrgica es una herramienta de aprendizaje para explorar la coordinación de instrumentos robóticos y el seguimiento de procedimientos guiados. Este proyecto integra una escena virtual de dos brazos PSM en CoppeliaSim, una aplicación gráfica desarrollada en Python, un control físico Logitech F710 y un servidor Orthanc para almacenar imágenes de la práctica en formato DICOM.

## Resumen
Se desarrolló un prototipo académico de simulador de sutura con dos brazos robóticos virtuales y una interfaz PySide6. El sistema utiliza la API remota ZMQ de CoppeliaSim para controlar articulaciones y consultar posiciones, mientras que pygame recibe entradas del Logitech F710. La práctica incorpora una aguja virtual, objetivos de sutura, registro de paciente ficticio y captura de imágenes DICOM Secondary Capture enviadas a Orthanc por HTTP. Se logró el control de los brazos mediante el mando y la recuperación de la escena; permanecen limitaciones en la dinámica durante la simulación, la visualización simultánea de cámaras y la gestión de avisos mediante Start. El sistema no reproduce sutura física real y se destina únicamente a demostración académica.

## Conclusiones
1. La combinación de CoppeliaSim, Python y el Logitech F710 permite demostrar control interactivo de dos instrumentos quirúrgicos virtuales.
2. La exportación DICOM y la integración con Orthanc muestran un flujo de interoperabilidad entre simulación e infraestructura PACS, pendiente de documentar con evidencia final del estudio recibido.
3. La representación de sutura y el agarre de aguja son simulados, por lo que no sustituyen la física de tejido ni la validación clínica.
4. Para una versión posterior se recomienda mejorar la estabilidad dinámica, el renderizado de las cámaras, la restauración HOME y la aceptación de avisos desde el mando.

## Evidencias 
- Captura de la GUI y registro ficticio.
<img width="536" height="382" alt="Captura de pantalla 2026-11-08 213718" src="https://github.com/user-attachments/assets/e796a6b2-f632-4615-bc93-49530350abda" />

- Captura del control F710 y escena CoppeliaSim.
<img width="1807" height="1095" alt="Captura de pantalla 2026-11-08 213732" src="https://github.com/user-attachments/assets/ccdb9479-787d-43d1-b868-629649df881a" />

- Captura PNG de sutura y DICOM recibido en Orthanc.
<img width="1892" height="842" alt="Captura de pantalla 2026-11-08 210937" src="https://github.com/user-attachments/assets/2b6eb665-e875-4874-bff9-70b7ae81e639" />
<img width="1890" height="990" alt="Captura de pantalla 2026-11-08 214612" src="https://github.com/user-attachments/assets/24f8a8d5-91c8-4985-975f-310a7880ae58" />

- Enlace del video demostrativo de 3–5 minutos.

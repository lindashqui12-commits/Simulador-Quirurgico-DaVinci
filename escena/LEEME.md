# Escena quirúrgica de CoppeliaSim

## Descripción

Esta carpeta contiene la escena utilizada para el desarrollo del **Simulador Quirúrgico Da Vinci**, implementado en CoppeliaSim.

**Archivo principal:** `dyn_dVRK_2arms.ttt`

La escena se utiliza como entorno virtual para la manipulación de los instrumentos robóticos PSM1 y PSM2 y la práctica simulada de sutura quirúrgica.

## Origen de la escena

El modelo robótico utilizado como punto de partida proviene del repositorio:

[dynamic-dvrk-coppeliasim-simulator — marcofer](https://github.com/marcofer/dynamic-dvrk-coppeliasim-simulator)

A partir de esta base se realizaron adaptaciones para incorporar un escenario de entrenamiento quirúrgico y permitir su interacción mediante una aplicación desarrollada en Python.

## Componentes del escenario

El proyecto contempla los siguientes elementos:

- Dos brazos quirúrgicos: PSM1 y PSM2.
- Paciente y camilla quirúrgica.
- Médico como elemento visual del escenario.
- Tejido de práctica para sutura.
- Aguja quirúrgica virtual.
- Tres cámaras: sutura, vista general y médico.

Las marcas y puntadas visuales de la práctica pueden generarse desde la aplicación Python al iniciar la sesión.

## Requisitos

- CoppeliaSim V4.10.0.
- Python y las dependencias indicadas en `requirements.txt`.
- Aplicación del simulador Da Vinci.
- Logitech F710 para control físico.

## Cómo abrir la escena

1. Abrir CoppeliaSim.
2. Seleccionar **File → Open scene**.
3. Buscar el archivo `dyn_dVRK_2arms.ttt`.
4. Abrir la escena y verificar que se visualicen los brazos y el escenario quirúrgico.
5. Ejecutar la aplicación del simulador Da Vinci.

Para el control XYZ desarrollado en este proyecto, inicialmente se trabaja con la simulación detenida debido a las limitaciones observadas en el comportamiento de los motores dinámicos.

## Reconocimiento

Se reconoce al autor **marcofer** por el repositorio utilizado como base. Las modificaciones académicas y la integración de la interfaz, el control Logitech y la captura DICOM corresponden al desarrollo de este proyecto.

La redistribución de los componentes originales está sujeta a sus respectivas condiciones de licencia.

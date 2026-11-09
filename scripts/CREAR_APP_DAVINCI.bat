@echo off
setlocal
cd /d "%~dp0"
echo ================================================
echo  DA VINCI - COMPILAR A APLICACION WINDOWS
 echo ================================================
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Copia este BAT a la carpeta que contiene .venv
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install --upgrade pyinstaller
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onedir --windowed --name "DaVinci_Simulador" --collect-all pygame --collect-all coppeliasim_zmqremoteapi_client "simulador_da_vinci_app.py"
if errorlevel 1 goto error
echo.
echo LISTO: dist\DaVinci_Simulador\DaVinci_Simulador.exe
echo Para usarlo: doble clic al EXE, con CoppeliaSim abierto.
echo Copia la carpeta COMPLETA si la mueves a otra ubicacion.
pause
exit /b 0
:error
echo ERROR al compilar. Revisa los mensajes de arriba.
pause
exit /b 1

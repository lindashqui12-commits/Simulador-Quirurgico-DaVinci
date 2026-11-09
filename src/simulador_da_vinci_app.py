import sys
import math
import time
import os
import json
import uuid
import urllib.request
import urllib.error
import base64
from pathlib import Path
from datetime import datetime

import numpy as np
import pygame
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QMessageBox,
    QComboBox, QGroupBox, QDockWidget, QScrollArea, QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QDateEdit, QCheckBox)
from coppeliasim_zmqremoteapi_client import RemoteAPIClient



class DialogoPaciente(QDialog):
    """Datos de una sesión de entrenamiento; no usar información clínica real."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Nueva práctica · Datos del paciente simulado')
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        aviso = QLabel('Datos para identificar el estudio DICOM en Orthanc.\n'
                       'Utiliza únicamente datos ficticios para esta demostración.')
        aviso.setWordWrap(True)
        layout.addWidget(aviso)
        form = QFormLayout()
        self.nombre = QLineEdit('PACIENTE SIMULADO')
        self.identificador = QLineEdit('SIM-001')
        self.fecha = QDateEdit()
        self.fecha.setCalendarPopup(True)
        self.fecha.setDisplayFormat('dd/MM/yyyy')
        self.fecha.setDate(self.fecha.date().addYears(-25))
        self.sexo = QComboBox()
        self.sexo.addItem('Sin especificar', '')
        self.sexo.addItem('Femenino', 'F')
        self.sexo.addItem('Masculino', 'M')
        self.descripcion = QLineEdit('Práctica simulada de sutura Da Vinci')
        form.addRow('Nombre del paciente:', self.nombre)
        form.addRow('Identificador (ID):', self.identificador)
        form.addRow('Fecha de nacimiento:', self.fecha)
        form.addRow('Sexo:', self.sexo)
        form.addRow('Descripción del estudio:', self.descripcion)
        layout.addLayout(form)
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.validar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def validar(self):
        if not self.nombre.text().strip() or not self.identificador.text().strip():
            QMessageBox.warning(self, 'Datos incompletos',
                                'Escribe un nombre y un identificador de paciente.')
            return
        self.accept()

    def datos(self):
        return {
            'nombre': self.nombre.text().strip(),
            'id': self.identificador.text().strip(),
            'nacimiento': self.fecha.date().toString('yyyyMMdd'),
            'sexo': self.sexo.currentData(),
            'estudio': self.descripcion.text().strip() or 'Práctica simulada de sutura Da Vinci',
        }


def nombre_dicom(nombre):
    """Nombre DICOM simple: APELLIDOS^NOMBRES, o texto libre sin acentos problemáticos."""
    import unicodedata
    normal = unicodedata.normalize('NFKD', nombre)
    texto = ''.join(c for c in normal if not unicodedata.combining(c))
    texto = ''.join(c for c in texto if c.isalnum() or c in ' ^-_').strip()
    return texto[:64] or 'PACIENTE^SIMULADO'



class SuturaGuiada:
    """Dibujos de sutura y agarre cinemático para demostración educativa."""
    def __init__(self, sim, puntas):
        self.sim = sim
        self.puntas = puntas
        self.tejido = sim.getObject('/Phantom_skin_respondable')
        self.aguja_raiz = sim.getObject('/Needle_40mm')
        self.aguja_punta = sim.getObject('/Needle_40mm/needle_tip')
        self.aguja_forma = sim.getObject('/Needle_40mm/needle_respondable')
        self.centro = np.array(sim.getObjectPosition(self.tejido, sim.handle_world), dtype=float)
        self.offset = np.array([0., 0., 0.008], dtype=float)
        self.paso = 0
        self.total = 4
        self.capas = []
        self.geometrias = []
        self.tolerancia = 0.025  # 25 mm para práctica guiada
        self.brazo_sujetando = None
        self.pose_relativa = None
        self.dibujar()

    def _capa(self, color, grosor):
        h = self.sim.addDrawingObject(self.sim.drawing_lines, grosor, 0.0, -1, 100, color)
        self.capas.append(h)
        return h

    def _linea(self, capa, a, b):
        self.sim.addDrawingObjectItem(capa, list(map(float, a)) + list(map(float, b)))

    def _segmento_solido(self, a, b, radio, color):
        """Cilindro real, visible por sensores de visión, no colisionable."""
        a = np.asarray(a, dtype=float)
        b = np.asarray(b, dtype=float)
        d = b - a
        largo = float(np.linalg.norm(d))
        if largo < 1e-6:
            return
        z = d / largo
        referencia = np.array([0., 0., 1.]) if abs(z[2]) < .90 else np.array([1., 0., 0.])
        x = np.cross(referencia, z)
        x /= np.linalg.norm(x)
        y = np.cross(z, x)
        centro = (a + b) * 0.5
        matriz = [float(x[0]), float(y[0]), float(z[0]), float(centro[0]),
                  float(x[1]), float(y[1]), float(z[1]), float(centro[1]),
                  float(x[2]), float(y[2]), float(z[2]), float(centro[2])]
        h = self.sim.createPureShape(2, 0,
                                     [radio * 2, radio * 2, largo], 0.01, None)
        self.sim.setObjectMatrix(h, matriz, self.sim.handle_world)
        self.sim.setShapeColor(h, None, self.sim.colorcomponent_ambient_diffuse, color)
        self.sim.setObjectAlias(h, 'GuiaSuturaVisual')
        self.geometrias.append(h)

    def borrar(self):
        for h in self.geometrias:
            try:
                self.sim.removeObject(h)
            except Exception:
                pass
        self.geometrias.clear()
        for h in self.capas:
            try:
                self.sim.removeDrawingObject(h)
            except Exception:
                pass
        self.capas.clear()

    def objetivo(self):
        x, y, z = self.centro + self.offset
        yy = y + (-0.015 + 0.01 * min(self.paso, 3))
        return np.array([x - 0.012, yy, z + 0.001])

    def distancia_objetivo(self):
        punta = np.array(self.sim.getObjectPosition(self.aguja_punta, self.sim.handle_world))
        return float(np.linalg.norm(punta - self.objetivo()))

    def dibujar(self):
        self.borrar()
        inc = self._capa([0.43, 0.05, 0.08], 4.0)
        hilo = self._capa([0.04, 0.14, 0.65], 3.0)
        guia = self._capa([0.95, 0.55, 0.06], 3.0)
        x, y, z = self.centro + self.offset
        self._segmento_solido((x, y - 0.024, z), (x, y + 0.024, z),
                             0.0015, [0.43, 0.05, 0.08])
        for i in range(self.total):
            yy = y + (-0.015 + 0.01 * i)
            puntos = [(x - 0.012, yy, z + 0.001),
                      (x - 0.006, yy, z + 0.005),
                      (x, yy, z + 0.007),
                      (x + 0.006, yy, z + 0.005),
                      (x + 0.012, yy, z + 0.001)]
            if i < self.paso:
                for a, b in zip(puntos, puntos[1:]):
                    self._segmento_solido(a, b, 0.0015, [0.04, 0.14, 0.85])
            elif i == self.paso:
                for xx in (x - 0.012, x + 0.012):
                    self._segmento_solido((xx, yy, z + 0.001),
                                         (xx, yy, z + 0.008), 0.0035,
                                         [1.0, 0.68, 0.02])

    def avanzar(self):
        if self.paso < self.total:
            self.paso += 1
            self.dibujar()

    def reiniciar(self):
        self.paso = 0
        self.dibujar()

    def ajustar(self, eje, cantidad):
        self.offset[eje] += cantidad
        self.dibujar()

    def sujetar(self, brazo):
        if self.brazo_sujetando:
            raise RuntimeError('Primero suelta la aguja del otro brazo.')
        if self.sim.getSimulationState() != self.sim.simulation_stopped:
            raise RuntimeError('Detén la simulación para sujetar la aguja.')
        # NO mover la aguja al brazo. El instrumento debe aproximarse primero.
        punta = np.asarray(self.sim.getObjectPosition(self.puntas[brazo], self.sim.handle_world))
        forma = np.asarray(self.sim.getObjectPosition(self.aguja_forma, self.sim.handle_world))
        distancia = float(np.linalg.norm(punta - forma))
        if distancia > 0.018:
            raise RuntimeError(f'El instrumento está a {distancia*1000:.1f} mm de la aguja. '
                               'Acércalo a menos de 18 mm antes de sujetarla.')
        self.pose_relativa = list(self.sim.getObjectPose(self.aguja_raiz, self.puntas[brazo]))
        self.brazo_sujetando = brazo

    def seguir_brazo(self, brazo):
        if self.brazo_sujetando == brazo and self.pose_relativa is not None:
            self.sim.setObjectPose(self.aguja_raiz, self.pose_relativa, self.puntas[brazo])

    def soltar(self):
        self.brazo_sujetando = None
        self.pose_relativa = None


class ConexionCoppelia:
    def __init__(self):
        self.client = RemoteAPIClient(host='localhost', port=23000)
        self.sim = self.client.require('sim')
        self.camaras = {
            'sutura': self.sim.getObject('/Camara_Sutura'),
            'general': self.sim.getObject('/Camara_General'),
            'medico': self.sim.getObject('/Camara_Medico'),
        }
        self.originales = {}
        self.estados = {}
        for nombre in ('sutura', 'general'):
            h = self.camaras[nombre]
            pose = list(self.sim.getObjectPose(h, self.sim.handle_world))
            # El eje Z del sensor es su dirección de observación.
            m = self.sim.getObjectMatrix(h, self.sim.handle_world)
            direccion = np.array([m[2], m[6], m[10]], dtype=float)
            direccion /= np.linalg.norm(direccion)
            distancia = 0.45 if nombre == 'sutura' else 2.0
            centro = np.array(pose[:3], dtype=float) + direccion * distancia
            self.originales[nombre] = pose
            self.estados[nombre] = {'centro': centro, 'distancia': distancia}
        print('Conectado a CoppeliaSim. Camaras:', self.camaras)

    def imagen(self, nombre):
        raw, resolucion = self.sim.getVisionSensorImg(self.camaras[nombre])
        w, h = [int(v) for v in resolucion]
        rgb = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)
        rgb = np.ascontiguousarray(np.flipud(rgb))
        return QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888).copy()

    def restaurar(self, nombre):
        h = self.camaras[nombre]
        self.sim.setObjectPose(h, self.originales[nombre], self.sim.handle_world)
        pose = self.originales[nombre]
        m = self.sim.getObjectMatrix(h, self.sim.handle_world)
        direccion = np.array([m[2], m[6], m[10]], dtype=float)
        direccion /= np.linalg.norm(direccion)
        distancia = 0.45 if nombre == 'sutura' else 2.0
        self.estados[nombre] = {
            'centro': np.array(pose[:3], dtype=float) + direccion * distancia,
            'distancia': distancia,
        }

    def mover(self, nombre, dx, dy, modo):
        h = self.camaras[nombre]
        pose = list(self.sim.getObjectPose(h, self.sim.handle_world))
        matriz = self.sim.getObjectMatrix(h, self.sim.handle_world)
        right = np.array([matriz[0], matriz[4], matriz[8]], dtype=float)
        up = np.array([matriz[1], matriz[5], matriz[9]], dtype=float)
        estado = self.estados[nombre]
        if modo == 'pan':
            desplazamiento = (-right * dx + up * dy) * estado['distancia'] * 0.0015
            pose[:3] = (np.array(pose[:3]) + desplazamiento).tolist()
            estado['centro'] += desplazamiento
            self.sim.setObjectPose(h, pose, self.sim.handle_world)
            return

        # Rotación orbital alrededor del centro de interés, usando
        # cuaterniones de CoppeliaSim para no depender de Euler.
        centro = estado['centro']
        pos = np.array(pose[:3], dtype=float)
        offset = pos - centro
        angulo_z = -dx * 0.006
        c, s = math.cos(angulo_z), math.sin(angulo_z)
        rot_z = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        offset = rot_z @ offset
        # El segundo giro usa el eje derecho de la cámara.
        angulo_x = -dy * 0.006
        eje = right / np.linalg.norm(right)
        c, s = math.cos(angulo_x), math.sin(angulo_x)
        rot_x = (np.eye(3) * c + (1-c) * np.outer(eje, eje) +
                 np.array([[0, -eje[2], eje[1]],
                           [eje[2], 0, -eje[0]],
                           [-eje[1], eje[0], 0]]) * s)
        offset = rot_x @ offset
        nueva_pos = centro + offset
        # Mantener apuntado al centro, preservando el sentido de la cámara.
        forward = centro - nueva_pos
        forward /= np.linalg.norm(forward)
        right_new = np.cross(np.array([0., 0., 1.]), forward)
        if np.linalg.norm(right_new) < 1e-5:
            right_new = right
        right_new /= np.linalg.norm(right_new)
        up_new = np.cross(forward, right_new)
        # setObjectMatrix admite matriz 3x4 por filas.
        mat = [right_new[0], up_new[0], forward[0], nueva_pos[0],
               right_new[1], up_new[1], forward[1], nueva_pos[1],
               right_new[2], up_new[2], forward[2], nueva_pos[2]]
        self.sim.setObjectMatrix(h, mat, self.sim.handle_world)

    def zoom(self, nombre, pasos):
        h = self.camaras[nombre]
        estado = self.estados[nombre]
        anterior = estado['distancia']
        nueva = float(np.clip(anterior * (0.88 ** pasos), 0.12, 6.0))
        pos = np.array(self.sim.getObjectPosition(h, self.sim.handle_world), dtype=float)
        vector = pos - estado['centro']
        if np.linalg.norm(vector) < 1e-6:
            return
        pos_nueva = estado['centro'] + vector / np.linalg.norm(vector) * nueva
        self.sim.setObjectPosition(h, pos_nueva.tolist(), self.sim.handle_world)
        estado['distancia'] = nueva




class ReceptorImagenes(QThread):
    fotograma = Signal(str, QImage)
    fallo = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.activo = True

    def run(self):
        # Cliente ZMQ exclusivo para este hilo: no compartir el cliente de movimiento.
        try:
            cliente = RemoteAPIClient(host='localhost', port=23000)
            sim = cliente.require('sim')
            camaras = {
                nombre: sim.getObject('/' + ruta)
                for nombre, ruta in [('sutura', 'Camara_Sutura'),
                                     ('general', 'Camara_General'),
                                     ('medico', 'Camara_Medico')]
            }
            # Los sensores normales no actualizan imágenes con la simulación detenida.
            # Activamos manejo explícito temporal para intentar renderizar en pausa.
            explicitos_originales = {}
            manejo_manual = False
            aviso_camara = False
            try:
                while self.activo:
                    detenido = sim.getSimulationState() == sim.simulation_stopped
                    if detenido and not manejo_manual:
                        try:
                            for nombre, handle in camaras.items():
                                explicitos_originales[nombre] = sim.getExplicitHandling(handle)
                                sim.setExplicitHandling(handle, 1)
                            manejo_manual = True
                        except Exception as exc:
                            if not aviso_camara:
                                self.fallo.emit('No se pudo activar renderizado con simulación detenida: ' + str(exc))
                                aviso_camara = True
                    elif not detenido and manejo_manual:
                        for nombre, handle in camaras.items():
                            try:
                                sim.setExplicitHandling(handle, explicitos_originales.get(nombre, 0))
                            except Exception:
                                pass
                        manejo_manual = False
                    for nombre, handle in camaras.items():
                        if not self.activo:
                            break
                        try:
                            if detenido and manejo_manual:
                                sim.handleVisionSensor(handle)
                            raw, resolucion = sim.getVisionSensorImg(handle)
                            w, h = map(int, resolucion)
                            rgb = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)
                            rgb = np.ascontiguousarray(np.flipud(rgb))
                            imagen = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888).copy()
                            self.fotograma.emit(nombre, imagen)
                        except Exception as exc:
                            if not aviso_camara:
                                self.fallo.emit('Problema con sensor de visión: ' + str(exc))
                                aviso_camara = True
                    self.msleep(65)
            finally:
                if manejo_manual:
                    for nombre, handle in camaras.items():
                        try:
                            sim.setExplicitHandling(handle, explicitos_originales.get(nombre, 0))
                        except Exception:
                            pass
        except Exception as exc:
            self.fallo.emit(str(exc))

    def detener(self):
        self.activo = False

class VisorCamara(QLabel):
    arrastre = Signal(float, float, str)
    rueda = Signal(float)

    def __init__(self, interactiva=False):
        super().__init__('Esperando imagen...')
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(200, 140)
        self.setStyleSheet('background: #05080e; color: white; border-radius: 7px;')
        self._imagen = None
        self._previo = None
        self.interactiva = interactiva
        if interactiva:
            self.setCursor(Qt.OpenHandCursor)

    def mostrar(self, imagen):
        self._imagen = imagen
        self._redibujar()

    def _redibujar(self):
        if self._imagen is not None:
            self.setPixmap(QPixmap.fromImage(self._imagen).scaled(
                self.size(), Qt.KeepAspectRatio, Qt.FastTransformation))

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._redibujar()

    def mousePressEvent(self, evento):
        if self.interactiva and evento.button() in (Qt.LeftButton, Qt.RightButton):
            self._previo = evento.position()
            self.setCursor(Qt.ClosedHandCursor)
        else:
            super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento):
        if self.interactiva and self._previo is not None:
            punto = evento.position()
            delta = punto - self._previo
            self._previo = punto
            modo = 'pan' if evento.buttons() & Qt.RightButton else 'orbita'
            self.arrastre.emit(delta.x(), delta.y(), modo)
        else:
            super().mouseMoveEvent(evento)

    def mouseReleaseEvent(self, evento):
        self._previo = None
        if self.interactiva:
            self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(evento)

    def wheelEvent(self, evento):
        if self.interactiva:
            self.rueda.emit(evento.angleDelta().y() / 120.0)
            evento.accept()
        else:
            super().wheelEvent(evento)


class PanelCamara(QFrame):
    def __init__(self, titulo, interactiva=False):
        super().__init__()
        self.setStyleSheet('QFrame {background:#151b27;border-radius:10px;}')
        layout = QVBoxLayout(self)
        cabecera = QLabel(titulo)
        cabecera.setStyleSheet('color:white;font-size:15px;font-weight:bold;')
        layout.addWidget(cabecera)
        self.visor = VisorCamara(interactiva)
        layout.addWidget(self.visor, 1)


class SimuladorDaVinci(QMainWindow):
    def __init__(self, datos_paciente):
        super().__init__()
        from pydicom.uid import generate_uid
        self.datos_paciente = datos_paciente
        self.uid_estudio = generate_uid()
        self.uid_serie = generate_uid()
        self.inicio_estudio = datetime.now()
        self.setWindowTitle('Simulador Quirúrgico Da Vinci')
        self.resize(1450, 850)
        self.conexion = ConexionCoppelia()
        self._ultimo_fotograma = None
        self._inicializar_brazos()
        self.sutura_guiada = SuturaGuiada(self.conexion.sim, self.puntas)
        self._configurar()
        self._crear_panel_brazos()
        self._crear_panel_sutura()
        self.receptor = ReceptorImagenes(self)
        self.receptor.fotograma.connect(self.recibir_fotograma)
        self.receptor.fallo.connect(self.error_imagen)
        self.receptor.start()
        self._iniciar_logitech()
        self._iniciar_start_ok()

    def _iniciar_logitech(self):
        """Lectura no bloqueante del F710 desde el hilo de la interfaz."""
        self.gamepad = None
        self.brazo_gamepad = 'PSM1'
        self._botones_previos = set()
        self._tick_logitech = 0
        self._home_inicio = None
        self._home_ejecutado = False
        self._start_previo = False
        self._foto_gatillo_previo = False
        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() == 0:
            self.estado.setText('Logitech: no detectado. Conecta el F710 y reinicia la app.')
            return
        self.gamepad = pygame.joystick.Joystick(0)
        self.gamepad.init()
        self.estado.setText(f'Control conectado: {self.gamepad.get_name()} | PSM1 activo')
        self.timer_logitech = QTimer(self)
        self.timer_logitech.timeout.connect(self._leer_logitech)
        self.timer_logitech.start(85)  # lectura más frecuente, velocidad moderada

    @staticmethod
    def _zona_muerta(valor):
        if abs(valor) <= 0.15:
            return 0.0
        return math.copysign((abs(valor) - 0.15) / 0.85, valor)

    def _mover_xyz_gamepad(self, brazo, desplazamiento):
        """Un paso IK XYZ amortiguado; nunca mueve la aguja por sí solo."""
        sim = self.conexion.sim
        if sim.getSimulationState() != sim.simulation_stopped:
            return
        handles = [self.joints[f'J{i}_{brazo}'] for i in (1, 2, 3)]
        inicio = self._posicion_punta(brazo)
        destino = inicio + desplazamiento
        # Hasta tres correcciones pequeñas para evitar saltos articulares.
        for _ in range(3):
            error = destino - self._posicion_punta(brazo)
            if np.linalg.norm(error) < 0.00025:
                break
            jac = self._jacobiano_xyz(brazo)
            dq = jac.T @ np.linalg.solve(jac @ jac.T + 0.025**2 * np.eye(3), error)
            dq[:2] = np.clip(dq[:2], -math.radians(1.1), math.radians(1.1))
            dq[2] = np.clip(dq[2], -0.0025, 0.0025)
            for h, delta in zip(handles, dq):
                q = sim.getJointPosition(h)
                sim.setJointPosition(h, self._limitar_joint(h, q + float(delta)))
        self.sutura_guiada.seguir_brazo(brazo)
        self._actualizar_brazo(brazo)
        avance = (self._posicion_punta(brazo) - inicio) * 1000
        self.estado.setText(f'F710 {brazo} | ΔX {avance[0]:+.1f} ΔY {avance[1]:+.1f} ΔZ {avance[2]:+.1f} mm')

    def _leer_logitech(self):
        if self.gamepad is None:
            return
        try:
            pygame.event.pump()
            botones = {i for i in range(self.gamepad.get_numbuttons())
                       if self.gamepad.get_button(i)}
            nuevos = botones - self._botones_previos
            self._botones_previos = botones

            # RT es el eje 5 en el F710 del usuario; -1 reposo, +1 pulsado.
            # Disparo por flanco: una sola fotografía por pulsación.
            rt = self.gamepad.get_axis(5) > 0.55
            foto_nueva = rt and not self._foto_gatillo_previo
            self._foto_gatillo_previo = rt

            # Mientras haya un aviso abierto no mover brazos ni activar comandos.
            if QApplication.activeModalWidget() is not None:
                return
            if foto_nueva:
                self.fotografia_orthanc()
                return

            if 4 in nuevos or 5 in nuevos:
                self.brazo_gamepad = 'PSM1' if 4 in nuevos else 'PSM2'
                self.selector_agarre.setCurrentText(self.brazo_gamepad)
                self.estado.setText(f'Logitech: {self.brazo_gamepad} seleccionado')
            if 3 in nuevos:  # Y: acercar el brazo (nunca teletransportar aguja)
                self.selector_agarre.setCurrentText(self.brazo_gamepad)
                self._acercar_brazo_aguja()
            if 0 in nuevos:  # A: sujetar, sin alternar a soltar
                if self.sutura_guiada.brazo_sujetando is None:
                    self.selector_agarre.setCurrentText(self.brazo_gamepad)
                    self._sujetar_aguja()
            if 1 in nuevos:  # B: soltar
                self._soltar_aguja()
            if 2 in nuevos:  # X: validar puntada
                self._validar_sutura()
            if 6 in nuevos:  # Back: reiniciar con confirmación
                respuesta = QMessageBox.question(
                    self, 'Reiniciar sutura',
                    '¿Reiniciar las puntadas? No se moverán los brazos ni la aguja.',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if respuesta == QMessageBox.Yes:
                    self._reiniciar_sutura()

            # HOME: mantener cruceta abajo 2 segundos. No mueve aguja.
            hat = self.gamepad.get_hat(0) if self.gamepad.get_numhats() else (0, 0)
            if hat == (0, -1):
                if self._home_inicio is None:
                    self._home_inicio = time.monotonic()
                    self._home_ejecutado = False
                elif not self._home_ejecutado and time.monotonic() - self._home_inicio >= 2.0:
                    self._home_ejecutado = True
                    if self.sutura_guiada.brazo_sujetando is not None:
                        QMessageBox.information(self, 'HOME',
                            'Primero suelta la aguja con B para regresar los brazos.')
                    else:
                        self._restaurar_brazos()
            else:
                self._home_inicio = None
                self._home_ejecutado = False

            if self.conexion.sim.getSimulationState() != self.conexion.sim.simulation_stopped:
                return
            # No mezclar desplazamiento manual con acciones de botón o HOME.
            if nuevos or hat == (0, -1):
                return
            x = self._zona_muerta(self.gamepad.get_axis(0))
            y = -self._zona_muerta(self.gamepad.get_axis(1))
            z = -self._zona_muerta(self.gamepad.get_axis(3))
            direccion = np.array([x, y, z], dtype=float)
            norma = float(np.linalg.norm(direccion))
            if norma < 0.05:
                return
            direccion /= max(1.0, norma)
            self._mover_xyz_gamepad(self.brazo_gamepad, direccion * 0.0025)
        except Exception as exc:
            self.timer_logitech.stop()
            self.estado.setText(f'Control Logitech detenido por error: {exc}')
            QMessageBox.warning(self, 'Logitech F710', str(exc))

    def _iniciar_start_ok(self):
        """Temporizador independiente: responde incluso durante QMessageBox.exec()."""
        self._start_ok_anterior = False
        self._timer_start_ok = QTimer(self)
        self._timer_start_ok.timeout.connect(self._comprobar_start_ok)
        self._timer_start_ok.start(45)

    def _comprobar_start_ok(self):
        if self.gamepad is None:
            return
        try:
            pygame.event.pump()
            indice = int(os.environ.get('F710_START_BUTTON', '7'))
            if indice >= self.gamepad.get_numbuttons():
                return
            presionado = bool(self.gamepad.get_button(indice))
            flanco = presionado and not self._start_ok_anterior
            self._start_ok_anterior = presionado
            if not flanco:
                return
            modal = QApplication.activeModalWidget()
            if isinstance(modal, QMessageBox):
                boton_ok = modal.button(QMessageBox.Ok)
                # Nunca aceptar confirmaciones de riesgo Yes/No con Start.
                if boton_ok is not None:
                    boton_ok.click()
        except Exception as exc:
            print(f'[F710 START] {exc}')

    def _configurar(self):
        central = QWidget()
        central.setStyleSheet('background:#1d1d1d;color:white;')
        self.setCentralWidget(central)
        vertical = QVBoxLayout(central)
        titulo = QLabel('SIMULADOR QUIRÚRGICO DA VINCI')
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet('font-size:25px;font-weight:bold;color:#4185c7;padding:12px;')
        vertical.addWidget(titulo)
        fila = QHBoxLayout()
        vertical.addLayout(fila, 1)
        izq = QVBoxLayout()
        fila.addLayout(izq, 3)
        self.sutura = PanelCamara('CÁMARA QUIRÚRGICA · SUTURA', True)
        izq.addWidget(self.sutura, 1)
        botones = QHBoxLayout()
        foto = QPushButton('📷  Tomar fotografía')
        foto.clicked.connect(self.fotografia_orthanc)
        restaurar_s = QPushButton('↻  Restaurar vista de sutura')
        restaurar_s.clicked.connect(lambda: self.restaurar('sutura'))
        botones.addWidget(foto)
        botones.addWidget(restaurar_s)
        izq.addLayout(botones)
        der = QVBoxLayout()
        fila.addLayout(der, 1)
        self.general = PanelCamara('VISTA GENERAL', True)
        der.addWidget(self.general, 1)
        restaurar_g = QPushButton('↻  Restaurar vista general')
        restaurar_g.clicked.connect(lambda: self.restaurar('general'))
        der.addWidget(restaurar_g)
        self.medico = PanelCamara('MÉDICO INSTRUCTOR')
        der.addWidget(self.medico, 1)
        instrucciones = QLabel('Bienvenido al simulador Da Vinci.\nPrepara los instrumentos para iniciar la sutura.')
        instrucciones.setWordWrap(True)
        instrucciones.setStyleSheet('background:#eaf2fa;color:#17365d;padding:13px;border-radius:7px;')
        der.addWidget(instrucciones)
        self.estado = QLabel('Estado: conectado a CoppeliaSim')
        vertical.addWidget(self.estado)
        self.sutura.visor.arrastre.connect(lambda dx, dy, modo: self.mover('sutura', dx, dy, modo))
        self.general.visor.arrastre.connect(lambda dx, dy, modo: self.mover('general', dx, dy, modo))
        self.sutura.visor.rueda.connect(lambda pasos: self.zoom('sutura', pasos))
        self.general.visor.rueda.connect(lambda pasos: self.zoom('general', pasos))

    def _inicializar_brazos(self):
        """Reutiliza la identificación de joints del controlador original."""
        sim = self.conexion.sim
        objetos = sim.getObjectsInTree(sim.handle_scene, sim.object_joint_type, 0)
        encontrados = {sim.getObjectAlias(h): h for h in objetos}
        self.joints = {}
        self.posiciones_originales = {}
        for brazo in ('PSM1', 'PSM2'):
            for i in range(1, 8):
                nombre = f'J{i}_{brazo}'
                if nombre not in encontrados:
                    raise RuntimeError(f'No se encontró {nombre} en la escena')
                h = encontrados[nombre]
                self.joints[nombre] = h
                self.posiciones_originales[nombre] = sim.getJointPosition(h)
        self.puntas = {
            'PSM1': sim.getObject('/TipOrient'),
            'PSM2': sim.getObject('/TipOrient2'),
        }

    def _crear_panel_brazos(self):
        dock = QDockWidget('CONTROL MANUAL · PSM1 / PSM2', self)
        dock.setObjectName('dock_brazos')
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        dock.setMinimumWidth(285)
        contenedor = QWidget()
        contenedor.setStyleSheet('background:#17202d;color:white;')
        layout = QVBoxLayout(contenedor)
        aviso = QLabel('Para mover articulaciones, DETÉN la simulación.\n'
                       'Las cámaras de visión pueden verse negras mientras está detenida.')
        aviso.setWordWrap(True)
        aviso.setStyleSheet('color:#ffd27f;')
        layout.addWidget(aviso)
        self.paneles_brazo = {}
        for brazo in ('PSM1', 'PSM2'):
            grupo = QGroupBox(brazo)
            columna = QVBoxLayout(grupo)
            selector = QComboBox()
            selector.addItems([f'J{i}' for i in range(1, 8)])
            posicion = QLabel('Posición: --')
            punta = QLabel('Punta: --')
            menos = QPushButton('◀ Mover -')
            mas = QPushButton('Mover + ▶')
            fila = QHBoxLayout()
            fila.addWidget(menos)
            fila.addWidget(mas)
            columna.addWidget(QLabel('Articulación:'))
            columna.addWidget(selector)
            columna.addWidget(posicion)
            columna.addWidget(punta)
            columna.addLayout(fila)
            layout.addWidget(grupo)
            self.paneles_brazo[brazo] = (selector, posicion, punta)
            selector.currentIndexChanged.connect(lambda _idx, b=brazo: self._actualizar_brazo(b))
            menos.clicked.connect(lambda _checked=False, b=brazo: self._mover_brazo(b, -1))
            mas.clicked.connect(lambda _checked=False, b=brazo: self._mover_brazo(b, 1))
        xyz_titulo = QLabel('MOVIMIENTO DE PUNTA · XYZ')
        xyz_titulo.setStyleSheet('font-weight:bold;color:#7ec8ff;padding-top:8px;')
        layout.addWidget(xyz_titulo)
        nota_xyz = QLabel('Experimental · 1 mm por clic · simulación detenida.\n'
                          'J1–J3; no controla todavía la orientación ni la pinza.')
        nota_xyz.setWordWrap(True)
        layout.addWidget(nota_xyz)
        for brazo in ('PSM1', 'PSM2'):
            grupo_xyz = QGroupBox(f'{brazo} · Mover punta')
            columna_xyz = QVBoxLayout(grupo_xyz)
            for eje, indice in [('X', 0), ('Y', 1), ('Z', 2)]:
                fila_xyz = QHBoxLayout()
                fila_xyz.addWidget(QLabel(eje))
                for signo, texto_boton in [(-1, '− 1 mm'), (1, '+ 1 mm')]:
                    boton_xyz = QPushButton(texto_boton)
                    boton_xyz.clicked.connect(
                        lambda _checked=False, b=brazo, i=indice, signo=signo:
                        self._mover_xyz(b, i, signo))
                    fila_xyz.addWidget(boton_xyz)
                columna_xyz.addLayout(fila_xyz)
            layout.addWidget(grupo_xyz)
        restaurar = QPushButton('↻ Restaurar ambos brazos')
        restaurar.clicked.connect(self._restaurar_brazos)
        layout.addWidget(restaurar)
        layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(contenedor)
        dock.setWidget(scroll)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        for brazo in ('PSM1', 'PSM2'):
            self._actualizar_brazo(brazo)

    def _verificar_brazos_detenidos(self):
        sim = self.conexion.sim
        if sim.getSimulationState() != sim.simulation_stopped:
            raise RuntimeError('Detén primero la simulación en CoppeliaSim para mover los joints.')

    def _actualizar_brazo(self, brazo):
        try:
            sim = self.conexion.sim
            selector, etiqueta, punta = self.paneles_brazo[brazo]
            nombre = f'J{selector.currentIndex() + 1}_{brazo}'
            h = self.joints[nombre]
            valor = sim.getJointPosition(h)
            tipo = sim.getJointType(h)
            if tipo == sim.joint_prismatic_subtype:
                etiqueta.setText(f'{nombre}: {valor:.4f} m')
            else:
                etiqueta.setText(f'{nombre}: {math.degrees(valor):.2f}°')
            xyz = sim.getObjectPosition(self.puntas[brazo], sim.handle_world)
            punta.setText(f'Punta X:{xyz[0]:.3f}  Y:{xyz[1]:.3f}  Z:{xyz[2]:.3f} m')
        except Exception as exc:
            self.estado.setText(f'Error de lectura de {brazo}: {exc}')

    def _mover_brazo(self, brazo, direccion):
        try:
            self._verificar_brazos_detenidos()
            sim = self.conexion.sim
            selector, _, _ = self.paneles_brazo[brazo]
            nombre = f'J{selector.currentIndex() + 1}_{brazo}'
            h = self.joints[nombre]
            tipo = sim.getJointType(h)
            paso = 0.005 if tipo == sim.joint_prismatic_subtype else math.radians(2)
            objetivo = sim.getJointPosition(h) + direccion * paso
            ciclica, intervalo = sim.getJointInterval(h)
            if not ciclica:
                minimo = intervalo[0]
                maximo = minimo + intervalo[1]
                objetivo = max(minimo, min(maximo, objetivo))
            sim.setJointPosition(h, objetivo)
            self.sutura_guiada.seguir_brazo(brazo)
            self._actualizar_brazo(brazo)
            self.estado.setText(f'{nombre} movido correctamente')
        except Exception as exc:
            QMessageBox.warning(self, 'Movimiento de brazo', str(exc))

    def _restaurar_brazos(self):
        try:
            self._verificar_brazos_detenidos()
            sim = self.conexion.sim
            for nombre, valor in self.posiciones_originales.items():
                sim.setJointPosition(self.joints[nombre], valor)
            for brazo in ('PSM1', 'PSM2'):
                self.sutura_guiada.seguir_brazo(brazo)
                self._actualizar_brazo(brazo)
            self.estado.setText('Posiciones de PSM1 y PSM2 restauradas')
        except Exception as exc:
            QMessageBox.warning(self, 'Restaurar brazos', str(exc))

    def _limitar_joint(self, handle, valor):
        sim = self.conexion.sim
        ciclica, intervalo = sim.getJointInterval(handle)
        if ciclica:
            return float(valor)
        minimo, rango = intervalo
        return float(np.clip(valor, minimo, minimo + rango))

    def _posicion_punta(self, brazo):
        sim = self.conexion.sim
        return np.asarray(sim.getObjectPosition(self.puntas[brazo], sim.handle_world), dtype=float)

    def _jacobiano_xyz(self, brazo):
        """Aproximación numérica local de la relación J1-J3 -> XYZ."""
        sim = self.conexion.sim
        handles = [self.joints[f'J{i}_{brazo}'] for i in (1, 2, 3)]
        base = self._posicion_punta(brazo)
        jac = np.zeros((3, 3), dtype=float)
        for indice, handle in enumerate(handles):
            q = sim.getJointPosition(handle)
            paso = 0.0005 if indice == 2 else math.radians(0.2)
            prueba = self._limitar_joint(handle, q + paso)
            if abs(prueba - q) < 1e-9:
                prueba = self._limitar_joint(handle, q - paso)
            if abs(prueba - q) < 1e-9:
                continue
            try:
                sim.setJointPosition(handle, prueba)
                jac[:, indice] = (self._posicion_punta(brazo) - base) / (prueba - q)
            finally:
                sim.setJointPosition(handle, q)
        return jac

    def _mover_xyz(self, brazo, eje, signo):
        try:
            self._verificar_brazos_detenidos()
            sim = self.conexion.sim
            inicio = self._posicion_punta(brazo)
            destino = inicio.copy()
            destino[eje] += signo * 0.001
            handles = [self.joints[f'J{i}_{brazo}'] for i in (1, 2, 3)]
            for _ in range(8):
                error = destino - self._posicion_punta(brazo)
                if np.linalg.norm(error) < 0.00015:
                    break
                jac = self._jacobiano_xyz(brazo)
                amortiguacion = 0.03
                dq = jac.T @ np.linalg.solve(
                    jac @ jac.T + amortiguacion ** 2 * np.eye(3), error)
                dq[:2] = np.clip(dq[:2], -math.radians(1), math.radians(1))
                dq[2] = np.clip(dq[2], -0.001, 0.001)
                if np.linalg.norm(dq) < 1e-9:
                    break
                for handle, cambio in zip(handles, dq):
                    actual = sim.getJointPosition(handle)
                    sim.setJointPosition(handle, self._limitar_joint(handle, actual + float(cambio)))
            self.sutura_guiada.seguir_brazo(brazo)
            real = (self._posicion_punta(brazo) - inicio) * 1000
            solicitado = np.zeros(3)
            solicitado[eje] = signo
            residual = np.linalg.norm(real - solicitado)
            self._actualizar_brazo(brazo)
            self.estado.setText(
                f'{brazo} · XYZ real (mm): X {real[0]:+.2f}, '
                f'Y {real[1]:+.2f}, Z {real[2]:+.2f} · Error {residual:.2f} mm')
        except Exception as exc:
            QMessageBox.warning(self, 'Movimiento XYZ', str(exc))


    def _crear_panel_sutura(self):
        dock = QDockWidget('PRÁCTICA DE SUTURA', self)
        dock.setObjectName('dock_sutura')
        dock.setMinimumWidth(260)
        panel = QWidget()
        panel.setStyleSheet('background:#17202d;color:white;')
        lay = QVBoxLayout(panel)
        self.etiqueta_progreso = QLabel('Puntadas: 0 / 4')
        self.etiqueta_progreso.setStyleSheet('font-size:18px;font-weight:bold;color:#80caff;')
        lay.addWidget(self.etiqueta_progreso)
        nota = QLabel('Sutura guiada: hilo visual, sin penetración física. '
                      'El brazo se aproxima a la aguja; solo puede sujetarla a menos de 18 mm. La aguja es estática y el agarre es simulado.')
        nota.setWordWrap(True)
        lay.addWidget(nota)
        lay.addWidget(QLabel('Brazo que sujetará la aguja:'))
        self.selector_agarre = QComboBox()
        self.selector_agarre.addItems(['PSM1', 'PSM2'])
        lay.addWidget(self.selector_agarre)
        acercar = QPushButton('Acercar brazo a la aguja (XYZ)')
        acercar.clicked.connect(self._acercar_brazo_aguja)
        lay.addWidget(acercar)
        agarrar = QPushButton('Sujetar aguja (si está cerca)')
        agarrar.clicked.connect(self._sujetar_aguja)
        soltar = QPushButton('Soltar aguja')
        soltar.clicked.connect(self._soltar_aguja)
        lay.addWidget(agarrar)
        lay.addWidget(soltar)
        self.etiqueta_agarre = QLabel('Aguja libre (estática)')
        lay.addWidget(self.etiqueta_agarre)
        avanzar = QPushButton('Completar puntada (demo)')
        avanzar.clicked.connect(self._avanzar_sutura)
        validar = QPushButton('Validar proximidad y completar')
        validar.clicked.connect(self._validar_sutura)
        reiniciar = QPushButton('Reiniciar sutura')
        reiniciar.clicked.connect(self._reiniciar_sutura)
        lay.addWidget(avanzar)
        lay.addWidget(validar)
        lay.addWidget(reiniciar)
        lay.addWidget(QLabel('Tolerancia: 25 mm alrededor del punto de entrada'))
        lay.addWidget(QLabel('Ajustar trazos al tejido:'))
        for titulo, eje, valor in [('X −5 mm', 0, -.005), ('X +5 mm', 0, .005),
                                  ('Y −5 mm', 1, -.005), ('Y +5 mm', 1, .005),
                                  ('Z −2 mm', 2, -.002), ('Z +2 mm', 2, .002)]:
            boton = QPushButton(titulo)
            boton.clicked.connect(lambda _checked=False, i=eje, v=valor: self._ajustar_sutura(i, v))
            lay.addWidget(boton)
        lay.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        dock.setWidget(scroll)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    def _acercar_brazo_aguja(self):
        """Aproximación incremental usando J1-J3, sin alterar la aguja."""
        try:
            self._verificar_brazos_detenidos()
            brazo = self.selector_agarre.currentText()
            if self.sutura_guiada.brazo_sujetando is not None:
                raise RuntimeError('Suelta la aguja antes de aproximar el brazo.')
            sim = self.conexion.sim
            objetivo = np.asarray(sim.getObjectPosition(
                self.sutura_guiada.aguja_forma, sim.handle_world), dtype=float)
            handles = [self.joints[f'J{i}_{brazo}'] for i in (1, 2, 3)]
            inicial = float(np.linalg.norm(objetivo - self._posicion_punta(brazo)))
            if inicial > 0.25:
                raise RuntimeError(f'Aguja demasiado lejos ({inicial*1000:.0f} mm). '
                                   'Aproxima el brazo manualmente primero.')
            anterior = inicial
            estancado = 0
            for _ in range(55):
                error = objetivo - self._posicion_punta(brazo)
                distancia = float(np.linalg.norm(error))
                if distancia <= 0.012:
                    break
                jac = self._jacobiano_xyz(brazo)
                # Paso cartesiano limitado a 4 mm para evitar saltos grandes.
                error = error * min(1.0, 0.004 / max(distancia, 1e-9))
                dq = jac.T @ np.linalg.solve(jac @ jac.T + .02**2 * np.eye(3), error)
                dq[:2] = np.clip(dq[:2], -math.radians(2), math.radians(2))
                dq[2] = np.clip(dq[2], -.004, .004)
                for h, delta in zip(handles, dq):
                    q = sim.getJointPosition(h)
                    sim.setJointPosition(h, self._limitar_joint(h, q + float(delta)))
                nuevo = float(np.linalg.norm(objetivo - self._posicion_punta(brazo)))
                if nuevo >= anterior - 0.0001:
                    estancado += 1
                else:
                    estancado = 0
                anterior = nuevo
                if estancado >= 7:
                    break
            final = float(np.linalg.norm(objetivo - self._posicion_punta(brazo)))
            self._actualizar_brazo(brazo)
            self.estado.setText(f'{brazo}: distancia a aguja {final*1000:.1f} mm '
                                f'(antes {inicial*1000:.1f} mm)')
            if final > 0.018:
                QMessageBox.information(self, 'Aproximación parcial',
                    f'El brazo se acercó hasta {final*1000:.1f} mm. '
                    'La posición podría no ser alcanzable solo con J1-J3. '
                    'Puedes ajustar las articulaciones manualmente.')
        except Exception as exc:
            QMessageBox.warning(self, 'Acercar brazo', str(exc))

    def _sujetar_aguja(self):
        try:
            brazo = self.selector_agarre.currentText()
            self.sutura_guiada.sujetar(brazo)
            self.etiqueta_agarre.setText(f'Aguja sujeta por {brazo} (agarre simulado)')
            self.estado.setText(f'Aguja sujeta por {brazo}; mueve el brazo con J1/J2 o XYZ (simulación detenida)')
        except Exception as exc:
            QMessageBox.warning(self, 'Agarre', str(exc))

    def _soltar_aguja(self):
        self.sutura_guiada.soltar()
        self.etiqueta_agarre.setText('Aguja libre (estática)')
        self.estado.setText('Aguja soltada')

    def _refrescar_sutura(self):
        n = self.sutura_guiada.paso
        self.etiqueta_progreso.setText(f'Puntadas: {n} / 4')
        self.estado.setText('Sutura visual completada' if n == 4 else f'Puntadas completadas: {n}/4')

    def _avanzar_sutura(self):
        self.sutura_guiada.avanzar()
        self._refrescar_sutura()

    def _validar_sutura(self):
        try:
            if self.sutura_guiada.paso >= 4:
                self.estado.setText('Sutura visual completada')
                return
            d = self.sutura_guiada.distancia_objetivo()
            if d <= self.sutura_guiada.tolerancia:
                self.sutura_guiada.avanzar()
                self._refrescar_sutura()
            else:
                QMessageBox.information(self, 'Objetivo pendiente',
                    f'La punta de la aguja está a {d*1000:.1f} mm del punto de entrada.\n'
                    f'Acércala a menos de {self.sutura_guiada.tolerancia*1000:.0f} mm o utiliza Completar puntada (demo).')
        except Exception as exc:
            QMessageBox.warning(self, 'Validación', str(exc))

    def _reiniciar_sutura(self):
        self.sutura_guiada.reiniciar()
        self._refrescar_sutura()

    def _ajustar_sutura(self, eje, valor):
        try:
            self.sutura_guiada.ajustar(eje, valor)
            self.estado.setText('Posición de los trazos de sutura ajustada')
        except Exception as exc:
            QMessageBox.warning(self, 'Ajustar sutura', str(exc))

    def recibir_fotograma(self, nombre, imagen):
        panel = {'sutura': self.sutura, 'general': self.general,
                 'medico': self.medico}[nombre]
        panel.visor.mostrar(imagen)
        if nombre == 'sutura':
            self._ultimo_fotograma = imagen

    def error_imagen(self, mensaje):
        self.estado.setText(f'Error de imágenes: {mensaje}')
        print('Error de recepción:', mensaje)

    def closeEvent(self, evento):
        if hasattr(self, 'timer_logitech'):
            self.timer_logitech.stop()
        if self.gamepad is not None:
            self.gamepad.quit()
        pygame.quit()
        self.sutura_guiada.borrar()
        self.receptor.detener()
        # El hilo podría estar esperando una respuesta de CoppeliaSim.
        if not self.receptor.wait(2000):
            self.receptor.setParent(None)
        super().closeEvent(evento)

    def mover(self, nombre, dx, dy, modo):
        try:
            self.conexion.mover(nombre, dx, dy, modo)
        except Exception as e:
            self.estado.setText(f'Error al mover cámara: {e}')
            print('Error de movimiento:', e)

    def zoom(self, nombre, pasos):
        try:
            self.conexion.zoom(nombre, pasos)
        except Exception as e:
            self.estado.setText(f'Error al hacer zoom: {e}')

    def restaurar(self, nombre):
        try:
            self.conexion.restaurar(nombre)
            self.estado.setText(f'Vista {nombre} restaurada')
        except Exception as e:
            self.estado.setText(f'Error al restaurar: {e}')

    def fotografia_orthanc(self):
        """Captura Camara_Sutura y crea DICOM Secondary Capture para Orthanc."""
        try:
            from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
            from pydicom.uid import (ExplicitVRLittleEndian, SecondaryCaptureImageStorage,
                                     generate_uid)
        except ImportError:
            QMessageBox.warning(self, 'Falta dependencia',
                'Instala pydicom: .\\.venv\\Scripts\\python.exe -m pip install pydicom')
            return
        try:
            imagen = self._ultimo_fotograma
            if imagen is None or imagen.isNull():
                raise RuntimeError('No hay imagen de Camara_Sutura. Comprueba las cámaras.')
            carpeta = (Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent) / 'capturas'
            carpeta.mkdir(exist_ok=True)
            marca = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            archivo_png = carpeta / f'sutura_{marca}.png'
            archivo_dcm = carpeta / f'sutura_{marca}.dcm'
            rgb = imagen.convertToFormat(QImage.Format_RGB888)
            ancho, alto = rgb.width(), rgb.height()
            raw = bytes(rgb.constBits())
            matriz = np.frombuffer(raw, dtype=np.uint8).reshape(alto, rgb.bytesPerLine())[:, :ancho*3]
            pixeles = np.ascontiguousarray(matriz).tobytes()
            if not rgb.save(str(archivo_png)):
                raise RuntimeError('No se pudo guardar la fotografía PNG')
            meta = FileMetaDataset()
            meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
            meta.MediaStorageSOPInstanceUID = generate_uid()
            meta.TransferSyntaxUID = ExplicitVRLittleEndian
            meta.ImplementationClassUID = generate_uid()
            ds = FileDataset(str(archivo_dcm), {}, file_meta=meta, preamble=b'\0'*128)
            ds.SOPClassUID = meta.MediaStorageSOPClassUID
            ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
            ds.StudyInstanceUID = self.uid_estudio
            ds.SeriesInstanceUID = self.uid_serie
            ds.Modality = 'OT'
            ds.PatientName = nombre_dicom(self.datos_paciente['nombre'])
            ds.PatientID = self.datos_paciente['id'][:64]
            ds.PatientBirthDate = self.datos_paciente['nacimiento']
            ds.PatientSex = self.datos_paciente['sexo']
            ds.StudyDescription = self.datos_paciente['estudio'][:64]
            ds.AccessionNumber = ''
            ds.StudyID = 'SIM001'
            ds.SeriesDescription = 'Camara de sutura - simulacion'
            ds.ImageType = ['DERIVED', 'SECONDARY']
            ds.ConversionType = 'WSD'
            ds.ContentDate = datetime.now().strftime('%Y%m%d')
            ds.ContentTime = datetime.now().strftime('%H%M%S.%f')
            ds.StudyDate = self.inicio_estudio.strftime('%Y%m%d')
            ds.StudyTime = self.inicio_estudio.strftime('%H%M%S.%f')
            ds.Rows = alto
            ds.Columns = ancho
            ds.SamplesPerPixel = 3
            ds.PhotometricInterpretation = 'RGB'
            ds.PlanarConfiguration = 0
            ds.BitsAllocated = 8
            ds.BitsStored = 8
            ds.HighBit = 7
            ds.PixelRepresentation = 0
            ds.PixelData = pixeles
            ds.save_as(str(archivo_dcm), enforce_file_format=True)
            url = os.environ.get('ORTHANC_URL', 'http://127.0.0.1:8042').rstrip('/')
            if not url.startswith(('http://', 'https://')):
                raise RuntimeError('ORTHANC_URL debe comenzar con http:// o https://')
            req = urllib.request.Request(url + '/instances', data=archivo_dcm.read_bytes(),
                headers={'Content-Type': 'application/dicom'}, method='POST')
            usuario = os.environ.get('ORTHANC_USER', '')
            clave = os.environ.get('ORTHANC_PASSWORD', '')
            if usuario:
                token = base64.b64encode(f'{usuario}:{clave}'.encode()).decode()
                req.add_header('Authorization', 'Basic ' + token)
            try:
                with urllib.request.urlopen(req, timeout=6) as respuesta:
                    resultado = json.loads(respuesta.read().decode('utf-8'))
                self.estado.setText('Fotografía DICOM enviada a Orthanc correctamente')
                QMessageBox.information(self, 'Captura enviada',
                    f'Fotografía y DICOM guardados en:\n{carpeta}\n\n'
                    f'Orthanc confirmó recepción. ID: {resultado.get("ID", "sin ID")}')
            except Exception as exc:
                self.estado.setText('Captura guardada; envío a Orthanc pendiente')
                QMessageBox.warning(self, 'DICOM guardado, Orthanc no disponible',
                    f'Se guardaron PNG y DICOM en:\n{carpeta}\n\n'
                    f'No se confirmó el envío a {url}.\nDetalle: {exc}')
        except Exception as exc:
            QMessageBox.warning(self, 'Error de captura DICOM', str(exc))

    def fotografia(self):
        try:
            imagen = self._ultimo_fotograma
            if imagen is None:
                raise RuntimeError('Todavía no se ha recibido una imagen')
            carpeta = (Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent) / 'capturas'
            carpeta.mkdir(exist_ok=True)
            archivo = carpeta / f'sutura_{datetime.now():%Y%m%d_%H%M%S}.png'
            if not imagen.save(str(archivo)):
                raise RuntimeError('No se pudo guardar la imagen')
            QMessageBox.information(self, 'Fotografía guardada', str(archivo))
        except Exception as e:
            QMessageBox.warning(self, 'Error de captura', str(e))


if __name__ == '__main__':
    try:
        import pydicom
    except ImportError:
        print('Falta pydicom. Instala con: .\\.venv\\Scripts\\python.exe -m pip install pydicom')
        sys.exit(1)
    app = QApplication(sys.argv)
    dialogo = DialogoPaciente()
    if dialogo.exec() != QDialog.Accepted:
        sys.exit(0)
    ventana = SimuladorDaVinci(dialogo.datos())
    ventana.show()
    sys.exit(app.exec())

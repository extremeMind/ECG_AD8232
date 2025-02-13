from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QComboBox, QLineEdit, QPushButton, 
                            QLabel)
from PyQt6.QtCore import Qt, QTimer, QDateTime
import sys
import serial
import numpy as np
from pyqtgraph import PlotWidget, InfiniteLine
import serial.tools.list_ports
from send_mail import send_mail
from tensorflow.keras.models import load_model
import threading
import re

# Dicionário para mapear os índices das classes para descrições
class_descriptions = {
    0: 'Normal',
    1: 'Extrassístoles Ventriculares',
    2: 'Extrassístoles Auriculares',
    3: 'Bloqueios AV',
    4: 'Ritmos de Escape Juncionais e Ventriculares',
    5: 'Taquicardia Ventricular',
    6: 'Flutter Auricular e Fibrilação',
    7: 'Bloqueios AV de Segundo/Terceiro Grau'
}

# Parâmetros de pré-processamento
WINDOW_SIZE = 10  # Tamanho da janela de dados
MIN_VALUE = 0     # Valor mínimo esperado nos dados (ajustar conforme necessário)
MAX_VALUE = 65535  # Valor máximo para uint16, ajuste conforme necessário

# Carregar o modelo LSTM pré-treinado
model = load_model('./model_lstm.h5')

class ECGApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Eletrocardiograma")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: black;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QComboBox, QLineEdit {
                background-color: black;
                color: white;
                border: 1px solid #00a6ff;
                border-radius: 0px;
                padding: 5px;
                min-width: 150px;
                height: 25px;
            }
            QPushButton {
                background-color: black;
                color: white;
                border: 1px solid white;
                border-radius: 0px;
                padding: 5px 15px;
                min-width: 80px;
            }
            QPushButton:checked {
                background-color: #00a6ff;
                border: 1px solid #00a6ff;
            }
        """)

        # Widget principal
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Área superior
        top_layout = QHBoxLayout()

        # Porta COM e Baud Rate
        input_layout = QHBoxLayout()

        # Porta COM
        port_layout = QVBoxLayout()
        port_label = QLabel("Porta COM:")
        self.port_combo = QComboBox()
        self.port_combo.setFixedWidth(80)
        self.update_ports()
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_combo)

        # Baud Rate
        baud_layout = QVBoxLayout()
        baud_label = QLabel("Baud Rate:")
        self.baud_input = QLineEdit()
        self.baud_input.setFixedWidth(80)
        self.baud_input.setText("115200")
        baud_layout.addWidget(baud_label)
        baud_layout.addWidget(self.baud_input)

        # Adiciona os layouts de Porta COM e Baud Rate ao layout de entrada
        input_layout.addLayout(port_layout)
        input_layout.addLayout(baud_layout)

        # Adiciona o layout de entrada ao layout superior
        top_layout.addLayout(input_layout)
        top_layout.addStretch()
    
        # Batimentos por minuto
        self.bpm_label = QLabel("0 bpm")
        self.bpm_label.setStyleSheet("""
            QLabel {
                width: 50px;
                height: 10px;
                color: white;
                font-size: 14px;
            }
        """)
        top_layout.addWidget(self.bpm_label)
        
        # Gráfico ECG
        self.plot_widget = PlotWidget()
        self.plot_widget.setBackground('black')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setYRange(0, 3000)  # Definir o intervalo do eixo y
        self.curve = self.plot_widget.plot(pen='g')
        self.second_curve = self.plot_widget.plot(pen='w')  # Segunda linha com cor diferente

        # Linha vermelha para o threshold
        #self.threshold_line = InfiniteLine(pos=1900, angle=0, pen='r')
        #self.plot_widget.addItem(self.threshold_line)

        # Botão para alternar a segunda linha
        self.toggle_second_line_button = QPushButton("Ativar ECG RAW")
        self.toggle_second_line_button.setCheckable(True)
        self.toggle_second_line_button.clicked.connect(self.toggle_second_line)
        top_layout.addWidget(self.toggle_second_line_button)

        # Área inferior
        bottom_layout = QHBoxLayout()

        # Diagnóstico (lado esquerdo)
        ia_layout = QVBoxLayout()
        ia_label = QLabel("Diagnóstico:")
        ia_label_atencao = QLabel("*Alerta: Este recurso é experimental e não substitui a avaliação de um profissional de saúde.")
        self.ia_button = QPushButton("Desativado")
        self.ia_button.setFixedWidth(80)
        self.ia_button.setCheckable(True)
        self.ia_button.clicked.connect(self.toggle_ia)
        ia_layout.addWidget(ia_label)
        ia_layout.addWidget(self.ia_button)
        ia_layout.addWidget(ia_label_atencao)

        # Email (lado direito)
        email_layout = QVBoxLayout()
        email_label = QLabel("Email:")
        self.email_input = QLineEdit()
        self.email_input.setFixedWidth(500)
        self.submit_button = QPushButton("Começar")
        self.submit_button.clicked.connect(self.start_monitoring)
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        email_layout.addWidget(self.submit_button)

        # Área de diagnóstico
        diagnostic_result_layout = QVBoxLayout()
        diagnostic_label = QLabel("Resultado do Diagnóstico:")
        diagnostic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.diagnostic_text = QLabel("Nenhuma anomalia detectada")
        self.diagnostic_text.setFixedSize(270, 30)  # Largura e altura fixas
        self.diagnostic_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.diagnostic_text.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                border: 1px solid #00a6ff;
                border-radius: 5px;
                padding: 5px;
                background-color: black;
                margin: 0 auto;
            }
        """)
        
        diagnostic_result_layout.addWidget(diagnostic_label)
        diagnostic_result_layout.addWidget(self.diagnostic_text, alignment=Qt.AlignmentFlag.AlignCenter)

        # Crie um layout horizontal para conter ia_layout e email_layout
        horizontal_layout = QHBoxLayout()
        horizontal_layout.addLayout(ia_layout)
        horizontal_layout.addStretch()  # Espaço flexível antes
        horizontal_layout.addLayout(diagnostic_result_layout)
        horizontal_layout.addStretch()  # Espaço flexível antes
        horizontal_layout.addLayout(email_layout)

        # Adiciona os layouts ao layout inferior
        bottom_layout.addLayout(horizontal_layout)

        # Adiciona todos os layouts ao layout principal
        layout.addLayout(top_layout)
        layout.addWidget(self.plot_widget)
        layout.addLayout(bottom_layout)
        
        # Inicialização
        self.data = np.zeros(3000)  # Aumentar o tamanho do array de dados para mostrar mais ciclos
        self.second_line_data = np.zeros(3000)  # Aumentar o tamanho do array de dados da segunda linha
        self.plotted_data = []  # Lista para armazenar dados plotados
        self.show_second_line = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.serial = None
        self.data_buffer = np.array([])  # Buffer para coletar dados até atingir WINDOW_SIZE
        self.diagnosis = None
        self.bpm = 0
        self.r_peaks = []  # Lista para armazenar timestamps dos picos R
        self.rr_intervals = []  # Lista para armazenar intervalos R-R
        self.threshold = 1940  # Ajuste inicial do threshold (em amplitude)
        self.belowThreshold = True
        self.email_input.textChanged.connect(self.check_email_input)
        self.last_valid_value = 0.0
        self.last_valid_value2 = 0.0
        self.ia_thread = None  # Thread para processamento de IA
        self.beat_old = 0
        self.beatIndex = 0
        self.beats = np.zeros(500)  # Array para armazenar os batimentos

    def check_email_input(self):
        """Verifica se o campo de email está preenchido."""
        if self.email_input.text().strip():
            self.submit_button.setEnabled(True)
        else:
            self.submit_button.setEnabled(False)

    def calculateBPM(self):
        """Calcula BPM com base nos intervalos R-R."""
        if len(self.rr_intervals) > 0:
            avg_rr_interval = np.mean(self.rr_intervals)
            self.bpm = 60000 / avg_rr_interval  # Converter ms para BPM
            self.bpm_label.setText(f"{int(self.bpm)} bpm")

    def update_ports(self):
        """Atualiza a lista de portas COM disponíveis."""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo.clear()
        self.port_combo.addItems(ports)

    def toggle_ia(self):
        """Ativa ou desativa o botão de IA."""
        self.ia_button.setText("Ativado" if self.ia_button.isChecked() else "Desativado")

    def toggle_second_line(self):
        """Ativa ou desativa a segunda linha do gráfico."""
        self.show_second_line = not self.show_second_line

    def start_monitoring(self):
        """Inicia a monitorização do ECG."""
        if not self.email_input.text().strip():
            return
        if not self.serial or not self.serial.is_open:
            try:
                port = self.port_combo.currentText()
                baud = int(self.baud_input.text())
                self.serial = serial.Serial(port, baud)
                self.timer.start(2)  # Verificar se com 1 não fica muito rápido
                self.submit_button.setText("Parar")
                self.port_combo.setEnabled(False)
                self.baud_input.setEnabled(False)
                self.email_input.setEnabled(False)
            except Exception as e:
                print(f"Erro ao conectar: {e}")
        else:
            self.stop_monitoring()

    def stop_monitoring(self):
        """Para a monitorização do ECG."""
        if self.serial and self.serial.is_open:
            self.timer.stop()
            self.serial.close()
            self.serial = None
            self.submit_button.setText("Continuar")
            self.port_combo.setEnabled(True)
            self.baud_input.setEnabled(True)
            self.email_input.setEnabled(True)

    def detect_r_peak(self, value, timestamp):
        """Deteta pico R e calcula intervalo R-R."""
        if value > self.threshold and self.belowThreshold:
            #self.calculate_average_bpm()  # Atualiza BPM com base nos últimos 500 batimentos
            self.belowThreshold = False
            self.r_peaks.append(timestamp)
            if len(self.r_peaks) > 1:
                rr_interval = self.r_peaks[-1] - self.r_peaks[-2]
                self.rr_intervals.append(rr_interval)
                if len(self.rr_intervals) >= WINDOW_SIZE:
                    self.rr_intervals = self.rr_intervals[-WINDOW_SIZE:]
                    self.calculateBPM()  # Atualiza BPM com base nos intervalos R-R
                    #self.calculate_average_bpm() 
                # Processamento IA
                    if self.ia_button.isChecked():
                        if self.ia_thread is None or not self.ia_thread.is_alive():
                            self.ia_thread = threading.Thread(target=self.process_rr_intervals)
                            self.ia_thread.start()
        elif value < self.threshold:
            self.belowThreshold = True

    def process_rr_intervals(self):
        """Processa intervalos R-R com o modelo."""
        rr_data = np.array(self.rr_intervals)
        rr_data = rr_data.reshape(1, len(rr_data), 1)
        prediction = model.predict(rr_data)
        predicted_class_index = np.argmax(prediction)
        self.diagnosis = class_descriptions[predicted_class_index]
        self.diagnostic_text.setText(self.diagnosis)
        if self.diagnosis != "Normal":
            recipient = self.email_input.text()
            subject = "Alerta de Doença Detectada"
            body = f"A IA detectou uma possível doença no eletrocardiograma. Diagnóstico: {self.diagnosis}"
            send_mail(recipient, subject, body)
            # Desativar IA após enviar email
            self.ia_button.setChecked(False)
            self.ia_button.setText("Desativado")
            self.ia_thread = None  # Desassociar a thread de IA após enviar o email
            
    def calculate_average_bpm(self):
        """Calcula a média de BPM com base nos últimos 500 batimentos."""
        beat_new = QDateTime.currentMSecsSinceEpoch()  # Obtém o milissegundo atual
        diff = beat_new - self.beat_old  # Encontra o tempo entre os dois últimos batimentos
        currentBPM = 60000 / diff  # Converte para batimentos por minuto
        self.beats[self.beatIndex] = currentBPM  # Armazena no array para calcular a média
        total = np.sum(self.beats)  # Soma todos os valores do array
        self.bpm = int(total / 500)  # Calcula a média
        self.beat_old = beat_new
        self.beatIndex = (self.beatIndex + 1) % 500  # Cicla pelo array em vez de usar uma fila FIFO
        self.bpm_label.setText(f"{int(self.bpm)} bpm")       

    def update_plot(self):
        """Atualiza o gráfico com novos dados."""
        while self.serial and self.serial.is_open and self.serial.in_waiting:
            try:
                line = self.serial.readline().decode().strip()
                
                # Verifica se a linha contém dois valores entre <>
                matches = re.findall(r'<(\d+)>', line)
                if len(matches) != 2:
                    continue  # Se a linha não estiver no formato correto, continue para a próxima leitura

                try:
                    value1 = float(int(matches[0]) / 1000)
                    value2 = int(matches[1])
                    
                    # Aplica um offset ao value2
                    offset = -1500
                    value2 += offset
                   
                    if 0 <= value1 <= 4095:
                        self.last_valid_value = value1  # Armazena o último valor válido
                    else:
                        value1 = self.last_valid_value
                    
                    if 0 <= value2 <= 4095:
                        self.last_valid_value2 = value2  # Armazena o último valor válido
                    else:
                        value2 = self.last_valid_value2
                except ValueError:
                    print(f"Erro ao converter para float: {line}")
                    value1 = self.last_valid_value  # Usa o último valor válido
                    value2 = self.last_valid_value2  # Usa o último valor válido

                self.data = np.roll(self.data, -1)
                self.data[-1] = value1
                self.curve.setData(self.data)
                self.plotted_data.append(value1)  # Armazena os dados plotados

                # Atualiza a segunda linha se estiver ativada
                if self.show_second_line:
                    self.second_line_data = np.roll(self.second_line_data, -1)
                    self.second_line_data[-1] = value2
                    self.second_curve.setData(self.second_line_data)
                else:
                    self.second_curve.clear()

                timestamp = QDateTime.currentMSecsSinceEpoch()
                self.detect_r_peak(value1, timestamp)

                

                
                    
            except Exception as e:
                print(f"Erro na atualização do gráfico: {e}")

    

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ECGApp()
    window.show()
    sys.exit(app.exec())

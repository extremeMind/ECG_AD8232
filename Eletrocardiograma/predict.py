import numpy as np
import scipy.io as sio
from tensorflow.keras.models import load_model


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
MIN_VALUE = 0     # Valor mínimo esperado nos dados (ajustar conforme seus dados)
MAX_VALUE = 65535  # Valor máximo para uint16, ajuste conforme necessário

# Carregar o modelo LSTM pré-treinado
model = load_model('./model_lstm.h5')

def normalize(data, min_val, max_val):
    """Normaliza os dados para o intervalo [0, 1]."""
    return (data - min_val) / (max_val - min_val)

def preprocess(data):
    """Aplica a normalização e reestrutura os dados para o formato necessário."""
    normalized_data = normalize(data, MIN_VALUE, MAX_VALUE)
    # Reshape data para (samples, time steps, features)
    reshaped_data = normalized_data.reshape(1, len(normalized_data), 1)
    return reshaped_data

def predict(data):
    """Realiza uma predição com o modelo."""
    processed_data = preprocess(data)
    prediction = model.predict(processed_data)
    predicted_class_index = np.argmax(prediction)
    return class_descriptions[predicted_class_index]


# Carregar dados do sensor
data_path = './sensorData.mat'
mat_contents = sio.loadmat(data_path)
data = mat_contents['dataStore'].flatten()  # Ajustar flatten() se estrutura for diferente

# Simular leitura em tempo real
for start in range(0, len(data) - WINDOW_SIZE, WINDOW_SIZE):
    window = data[start:start + WINDOW_SIZE]
    output = predict(window)
    #print("Janela de dados:", window)
    #print("Predição:", output)
    
    print("Descrição da classe predita:", output)
    # Aqui você pode decidir o que fazer com a saída

import tkinter as tk  # Importa a biblioteca Tkinter para a interface gráfica
import requests  # Importa a biblioteca requests para fazer requisições HTTP (comunicar com o Blynk e Telegram)
import json  # Importa a biblioteca json para lidar com dados no formato JSON (vindos do Blynk)
import numpy as np  # Importa a biblioteca NumPy para cálculos numéricos (usado na regressão linear)
from sklearn.linear_model import LinearRegression  # Importa o modelo de Regressão Linear do scikit-learn
from sklearn.metrics import mean_squared_error  # Importa a função para calcular o erro quadrático médio (RMSE)
import time  # Importa a biblioteca time para trabalhar com tempo (controlar o envio de alertas)

# --- Configurações do Sistema ---

# Configurações do Blynk
blynk_token = "aEMj2BSxHnip3ZZyZqVnBzrAlQsCEoBY"  # token do Blynk
blynk_server = "blynk.cloud"  # Endereço do servidor Blynk

# Configurações do Telegram
telegram_bot_token = "7230891112:AAEcrh13eynokGGHYzxmJu75oe8iwi2V5BA"
telegram_chat_id = "1099425208"  # chatId

# --- Limites de Alerta (Ajustados para Sobral-CE) ---

# Temperatura
temp_ideal = 30  # Temperatura ideal (confortável) em graus Celsius
temp_atencao = 35  # Temperatura que precisa de atenção em graus Celsius
temp_critico = 40  # Temperatura crítica (risco para os componentes) em graus Celsius

# Umidade
hum_ideal = 60  # Umidade ideal em porcentagem
hum_atencao = 70  # Umidade que precisa de atenção em porcentagem
hum_critico = 80  # Umidade crítica em porcentagem

# Nível de Enchimento da Lixeira
trash_full_threshold = 100  # Limite (em porcentagem) para considerar a lixeira cheia

# --- Parâmetros do Modelo de Previsão ---
window_size = 10  # Tamanho da janela deslizante para o treinamento incremental (número de leituras recentes usadas)
temp_increase_threshold = 0.5  # Limiar (em graus Celsius) para identificar um aumento constante na temperatura
hum_increase_threshold = 0.5  # Limiar (em porcentagem) para identificar um aumento constante na umidade

# --- Controle de Alertas ---
last_trash_full_alert_time = 0  # Variável para armazenar o tempo (em segundos desde 1970) do último alerta de lixeira cheia
last_temp_alert_time = 0  # Variável para controlar o tempo do último alerta de temperatura
last_hum_alert_time = 0  # Variável para controlar o tempo do último alerta de umidade

# --- Funções do Sistema ---

def get_blynk_data():
    """
    Obtém os dados de temperatura, umidade e nível de enchimento da lixeira do servidor Blynk.
    Em caso de falha na conexão, retorna valores zerados e define data['offline'] como True.

    Returns:
        dict: Um dicionário contendo os dados obtidos do Blynk, com as chaves "temperature", "humidity", "filling" e "offline".
              Se houver algum erro na obtenção dos dados, os valores correspondentes no dicionário serão None e 'offline' será True.
    """
    data = {"temperature": None, "humidity": None, "filling": None, "offline": False}  # Inicializa um dicionário para armazenar os dados, com valores iniciais como None e 'offline' como False

    # Itera sobre os pares de nome do campo e pino virtual do Blynk
    for field_name, pin in {"temperature": "V0", "humidity": "V1", "filling": "V4"}.items():
        # Constrói a URL para a requisição à API do Blynk, incluindo o token de autenticação e o pino virtual
        url = f"https://{blynk_server}/external/api/get?token={blynk_token}&{pin}"  
        try:
            # Faz uma requisição GET para a URL construída com timeout de 5 segundos
            response = requests.get(url, timeout=5) 
            # Verifica se a requisição foi bem-sucedida (código de status 200)
            response.raise_for_status()  
            # Converte a resposta da API (em formato JSON) para um dicionário Python
            value = json.loads(response.text)
            # Extrai o valor do dado do dicionário e o converte para um número de ponto flutuante (float)
            data[field_name] = float(value) # Armazena o valor no dicionário data, na chave correspondente ao nome do campo
        except requests.exceptions.RequestException as e:
            # Captura qualquer erro que ocorra durante a requisição à API do Blynk (incluindo timeout)
            print(f"Erro ao obter dados do Blynk: {e}")  # Imprime uma mensagem de erro no console
            data['offline'] = True # Define 'offline' como True para indicar falha na conexão
            # Define todos os valores como zero em caso de erro
            data["temperature"] = 0.0
            data["humidity"] = 0.0
            data["filling"] = 0.0
    # Retorna o dicionário contendo os dados obtidos do Blynk (ou valores zerados e 'offline' = True em caso de erro)
    return data  

def send_telegram_alert(message):
    """
    Envia uma mensagem de alerta para o Telegram.

    Args:
        message (str): A mensagem de alerta a ser enviada.
    """
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"  # Constrói a URL da API do Telegram
    payload = {"chat_id": telegram_chat_id, "text": message}  # Define os parâmetros da mensagem (ID do chat e texto)
    try:
        response = requests.post(url, json=payload)  # Faz a requisição POST para a API do Telegram
        response.raise_for_status()  # Levanta uma exceção se o código de status da resposta não for 200 (OK)
        print("Alerta enviado com sucesso")  # Imprime uma mensagem de sucesso se a mensagem for enviada
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar alerta: {e}")  # Imprime uma mensagem de erro se houver algum problema

def ping_blynk():
    """
    Envia uma requisição ping para o servidor Blynk para verificar a conexão.

    Returns:
        bool: True se a conexão estiver ativa, False caso contrário.
    """
    url = f"https://{blynk_server}/external/api/isHardwareConnected?token={blynk_token}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        connected = json.loads(response.text)
        return bool(connected)
    except requests.exceptions.RequestException as e:
        print(f"Erro ao verificar a conexão com o Blynk: {e}")
        return False

def train_model(temperatures, humidities):
    """
    Treina os modelos de regressão linear para temperatura e umidade.

    Args:
        temperatures (list): Lista de valores de temperatura.
        humidities (list): Lista de valores de umidade.

    Returns:
        tuple: Uma tupla contendo os modelos de regressão linear treinados para temperatura e umidade.
    """
    # Prepara os dados para o treinamento do modelo
    X = np.arange(len(temperatures)).reshape(-1, 1)  # Cria um array NumPy com os índices das leituras
    y_temp = np.array(temperatures).reshape(-1, 1)  # Converte a lista de temperaturas em um array NumPy
    y_hum = np.array(humidities).reshape(-1, 1)  # Converte a lista de umidades em um array NumPy

    # Cria e treina os modelos de regressão linear
    model_temp = LinearRegression().fit(X, y_temp)  # Cria e treina o modelo para temperatura
    model_hum = LinearRegression().fit(X, y_hum)  # Cria e treina o modelo para umidade

    return model_temp, model_hum  # Retorna os modelos treinados

def predict_next_values(model_temp, model_hum, n=1):
    """
    Prediz os próximos valores de temperatura e umidade usando os modelos treinados.

    Args:
        model_temp: Modelo de regressão linear para temperatura.
        model_hum: Modelo de regressão linear para umidade.
        n (int, optional): Número de valores a serem previstos. Defaults to 1.

    Returns:
        tuple: Uma tupla contendo os valores previstos de temperatura e umidade.
    """
    last_index = len(model_temp.coef_) - 1  # Obtém o índice da última leitura usada no treinamento
    next_index = last_index + 1  # Calcula o índice da próxima leitura

    # Faz a previsão usando os modelos
    pred_temp = model_temp.predict(np.array([[next_index]]))  # Prediz a temperatura
    pred_hum = model_hum.predict(np.array([[next_index]]))  # Prediz a umidade

    return pred_temp[0][0], pred_hum[0][0]  # Retorna os valores previstos

def atualizar_interface():
    """
    Atualiza a interface gráfica com os dados em tempo real, previsões e alertas.
    Se o dispositivo estiver offline, exibe a mensagem "Dispositivo Offline" e zera os valores.
    """
    global data, model_temp, model_hum
    global label_temperatura, label_umidade, label_previsao_temp, label_previsao_hum, label_alerta, canvas_lixeira, label_offline
    global temperatures, humidities, indicador_temperatura, indicador_umidade
    global last_temp_alert_time, last_hum_alert_time

    # Verifica se o dispositivo está offline
    if data['offline']:
        # Se estiver offline:
        label_offline.config(text="Dispositivo Offline", fg="red") # Exibe a mensagem "Dispositivo Offline" em vermelho
        label_temperatura.config(text="Temperatura: --°C") # Limpa o valor da temperatura
        label_umidade.config(text="Umidade: --%") # Limpa o valor da umidade
        label_previsao_temp.config(text="Temperatura Prevista: --°C") # Limpa a previsão de temperatura
        label_previsao_hum.config(text="Umidade Prevista: --%") # Limpa a previsão de umidade
        label_capacidade_lixeira.config(text="Capacidade da Lixeira: --%") # Limpa o valor da capacidade da lixeira
        canvas_lixeira.delete("all")  # Limpa o canvas da lixeira
        indicador_temperatura.config(bg="white") # Define a cor do indicador de temperatura para branco
        indicador_umidade.config(bg="white") # Define a cor do indicador de umidade para branco
    else:
        # Se o dispositivo estiver online:
        label_offline.config(text="")  # Limpa a mensagem de offline

        # Verifica se há dados suficientes para treinar o modelo e fazer previsões
        if len(temperatures) >= 2 and len(humidities) >= 2:
            # Treina os modelos de regressão para temperatura e umidade
            model_temp, model_hum = train_model(temperatures, humidities)
            # Faz a previsão dos próximos valores de temperatura e umidade
            pred_temp, pred_hum = predict_next_values(model_temp, model_hum)

            # Atualiza os labels de previsão na interface gráfica
            label_previsao_temp.config(text=f"Temperatura Prevista: {pred_temp:.2f}°C")
            label_previsao_hum.config(text=f"Umidade Prevista: {pred_hum:.2f}%")

            # --- Verifica as Previsões e Gera Alertas ---
            mensagem_alerta = ""  # Inicializa a mensagem de alerta como vazia

            # Alertas de Temperatura
            if pred_temp >= temp_critico and (time.time() - last_temp_alert_time) >= 60:
                # Se a temperatura prevista for maior ou igual ao limite crítico e já tiver passado 1 minuto desde o último alerta
                mensagem_alerta += f"ALERTA CRÍTICO: Temperatura prevista muito alta ({pred_temp:.2f}°C). Verificar lixeira!\n"
                send_telegram_alert(
                    f"ALERTA CRÍTICO: Temperatura prevista muito alta ({pred_temp:.2f}°C). Verificar lixeira!"
                )
                last_temp_alert_time = time.time()  # Atualiza o tempo do último alerta de temperatura
            elif pred_temp >= temp_atencao and (time.time() - last_temp_alert_time) >= 60:
                # Se a temperatura prevista for maior ou igual ao limite de atenção e já tiver passado 1 minuto desde o último alerta
                mensagem_alerta += f"ALERTA: Temperatura prevista elevada ({pred_temp:.2f}°C). Monitorar a situação.\n"
                send_telegram_alert(
                    f"ALERTA: Temperatura prevista elevada ({pred_temp:.2f}°C). Monitorar a situação."
                )
                last_temp_alert_time = time.time()  # Atualiza o tempo do último alerta de temperatura

            # Alertas de Umidade
            if pred_hum >= hum_critico and (time.time() - last_hum_alert_time) >= 60:
                # Se a umidade prevista for maior ou igual ao limite crítico e já tiver passado 1 minuto desde o último alerta
                mensagem_alerta += f"ALERTA CRÍTICO: Umidade prevista muito alta ({pred_hum:.2f}%). Verificar lixeira!\n"
                send_telegram_alert(
                    f"ALERTA CRÍTICO: Umidade prevista muito alta ({pred_hum:.2f}%). Verificar lixeira!"
                )
                last_hum_alert_time = time.time()  # Atualiza o tempo do último alerta de umidade
            elif pred_hum >= hum_atencao and (time.time() - last_hum_alert_time) >= 60:
                # Se a umidade prevista for maior ou igual ao limite de atenção e já tiver passado 1 minuto desde o último alerta
                mensagem_alerta += f"ALERTA: Umidade prevista elevada ({pred_hum:.2f}%). Monitorar a situação.\n"
                send_telegram_alert(
                    f"ALERTA: Umidade prevista elevada ({pred_hum:.2f}%). Monitorar a situação."
                )
                last_hum_alert_time = time.time()  # Atualiza o tempo do último alerta de umidade

            # --- Atualiza o label de alerta na interface ---
            if mensagem_alerta:  # Se houver alguma mensagem de alerta
                label_alerta.config(text=mensagem_alerta, fg="red2")
            else:  # Se não houver alertas, limpa o label
                label_alerta.config(text="")

    janela.after(10000, atualizar_interface)  # Agenda a próxima atualização da interface após 10 segundos


def atualizar_dados_tempo_real():
    """
    Atualiza os dados em tempo real, obtidos do Blynk, e verifica o nível de enchimento da lixeira.
    Verifica ativamente o status da conexão com o Blynk.
    """
    global data, label_temperatura, label_umidade, label_capacidade_lixeira
    global canvas_lixeira, temperatures, humidities, last_trash_full_alert_time, indicador_temperatura, indicador_umidade

    # Verifica a conexão com o Blynk
    if ping_blynk():
        data = get_blynk_data()  # Obtém os dados mais recentes do Blynk
        data['offline'] = False # Define o dispositivo como online
        print(f"Dados obtidos: {data}")  # Imprime os dados obtidos no console (para debug)

        # Verifica se o dispositivo NÃO está offline
        if not data['offline']: 
            if data["temperature"] is not None:
                # Atualiza o label de temperatura na interface gráfica
                label_temperatura.config(text=f"Temperatura: {data['temperature']:.2f}°C")
                # Adiciona a temperatura atual à lista de temperaturas recentes
                temperatures.append(data["temperature"])
                # Mantém apenas as últimas 'window_size' temperaturas na lista
                temperatures = temperatures[-window_size:]

                # --- Controle da indicador de temperatura em tempo real ---
                if data[
                    "temperature"
                ] >= temp_critico:  # Vermelho se a temperatura atual for maior ou igual ao limite crítico
                    indicador_temperatura.config(bg="red")
                elif (
                    data["temperature"] >= temp_atencao
                ):  # Laranja se a temperatura atual for maior ou igual ao limite de atenção
                    indicador_temperatura.config(bg="orange")
                else:  # Verde se a temperatura atual for menor que o limite de atenção
                    indicador_temperatura.config(bg="green")

                # Verifica se há um aumento constante na temperatura (em tempo real)
                if len(temperatures) >= 5:
                    temp_diff = temperatures[-1] - temperatures[-5]  # Calcula a diferença entre o último e o quinto valor
                    if temp_diff > temp_increase_threshold:
                        send_telegram_alert(f"Alerta de Tendência: Temperatura em Aumento!")

            if data["humidity"] is not None:
                # Atualiza o label de umidade na interface gráfica
                label_umidade.config(text=f"Umidade: {data['humidity']:.2f}%")
                # Adiciona a umidade atual à lista de umidades recentes
                humidities.append(data["humidity"])
                # Mantém apenas as últimas 'window_size' umidades na lista
                humidities = humidities[-window_size:]

                # --- Controle da indicador de umidade em tempo real ---
                if (
                    data["humidity"] >= hum_critico
                ):  # Vermelho se a umidade atual for maior ou igual ao limite crítico
                    indicador_umidade.config(bg="red")
                elif (
                    data["humidity"] >= hum_atencao
                ):  # Laranja se a umidade atual for maior ou igual ao limite de atenção
                    indicador_umidade.config(bg="orange")
                else:  # Verde se a umidade atual for menor que o limite de atenção
                    indicador_umidade.config(bg="green")

                # Verifica se há um aumento constante na umidade (em tempo real)
                if len(humidities) >= 5:
                    hum_diff = humidities[-1] - humidities[-5]  # Calcula a diferença entre o último e o quinto valor
                    if hum_diff > hum_increase_threshold:
                        send_telegram_alert(f"Alerta de Tendência: Umidade em Aumento!")

            if data["filling"] is not None:
                # Atualiza o label de capacidade da lixeira na interface
                label_capacidade_lixeira.config(text=f"Capacidade da Lixeira: {data['filling']}%")
                # Atualiza o gráfico da lixeira na interface
                preencher_lixeira(data["filling"])

                # Verifica se a lixeira está cheia e se passou tempo suficiente desde o último alerta
                if data["filling"] >= trash_full_threshold and (
                    last_trash_full_alert_time == 0 or time.time() - last_trash_full_alert_time >= 60
                ):
                    send_telegram_alert("Alerta de Lixeira: A lixeira está cheia!")
                    last_trash_full_alert_time = time.time()  # Atualiza o tempo do último alerta
    else:
        # Dispositivo offline
        data['offline'] = True
        print("Dispositivo Blynk offline.")

    janela.after(
        1000, atualizar_dados_tempo_real
    )  # Agenda a próxima atualização dos dados em tempo real após 1 segundo

def preencher_lixeira(capacidade):
    """
    Desenha e preenche o gráfico da lixeira na interface gráfica.

    Args:
        capacidade (float): O nível de enchimento da lixeira (em porcentagem).
    """
    global canvas_lixeira  # Acessa a variável global canvas_lixeira
    canvas_lixeira.delete("all")  # Limpa o canvas

    # Desenha o contorno da lixeira (bordas e topo)
    canvas_lixeira.create_line(50, 50, 50, 200, width=2)  # Borda esquerda
    canvas_lixeira.create_line(150, 50, 150, 200, width=2)  # Borda direita

    # Desenha o fundo branco para o indicador de nível
    canvas_lixeira.create_rectangle(51, 51, 149, 199, fill="white", outline="")

    # Define a cor do gráfico com base no nível de enchimento
    cor = "green"  # Verde para níveis baixos
    if capacidade >= trash_full_threshold:
        cor = "red"  # Vermelho para lixeira cheia
    elif capacidade >= 80:
        cor = "orange"  # Laranja para níveis altos
    elif capacidade >= 50:
        cor = "yellow"  # Amarelo para níveis médios

    # Calcula a altura do preenchimento no canvas
    altura_convertida = 200 - (capacidade * 150 / 100)
    # Desenha o retângulo que representa o nível de enchimento
    canvas_lixeira.create_rectangle(50, altura_convertida, 150, 200, fill=cor)
    # Atualiza o label de capacidade da lixeira
    label_capacidade_lixeira.config(text=f"Capacidade da Lixeira: {capacidade}%")

# --- Criação da Interface Gráfica ---

janela = tk.Tk()  # Cria a janela principal da interface
janela.title("Monitoramento de Ambiente")  # Define o título da janela

# Cria o label do título
label_titulo = tk.Label(janela, text="Monitoramento Lixeira", font=("Arial", 24, "bold"), bg='#24c48e', fg='white')
label_titulo.place(x=100, y=50)  # Posiciona o label na parte superior

# Cria os labels para exibir os dados
label_temperatura = tk.Label(janela, text="Temperatura: --°C", font=("Arial", 14))
label_temperatura.place(x=100, y=150)
label_temperatura.config(bg='#24c48e') # Define a cor de fundo como azul claro
label_temperatura.config(fg='#ffffff') # Define a cor da letra como branco

label_umidade = tk.Label(janela, text="Umidade: --%", font=("Arial", 14))
label_umidade.place(x=100, y=190)
label_umidade.config(bg='#24c48e') # Define a cor de fundo como azul claro
label_umidade.config(fg='#ffffff') # Define a cor da letra como branco

label_previsao_temp = tk.Label(janela, text="Temperatura Prevista: --°C", font=("Arial", 14))
label_previsao_temp.place(x=100, y=230)
label_previsao_temp.config(bg='#24c48e') # Define a cor de fundo como azul claro
label_previsao_temp.config(fg='#ffffff') # Define a cor da letra como branco

label_previsao_hum = tk.Label(janela, text="Umidade Prevista: --%", font=("Arial", 14))
label_previsao_hum.place(x=100, y=270)
label_previsao_hum.config(bg='#24c48e') # Define a cor de fundo como azul claro
label_previsao_hum.config(fg='#ffffff') # Define a cor da letra como branco

# Label para exibir a mensagem "Dispositivo Offline"
label_offline = tk.Label(janela, text="", font=("Arial", 14, "bold"), fg="red")
label_offline.place(x=100, y=100)  # Posiciona o label acima dos outros
label_offline.config(bg='#24c48e') # Define a cor de fundo como azul claro
label_offline.config(fg='#ffffff') # Define a cor da letra como branco

label_alerta = tk.Label(janela, text="", font=("Arial", 14, "bold"))
label_alerta.place(x=100, y=310)
label_alerta.config(bg='#24c48e') # Define a cor de fundo como azul claro

# Cria o canvas para o gráfico da lixeira
canvas_lixeira = tk.Canvas(janela, width=200, height=200, bg='#24c48e', highlightthickness=0)
canvas_lixeira.place(x=820, y=320)

# Cria o label para a capacidade da lixeira
label_capacidade_lixeira = tk.Label(janela, text="Capacidade da Lixeira: 0%", font=("Arial", 14), fg="#000000")
label_capacidade_lixeira.place(x=800, y=540)
label_capacidade_lixeira.config(bg='#24c48e') # Define a cor de fundo como azul claro
label_capacidade_lixeira.config(fg='#ffffff') # Define a cor da letra como branco

# Cria os indicadores que mudam de cor de acordo com os alertas
indicador_temperatura = tk.Canvas(janela, width=20, height=20, bg="white", borderwidth=0)
indicador_temperatura.place(x=300, y=150)

indicador_umidade = tk.Canvas(janela, width=20, height=20, bg="white", borderwidth=0)
indicador_umidade.place(x=300, y=190)

# --- Inicialização do Programa ---

# Inicializa as listas que armazenarão os dados de temperatura e umidade
temperatures = []
humidities = []

# Inicializa o dicionário data com 'offline' como False para evitar erros na primeira atualização da interface
data = {"offline": False} 

# Obtém os dados iniciais do Blynk
initial_data = get_blynk_data()
if initial_data["filling"] is not None:
    # Se os dados de enchimento forem válidos, preenche o gráfico da lixeira
    preencher_lixeira(initial_data["filling"])
    # Se a lixeira estiver cheia, envia um alerta
    if initial_data["filling"] >= trash_full_threshold:
        send_telegram_alert("Alerta de Lixeira: A lixeira está cheia!")
        last_trash_full_alert_time = time.time()  # Define o tempo do último alerta

# Define o tamanho da janela principal
janela.geometry("1280x720")
janela.config(bg='#24c48e') # Define a cor de fundo como azul claro

# Inicia as funções de atualização da interface e dos dados em tempo real
atualizar_interface()
atualizar_dados_tempo_real()

# Inicia o loop principal da interface gráfica
janela.mainloop()

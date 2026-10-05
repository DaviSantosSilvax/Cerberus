from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv('MQTT_HOST', '163.176.173.232')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_USER = os.getenv('MQTT_USER', 'esp32')
MQTT_PASS = os.getenv('MQTT_PASS', 'jD8l30JiFjw2hvf1IkVK4uW')

estado_quarto = {
    'temperatura': None,
    'umidade': None,
    'lampada': 'off',
    'ar': 'off',
}

_client = None
_loop = None
_callback_comando = None

def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        print('LOG MQTT: Conectado com sucesso ao broker!')
        client.subscribe('quarto/temperatura')
        client.subscribe('quarto/umidade')
        client.subscribe('quarto/lampada')
        client.subscribe('quarto/ar')
        client.subscribe('quarto/lampada/set')
        client.subscribe('quarto/ar/set')
        client.subscribe('quarto/sincronizar')
        client.subscribe('quarto/spotify/comando')
    else:
        print(f'LOG MQTT: Falha ao conectar, codigo {rc}')

def _on_message(client, userdata, msg):
    try:
        topico = msg.topic
        valor = msg.payload.decode('latin1', errors='ignore').strip()

        if topico == 'quarto/temperatura':
            try: estado_quarto['temperatura'] = float(valor)
            except: pass
        elif topico == 'quarto/umidade':
            try: estado_quarto['umidade'] = float(valor)
            except: pass
        elif topico == 'quarto/lampada':
            estado_quarto['lampada'] = valor
        elif topico == 'quarto/ar':
            estado_quarto['ar'] = valor
        elif topico in ('quarto/lampada/set', 'quarto/ar/set', 'quarto/sincronizar', 'quarto/spotify/comando'):
            if _callback_comando and _loop and _loop.is_running():
                asyncio.run_coroutine_threadsafe(_callback_comando(topico, valor), _loop)
    except Exception as e:
        print(f'LOG MQTT: Erro ao processar mensagem: {e}')

def obter_cliente_mqtt():
    global _client
    if _client is None:
        try:
            # Compatível com paho-mqtt v1 e v2
            try:
                _client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
            except Exception:
                _client = mqtt.Client()
            if MQTT_USER and MQTT_PASS:
                _client.username_pw_set(MQTT_USER, MQTT_PASS)
            _client.on_connect = _on_connect
            _client.on_message = _on_message
            _client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            _client.loop_start()
        except Exception as e:
            print(f'LOG MQTT: Erro ao iniciar cliente MQTT: {e}')
            _client = None
    return _client

async def escutar_mqtt(callback_comando=None):
    global _loop, _callback_comando
    _loop = asyncio.get_running_loop()
    _callback_comando = callback_comando
    obter_cliente_mqtt()
    while True:
        await asyncio.sleep(60)

async def publicar(topico: str, mensagem: str, retain: bool = False) -> bool:
    """Publica uma mensagem no broker MQTT de forma assincrona e sem travar."""
    try:
        cli = obter_cliente_mqtt()
        if cli:
            info = cli.publish(topico, mensagem, retain=retain)
            return True
        return False
    except Exception as e:
        print(f'LOG MQTT: Falha ao publicar em {topico}: {e}')
        return False

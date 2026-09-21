from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
import aiomqtt

MQTT_HOST = os.getenv('MQTT_HOST', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_USER = os.getenv('MQTT_USER')
MQTT_PASS = os.getenv('MQTT_PASS')

estado_quarto = {
    'temperatura': None,
    'umidade': None,
    'lampada': 'off',
    'ar': 'off',
}

async def escutar_mqtt(callback_comando=None):
    while True:
        try:
            async with aiomqtt.Client(
                hostname=MQTT_HOST, port=MQTT_PORT,
                username=MQTT_USER, password=MQTT_PASS,
            ) as client:
                await client.subscribe('quarto/temperatura')
                await client.subscribe('quarto/umidade')
                await client.subscribe('quarto/lampada')
                await client.subscribe('quarto/ar')
                await client.subscribe('quarto/lampada/set')
                await client.subscribe('quarto/ar/set')
                await client.subscribe('quarto/sincronizar')
                print('LOG MQTT: Conectado e escutando topicos de status e comandos!')
                async for msg in client.messages:
                    valor = msg.payload.decode()
                    topico_str = str(msg.topic)
                    if msg.topic.matches('quarto/temperatura'):
                        try: estado_quarto['temperatura'] = float(valor)
                        except: pass
                    elif msg.topic.matches('quarto/umidade'):
                        try: estado_quarto['umidade'] = float(valor)
                        except: pass
                    elif msg.topic.matches('quarto/lampada'):
                        estado_quarto['lampada'] = valor
                    elif msg.topic.matches('quarto/ar'):
                        estado_quarto['ar'] = valor
                    elif msg.topic.matches('quarto/lampada/set') or msg.topic.matches('quarto/ar/set') or msg.topic.matches('quarto/sincronizar'):
                        if callback_comando:
                            await callback_comando(topico_str, valor)
        except Exception as e:
            print('LOG MQTT: erro na conexao, tentando de novo em 5s:', e)
            await asyncio.sleep(5)

async def publicar(topico: str, mensagem: str):
    async with aiomqtt.Client(
        hostname=MQTT_HOST, port=MQTT_PORT,
        username=MQTT_USER, password=MQTT_PASS,
    ) as client:
        await client.publish(topico, mensagem)

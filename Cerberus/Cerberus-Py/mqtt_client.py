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
}

async def escutar_mqtt():
    while True:
        try:
            async with aiomqtt.Client(
                hostname=MQTT_HOST, port=MQTT_PORT,
                username=MQTT_USER, password=MQTT_PASS,
            ) as client:
                await client.subscribe('quarto/temperatura')
                await client.subscribe('quarto/umidade')
                async for msg in client.messages:
                    valor = msg.payload.decode()
                    if msg.topic.matches('quarto/temperatura'):
                        estado_quarto['temperatura'] = float(valor)
                    elif msg.topic.matches('quarto/umidade'):
                        estado_quarto['umidade'] = float(valor)
        except Exception as e:
            print('LOG MQTT: erro na conexão, tentando de novo em 5s:', e)
            await asyncio.sleep(5)

async def publicar(topico: str, mensagem: str):
    async with aiomqtt.Client(
        hostname=MQTT_HOST, port=MQTT_PORT,
        username=MQTT_USER, password=MQTT_PASS,
    ) as client:
        await client.publish(topico, mensagem)

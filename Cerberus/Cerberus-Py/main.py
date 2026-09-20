import os
import asyncio
import re
import unicodedata
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tuya_connector import TuyaOpenAPI
from groq import AsyncGroq
from mqtt_client import escutar_mqtt, publicar, estado_quarto

load_dotenv()

ACCESS_ID = os.getenv('TUYA_ACCESS_ID')
ACCESS_SECRET = os.getenv('TUYA_ACCESS_SECRET')
ENDPOINT = os.getenv('TUYA_ENDPOINT', 'https://openapi.tuyaus.com')

DEVICE_LAMPADA_ID = os.getenv('DEVICE_LAMPADA_ID')
DEVICE_TOMADA_AR_ID = os.getenv('DEVICE_TOMADA_AR_ID')

GROQ_API_KEY = os.getenv('GROQ_API_KEY')

if not ACCESS_ID or not ACCESS_SECRET:
    raise ValueError('ERRO: TUYA_ACCESS_ID e TUYA_ACCESS_SECRET devem ser definidos no arquivo .env')

openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_SECRET)
openapi.connect()

groq_client = AsyncGroq(api_key=GROQ_API_KEY)

@asynccontextmanager
async def lifespan(app: FastAPI):
    tarefa_mqtt = asyncio.create_task(escutar_mqtt())
    yield
    tarefa_mqtt.cancel()

app = FastAPI(title='Cerberus Home API', version='1.0.0', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

class PowerRequest(BaseModel):
    state: bool

class WhiteRequest(BaseModel):
    bright: int
    temp: int

class ColorRequest(BaseModel):
    h: int
    s: int = 1000
    v: int = 1000

class ChatRequest(BaseModel):
    mensagem: str

def check_tuya_response(response: dict):
    print('LOG TUYA API:', response)
    if not response.get('success', False):
        err_msg = response.get('msg', 'Erro desconhecido')
        err_code = response.get('code', 500)
        raise HTTPException(status_code=400, detail=f'Erro Tuya {err_code}: {err_msg}')
    return response

@app.get('/api/lampada/status')
def get_lampada_status():
    res = openapi.get(f'/v1.0/iot-03/devices/{DEVICE_LAMPADA_ID}')
    if res.get('success'):
        result = res.get('result', {})
        return {
            'online': result.get('online', False),
            'name': result.get('name', 'Lumi'),
            'status': result.get('status', [])
        }
    return {'online': False, 'error': res}

@app.post('/api/lampada/power')
def set_lampada_power(req: PowerRequest):
    commands = [{'code': 'switch_led', 'value': req.state}]
    res = openapi.post(f'/v1.0/iot-03/devices/{DEVICE_LAMPADA_ID}/commands', {'commands': commands})
    return check_tuya_response(res)

@app.post('/api/lampada/white')
def set_lampada_white(req: WhiteRequest):
    commands = [
        {'code': 'work_mode', 'value': 'white'},
        {'code': 'bright_value_v2', 'value': req.bright},
        {'code': 'temp_value_v2', 'value': req.temp}
    ]
    res = openapi.post(f'/v1.0/iot-03/devices/{DEVICE_LAMPADA_ID}/commands', {'commands': commands})
    return check_tuya_response(res)

@app.post('/api/lampada/color')
def set_lampada_color(req: ColorRequest):
    commands = [
        {'code': 'work_mode', 'value': 'colour'},
        {'code': 'colour_data_v2', 'value': {'h': req.h, 's': req.s, 'v': req.v}}
    ]
    res = openapi.post(f'/v1.0/iot-03/devices/{DEVICE_LAMPADA_ID}/commands', {'commands': commands})
    return check_tuya_response(res)

@app.post('/api/lampada/mode')
def set_lampada_mode(req: dict):
    mode = req.get('mode', 'white')
    commands = [{'code': 'work_mode', 'value': mode}]
    res = openapi.post(f'/v1.0/iot-03/devices/{DEVICE_LAMPADA_ID}/commands', {'commands': commands})
    return check_tuya_response(res)

@app.get('/api/ar-condicionado/status')
def get_tomada_ar_status():
    res = openapi.get(f'/v1.0/iot-03/devices/{DEVICE_TOMADA_AR_ID}')
    if res.get('success'):
        result = res.get('result', {})
        return {
            'online': result.get('online', False),
            'name': result.get('name', 'Lumi ar condicionado'),
            'status': result.get('status', [])
        }
    return {'online': False, 'error': res}

@app.post('/api/ar-condicionado/power')
def set_tomada_ar_power(req: PowerRequest):
    commands = [{'code': 'switch_1', 'value': req.state}]
    res = openapi.post(f'/v1.0/iot-03/devices/{DEVICE_TOMADA_AR_ID}/commands', {'commands': commands})
    return check_tuya_response(res)

@app.get('/api/dashboard/quarto')
def get_status_quarto():
    return estado_quarto

@app.post('/api/lampada-quarto/power')
async def set_lampada_quarto_power(req: PowerRequest):
    await publicar('quarto/lampada', 'on' if req.state else 'off')
    return {'ok': True}

def sem_acento(texto: str) -> str:
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()

async def voltar_ocioso(segundos: float):
    await asyncio.sleep(segundos)
    await publicar('quarto/estado', 'ocioso')

EMOCOES = {'feliz', 'triste', 'bravo', 'surpreso', 'amoroso', 'neutro'}
SYSTEM_PROMPT = (
    'Voce e o Cerberus, assistente de uma casa inteligente. Responda em portugues, '
    'em ate 2 frases curtas. Comece SEMPRE com uma tag de emocao entre colchetes, '
    'escolhida conforme o tom da conversa: [feliz], [triste], [bravo], [surpreso], '
    '[amoroso] ou [neutro]. Exemplo: [feliz] Que bom te ver por aqui!'
)

def separar_emocao(bruto: str):
    m = re.match(r'\s*\[(\w+)\]\s*(.*)', bruto, re.S)
    if m and m.group(1).lower() in EMOCOES:
        return m.group(1).lower(), m.group(2).strip()
    return 'neutro', bruto.strip()

@app.post('/api/chat')
async def chat(req: ChatRequest):
    await publicar('quarto/estado', 'pensando')
    try:
        resposta = await groq_client.chat.completions.create(
            model=os.getenv('GROQ_MODEL'),
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': req.mensagem},
            ],
        )
    except Exception as e:
        print('LOG GROQ:', repr(e))
        await publicar('quarto/estado', 'ocioso')
        raise HTTPException(status_code=502, detail=f'Erro na Groq: {e}')
    emocao, texto = separar_emocao(resposta.choices[0].message.content)
    await publicar('quarto/emocao', emocao)
    await publicar('quarto/legenda', sem_acento(texto)[:300])
    await publicar('quarto/estado', 'falando')
    asyncio.create_task(voltar_ocioso(max(3, len(texto) / 15)))
    return {'resposta': texto, 'emocao': emocao}

    return {'resposta': texto}

if __name__ == '__main__':
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)

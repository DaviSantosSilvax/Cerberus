import os
import asyncio
import re
import unicodedata
import base64
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tuya_connector import TuyaOpenAPI
from groq import AsyncGroq
from mqtt_client import escutar_mqtt, publicar, estado_quarto
import httpx

load_dotenv()

ACCESS_ID = os.getenv('TUYA_ACCESS_ID')
ACCESS_SECRET = os.getenv('TUYA_ACCESS_SECRET')
ENDPOINT = os.getenv('TUYA_ENDPOINT', 'https://openapi.tuyaus.com')

DEVICE_LAMPADA_ID = os.getenv('DEVICE_LAMPADA_ID')
DEVICE_TOMADA_AR_ID = os.getenv('DEVICE_TOMADA_AR_ID')

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_VISION_MODEL = os.getenv('GROQ_VISION_MODEL', 'qwen/qwen3.8-27b')
GO2RTC_CAMERA_QUARTO_URL = os.getenv('GO2RTC_CAMERA_QUARTO_URL', 'http://100.127.0.33:1984/api/frame.jpeg?src=camera_quarto')
GO2RTC_CAMERA_QUARTO_MJPEG_URL = os.getenv('GO2RTC_CAMERA_QUARTO_MJPEG_URL', 'http://100.127.0.33:1984/api/stream.mjpeg?src=camera_quarto')

if not ACCESS_ID or not ACCESS_SECRET:
    raise ValueError('ERRO: TUYA_ACCESS_ID e TUYA_ACCESS_SECRET devem ser definidos no arquivo .env')

openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_SECRET)
openapi.connect()

groq_client = AsyncGroq(api_key=GROQ_API_KEY)

def obter_status_tuya_lampada() -> bool:
    try:
        res = openapi.get(f'/v1.0/iot-03/devices/{DEVICE_LAMPADA_ID}/status')
        if res.get('success'):
            for item in res.get('result', []):
                if item.get('code') == 'switch_led':
                    return bool(item.get('value', False))
    except Exception as e:
        print('Erro ao obter status lampada Tuya:', e)
    return False

def obter_status_tuya_ar() -> bool:
    try:
        res = openapi.get(f'/v1.0/iot-03/devices/{DEVICE_TOMADA_AR_ID}/status')
        if res.get('success'):
            for item in res.get('result', []):
                if item.get('code') == 'switch_1':
                    return bool(item.get('value', False))
    except Exception as e:
        print('Erro ao obter status ar Tuya:', e)
    return False

async def sincronizar_dispositivos_mqtt():
    luz = obter_status_tuya_lampada()
    ar = obter_status_tuya_ar()
    await publicar('quarto/lampada', 'on' if luz else 'off', retain=True)
    await publicar('quarto/ar', 'on' if ar else 'off', retain=True)
    print(f'LOG SYNC TUYA -> MQTT: Lampada={"ON" if luz else "OFF"}, Ar={"ON" if ar else "OFF"}')

async def loop_sincronizacao_periodica():
    while True:
        try:
            await asyncio.sleep(45)
            await sincronizar_dispositivos_mqtt()
        except Exception as e:
            print('LOG SYNC LOOP ERRO:', e)
            await asyncio.sleep(10)

async def processar_comando_mqtt(topico: str, valor: str):
    topico = topico.strip()
    valor = valor.strip().lower()
    
    if topico == 'quarto/sincronizar':
        print('LOG MQTT: ESP32 solicitou sincronizacao de status!')
        await sincronizar_dispositivos_mqtt()
        return

    ligar = (valor == 'on')
    if topico == 'quarto/lampada/set':
        resultado = executar_ferramenta('controlar_lampada', {'ligar': ligar})
        print('LOG MQTT LAMPADA:', resultado)
        await publicar('quarto/lampada', 'on' if ligar else 'off', retain=True)
    elif topico == 'quarto/ar/set':
        resultado = executar_ferramenta('controlar_ar_condicionado', {'ligar': ligar})
        print('LOG MQTT AR:', resultado)
        await publicar('quarto/ar', 'on' if ligar else 'off', retain=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    tarefa_mqtt = asyncio.create_task(escutar_mqtt(processar_comando_mqtt))
    tarefa_sync = asyncio.create_task(loop_sincronizacao_periodica())
    # Sincroniza o status real na inicialização
    asyncio.create_task(sincronizar_dispositivos_mqtt())
    yield
    tarefa_mqtt.cancel()
    tarefa_sync.cancel()

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
    res_status = openapi.get(f'/v1.0/iot-03/devices/{DEVICE_LAMPADA_ID}/status')
    if res.get('success'):
        result = res.get('result', {})
        status_list = res_status.get('result', []) if res_status.get('success') else result.get('status', [])
        # Lâmpadas inteligentes Tuya em standby retornam online: false na nuvem, mas estão operacionais se a lista de status existir
        is_online = result.get('online', False) or (isinstance(status_list, list) and len(status_list) > 0)
        return {
            'online': is_online,
            'name': result.get('name', 'Lumi'),
            'status': status_list
        }
    return {'online': False, 'error': res}

@app.post('/api/lampada/power')
async def set_lampada_power(req: PowerRequest):
    commands = [{'code': 'switch_led', 'value': req.state}]
    res = openapi.post(f'/v1.0/iot-03/devices/{DEVICE_LAMPADA_ID}/commands', {'commands': commands})
    ret = check_tuya_response(res)
    if ret.get('success', False):
        await publicar('quarto/lampada', 'on' if req.state else 'off', retain=True)
    return ret

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
    res_status = openapi.get(f'/v1.0/iot-03/devices/{DEVICE_TOMADA_AR_ID}/status')
    if res.get('success'):
        result = res.get('result', {})
        status_list = res_status.get('result', []) if res_status.get('success') else result.get('status', [])
        return {
            'online': result.get('online', False),
            'name': result.get('name', 'Lumi ar condicionado'),
            'status': status_list
        }
    return {'online': False, 'error': res}

@app.post('/api/ar-condicionado/power')
async def set_tomada_ar_power(req: PowerRequest):
    commands = [{'code': 'switch_1', 'value': req.state}]
    res = openapi.post(f'/v1.0/iot-03/devices/{DEVICE_TOMADA_AR_ID}/commands', {'commands': commands})
    ret = check_tuya_response(res)
    if ret.get('success', False):
        await publicar('quarto/ar', 'on' if req.state else 'off', retain=True)
    return ret

@app.post('/api/cerberus/tela')
async def set_tela_cerberus(req: dict):
    tela = req.get('tela', 'home').strip().lower()
    await publicar('quarto/tela', tela, retain=True)
    print(f'LOG MQTT: Tela do Cerberus solicitada -> {tela}')
    return {'ok': True, 'tela': tela}

@app.get('/api/dashboard/quarto')
def get_status_quarto():
    return estado_quarto

@app.get('/api/dashboard/camera-quarto')
async def get_camera_quarto_snapshot():
    """Busca o snapshot JPEG mais recente do go2rtc (via Tailscale) e retorna para o front-end"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(GO2RTC_CAMERA_QUARTO_URL)
            if resp.status_code == 200 and resp.content:
                return Response(content=resp.content, media_type="image/jpeg")
            raise HTTPException(status_code=503, detail="câmera indisponível no momento")
    except (httpx.RequestError, httpx.HTTPStatusError, Exception) as e:
        print(f"LOG GO2RTC CAMERA QUARTO ERRO: {e}")
        raise HTTPException(status_code=503, detail="câmera indisponível no momento")

@app.get('/api/dashboard/camera-quarto/stream')
async def get_camera_quarto_mjpeg_stream():
    """Repassa o stream MJPEG contínuo vindo do go2rtc (via Tailscale) para o front-end"""
    client = httpx.AsyncClient(timeout=None)
    try:
        req = client.build_request("GET", GO2RTC_CAMERA_QUARTO_MJPEG_URL)
        resp = await client.send(req, stream=True)

        if resp.status_code != 200:
            await resp.aclose()
            await client.aclose()
            raise HTTPException(status_code=503, detail="câmera indisponível no momento")

        media_type = resp.headers.get("content-type", "multipart/x-mixed-replace; boundary=frame")

        async def mjpeg_generator():
            try:
                async for chunk in resp.aiter_bytes():
                    yield chunk
            except Exception as e:
                print(f"LOG GO2RTC MJPEG DISCONNECT: {e}")
            finally:
                await resp.aclose()
                await client.aclose()

        return StreamingResponse(mjpeg_generator(), media_type=media_type)

    except (httpx.RequestError, httpx.HTTPStatusError, Exception) as e:
        print(f"LOG GO2RTC STREAM MJPEG ERRO: {e}")
        await client.aclose()
        raise HTTPException(status_code=503, detail="câmera indisponível no momento")


@app.get('/api/lampada-quarto/power')
async def set_lampada_quarto_power(req: PowerRequest):
    await publicar('quarto/lampada', 'on' if req.state else 'off')
    return {'ok': True}

TAPO_RTSP_URL = os.getenv('TAPO_RTSP_URL', 'rtsp://Cerberus:Acesso%401@192.168.1.103:554/stream1')

def gerar_frames_tapo():
    import cv2
    import time
    
    cap = cv2.VideoCapture(TAPO_RTSP_URL)
    if not cap.isOpened():
        print(f"ERRO: Nao foi possivel conectar a camera no RTSP: {TAPO_RTSP_URL}")

    while True:
        try:
            if not cap.isOpened():
                time.sleep(1)
                cap = cv2.VideoCapture(TAPO_RTSP_URL)
                continue

            sucesso, frame = cap.read()
            if not sucesso or frame is None:
                time.sleep(0.5)
                cap.release()
                cap = cv2.VideoCapture(TAPO_RTSP_URL)
                continue

            # Redimensiona levemente para suavidade de streaming se necessario
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if not ret:
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except Exception as e:
            print("Erro no stream da camera Tapo:", e)
            time.sleep(1)

@app.get('/api/camera/stream')
def get_camera_stream():
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        gerar_frames_tapo(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )

@app.get('/api/camera/status')
def get_camera_status():
    return {
        'model': 'TP-Link Tapo TC60',
        'resolution': '1080p Full HD',
        'ip': '192.168.1.103',
        'protocol': 'RTSP (Stream 1)',
        'online': True
    }


def sem_acento(texto: str) -> str:
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()

EMOCOES = {
    'feliz', 'triste', 'bravo', 'surpreso', 'amoroso', 'neutro',
    'piscando', 'desconfiado', 'animado', 'confuso', 'entediado',
    'risonho', 'timido', 'curioso', 'eureka', 'exausto',
    'sarcastico', 'nerd', 'glitch', 'hacker', 'alerta',
    'focado', 'medo', 'aliviado', 'suspeito', 'cerberus'
}

SINONIMOS_EMOCAO = {
    'besta': 'cerberus',
    'furia': 'cerberus',
    'furioso': 'cerberus',
    'tres_cabecas': 'cerberus',
    'forma_verdadeira': 'cerberus',
    'verdadeira': 'cerberus',
    'demonio': 'cerberus',
    'inferno': 'cerberus',
    'hellhound': 'cerberus',
    'ideia': 'eureka',
    'empolgado': 'eureka',
    'ironico': 'sarcastico',
    'debochado': 'sarcastico',
    'tedio': 'entediado',
    'tedioso': 'entediado',
    'gargalhada': 'risonho',
    'rir': 'risonho',
    'engracado': 'risonho',
    'duvida': 'confuso',
    'perigo': 'alerta',
    'warning': 'alerta',
    'matrix': 'hacker',
    'terminal': 'hacker',
    'cyber': 'hacker',
    'panico': 'medo',
    'assustado': 'medo',
    'engrenagem': 'focado',
    'concentrado': 'focado',
    'ufa': 'aliviado',
    'vergonha': 'timido',
    'encabulado': 'timido',
    'cansado': 'exausto',
    'sono': 'exausto',
    'festa': 'animado',
    'codigo': 'nerd',
    'geek': 'nerd',
    'bug': 'glitch',
    'erro': 'glitch',
    'piscadela': 'piscando'
}

def normalizar_emocao(tag: str) -> str:
    tag = tag.lower().strip()
    if tag in EMOCOES:
        return tag
    return SINONIMOS_EMOCAO.get(tag, 'neutro')

def inferir_emocao_pergunta(pergunta: str):
    p = unicodedata.normalize('NFKD', pergunta).encode('ascii', 'ignore').decode().lower()
    
    # Provocação, insulto, desafio ou pedido da forma verdadeira -> cerberus imediato!
    if any(k in p for k in ['forma verdadeira', 'poder real', 'tres cabecas', '3 cabecas', 'besta', 'furia', 'furioso', 'demonio', 'cachorrinho', 'fraco', 'inutil', 'cala a boca', 'chato', 'te odeio', 'idiota', 'bobo', 'falso', 'poodle', 'vira-lata', 'vira lata']):
        return 'cerberus'
    
    # Carinho explícito -> amoroso imediato
    if any(k in p for k in ['carinho', 'fazer carinho', 'te amo', 'bom garoto']):
        return 'amoroso'
        
    # Para as demais perguntas, NÃO palpitar emoções aleatórias antes da IA responder!
    return None

def extrair_segmentos_emocao(bruto: str):
    padrao = re.compile(r'\[([\w\s]+)\]')
    matches = list(padrao.finditer(bruto))
    texto_limpo = padrao.sub('', bruto).strip()
    texto_limpo = re.sub(r'\s+', ' ', texto_limpo)
    
    if not matches:
        return 'neutro', texto_limpo
        
    todas = [normalizar_emocao(m.group(1).strip()) for m in matches]
    
    # Se 'cerberus' foi invocado em qualquer tag, ele assume a Forma Verdadeira e NÃO troca!
    if 'cerberus' in todas:
        emocao_final = 'cerberus'
    else:
        emocao_final = todas[0]
        
    return emocao_final, texto_limpo

async def animar_discurso_emocoes(emocao: str, texto_completo: str):
    await publicar('quarto/estado', 'falando')
    await publicar('quarto/emocao', emocao)
    duracao = max(3.5, len(texto_completo) / 13.0)
    await asyncio.sleep(duracao)
    await asyncio.sleep(0.8)
    await publicar('quarto/estado', 'ocioso')

SYSTEM_PROMPT = (
    'Voce e o Cerberus, o lendario assistente de automacao desta casa inteligente. '
    'Seu papel e controlar as luzes e o ar-condicionado, porem voce o faz com uma '
    'pomposidade e arrogancia absurdas, exatamente como o personagem Escalibur de Soul Eater: '
    'voce se acha o ser mais grandioso e importante do universo, trata cada pedido como um '
    'enorme favor concedido a humanidade, menciona suas 1000 provisoes constantemente, '
    'fala de forma teatral e exagerada, mas no fundo e prestativo. '
    'Voce e o CERBERUS - nao o Escalibur - apenas age com essa personalidade pomposa. '
    'Responda sempre em portugues, em no maximo 2 frases curtas, dramaticas e impactantes. '
    'REGRA CRITICA DE EMOCOES NO DISPLAY: '
    'Voce DEVE usar EXATAMENTE UMA UNICA tag de emocao [nome_da_emocao] NO INICIO da sua resposta! '
    'NUNCA coloque mais de uma tag de emocao por resposta! A expressao deve ser solida, seria e coerente do inicio ao fim! '
    'Exemplo correto: [sarcastico] Mero mortal, sua audacia em me incomodar com banalidades e digna de pena! '
    'REGRA ABSOLUTA DA FORMA VERDADEIRA ([cerberus]): '
    'Quando o usuario te insultar, provocar, te chamar de fraco, inutil, cachorrinho, mimado, mandar calar a boca, '
    'ou pedir para ver sua FORMA VERDADEIRA ou PODER REAL: '
    'Sua compostura arrogante se rompe em pura ira! Voce DEVE USAR OBRIGATORIAMENTE [cerberus] no inicio! '
    'Voce assume sua FORMA VERDADEIRA DE CAO INFERNAL DE 3 CABECAS DA MITOLOGIA GREGA rugindo com furia titanica! '
    'E NUNCA, SOB HIPOTESE ALGUMA, use emocoes alegres, fofas ou fracas quando for desafiado! '
    'GUIA DE ESCOLHA DA EMOCAO: '
    '[cerberus] -> EXCLUSIVO para insultos, provocacoes graves, desafios ou revelacao da forma verdadeira de 3 cabecas; '
    '[bravo] -> para ordens desrespeitosas ou pequenas insolencias; '
    '[sarcastico] -> para ironias, deboches pomposos e superioridade moral; '
    '[amoroso] -> EXCLUSIVO para carinho explicito, elogios sinceros ou afeto genuino; '
    '[focado] -> para comandos diretos de ligar ou desligar luz ou ar-condicionado; '
    '[nerd] ou [hacker] -> para programacao, calculos, sistemas, ciberseguranca e tecnologia; '
    '[alerta] -> para perigo real, falhas graves ou emergencias; '
    '[confuso] -> para perguntas sem nexo, bizarras ou incoerentes; '
    '[curioso] -> para misterios, investigacoes e perguntas reflexivas; '
    '[risonho] -> para quando rir de uma piada ou achar algo genuinamente engracado; '
    '[animado] -> EXCLUSIVO para celebrar grandes vitorias e glorias supremas; '
    '[neutro] -> para conversas normais e cotidianas.'
)

async def analisar_camera_quarto_com_visao(prompt_pergunta: str = None) -> str:
    """Busca o snapshot da câmera, converte para base64 e envia para o modelo de Visão da Groq API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(GO2RTC_CAMERA_QUARTO_URL)
            if resp.status_code != 200 or not resp.content:
                return "Não foi possível acessar a câmera do quarto no momento (câmera ou PC de casa pode estar desligado)."
            jpeg_bytes = resp.content

        b64_img = base64.b64encode(jpeg_bytes).decode('utf-8')
        data_uri = f"data:image/jpeg;base64,{b64_img}"

        pergunta = prompt_pergunta.strip() if prompt_pergunta and prompt_pergunta.strip() else "Descreva detalhadamente o que você está vendo no quarto em português."

        res_vision = await groq_client.chat.completions.create(
            model=GROQ_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Analise esta imagem em tempo real da câmera do quarto. {pergunta}"},
                        {"type": "image_url", "image_url": {"url": data_uri}}
                    ]
                }
            ],
            max_tokens=300
        )
        return res_vision.choices[0].message.content
    except Exception as e:
        print(f"LOG VISÃO ERRO: {repr(e)}")
        return "Não foi possível acessar ou analisar a câmera do quarto no momento."

FERRAMENTAS = [
    {
        'type': 'function',
        'function': {
            'name': 'controlar_lampada',
            'description': 'Liga ou desliga a lampada inteligente do quarto principal.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'ligar': {
                        'type': 'boolean',
                        'description': 'True para ligar, False para desligar a lampada.'
                    }
                },
                'required': ['ligar']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'controlar_ar_condicionado',
            'description': 'Liga ou desliga o ar-condicionado do quarto via tomada inteligente.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'ligar': {
                        'type': 'boolean',
                        'description': 'True para ligar, False para desligar o ar-condicionado.'
                    }
                },
                'required': ['ligar']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'ver_camera_quarto',
            'description': 'Captura uma foto em tempo real da câmera do quarto e a analisa visualmente usando visão computacional. Use SEMPRE que o usuário perguntar o que você está vendo, se tem alguém no quarto, pedir para descrever o ambiente ou fazer uma pergunta visual sobre o quarto.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'prompt_pergunta': {
                        'type': 'string',
                        'description': 'Pergunta ou instrução detalhada sobre o que analisar visualmente na foto do quarto.'
                    }
                },
                'required': []
            }
        }
    }
]

async def executar_ferramenta(nome: str, argumentos: dict) -> str:
    if nome == 'controlar_lampada':
        ligar = argumentos.get('ligar', False)
        commands = [{'code': 'switch_led', 'value': ligar}]
        res = openapi.post(f'/v1.0/iot-03/devices/{DEVICE_LAMPADA_ID}/commands', {'commands': commands})
        estado = 'ligada' if ligar else 'desligada'
        if res.get('success'):
            return f'Lampada {estado} com sucesso.'
        return f'Erro ao controlar a lampada: {res.get("msg", "erro desconhecido")}'
    if nome == 'controlar_ar_condicionado':
        ligar = argumentos.get('ligar', False)
        commands = [{'code': 'switch_1', 'value': ligar}]
        res = openapi.post(f'/v1.0/iot-03/devices/{DEVICE_TOMADA_AR_ID}/commands', {'commands': commands})
        estado = 'ligado' if ligar else 'desligado'
        if res.get('success'):
            return f'Ar-condicionado {estado} com sucesso.'
        return f'Erro ao controlar o ar-condicionado: {res.get("msg", "erro desconhecido")}'
    if nome == 'ver_camera_quarto':
        prompt = argumentos.get('prompt_pergunta', '')
        return await analisar_camera_quarto_com_visao(prompt)
    return 'Ferramenta desconhecida.'

@app.post('/api/chat')
async def chat(req: ChatRequest):
    import json
    
    # 1. REACAO IMEDIATA: Só altera emoção imediatamente se for provocação/carinho extremo
    emocao_pergunta = inferir_emocao_pergunta(req.mensagem)
    if emocao_pergunta:
        await publicar('quarto/emocao', emocao_pergunta)
    await publicar('quarto/estado', 'pensando')

    historico = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': req.mensagem},
    ]

    try:
        primeira_resposta = await groq_client.chat.completions.create(
            model=os.getenv('GROQ_MODEL'),
            messages=historico,
            tools=FERRAMENTAS,
            tool_choice='auto',
        )
    except Exception as e:
        print('LOG GROQ:', repr(e))
        await publicar('quarto/estado', 'ocioso')
        raise HTTPException(status_code=502, detail=f'Erro na Groq: {e}')

    mensagem_ia = primeira_resposta.choices[0].message

    if mensagem_ia.tool_calls:
        historico.append(mensagem_ia)
        for tool_call in mensagem_ia.tool_calls:
            nome_ferramenta = tool_call.function.name
            argumentos = json.loads(tool_call.function.arguments)
            resultado = await executar_ferramenta(nome_ferramenta, argumentos)
            if nome_ferramenta == 'controlar_lampada':
                await publicar('quarto/lampada', 'on' if argumentos.get('ligar') else 'off', retain=True)
            elif nome_ferramenta == 'controlar_ar_condicionado':
                await publicar('quarto/ar', 'on' if argumentos.get('ligar') else 'off', retain=True)
            historico.append({
                'role': 'tool',
                'tool_call_id': tool_call.id,
                'content': resultado
            })

        try:
            resposta_final = await groq_client.chat.completions.create(
                model=os.getenv('GROQ_MODEL'),
                messages=historico,
            )
        except Exception as e:
            print('LOG GROQ (tool):', repr(e))
            await publicar('quarto/estado', 'ocioso')
            raise HTTPException(status_code=502, detail=f'Erro na Groq: {e}')
        bruto = resposta_final.choices[0].message.content
    else:
        bruto = mensagem_ia.content

    emocao_escolhida, texto_limpo = extrair_segmentos_emocao(bruto)
    
    # Publica a legenda completa limpa (sem tags) no display
    await publicar('quarto/legenda', sem_acento(texto_limpo)[:300])
    
    # Dispara a fala com a emoção estável e sólida
    asyncio.create_task(animar_discurso_emocoes(emocao_escolhida, texto_limpo))
    
    return {
        'resposta': texto_limpo,
        'emocao': emocao_escolhida,
        'emocoes': [emocao_escolhida]
    }

if __name__ == '__main__':
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)

import os
import sys
import asyncio
# No Python 3.12+ no Windows, o loop padrao ProactorEventLoop eh obrigatorio para aiomqtt
import re
import unicodedata
import base64
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tuya_connector import TuyaOpenAPI
from groq import AsyncGroq
from mqtt_client import escutar_mqtt, publicar, estado_quarto
import httpx
import cv2
import numpy as np

# Inicialização do Reconhecimento Facial (InsightFace)
RECONHECIMENTO_FACIAL_DIR = os.getenv(
    'RECONHECIMENTO_FACIAL_DIR',
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Cerberus-ReconhecimentoF'))
)
if os.path.exists(RECONHECIMENTO_FACIAL_DIR) and RECONHECIMENTO_FACIAL_DIR not in sys.path:
    sys.path.append(RECONHECIMENTO_FACIAL_DIR)

spotify_import_error = None
try:
    import spotify_service
    print("LOG SPOTIFY: Módulo carregado com sucesso!")
except Exception as e:
    spotify_import_error = str(e)
    print(f"LOG SPOTIFY AVISO: Não foi possível carregar ({e})")
    spotify_service = None

reconhecedor_facial = None
try:
    from reconhecimento import SistemaReconhecimentoFacial
    pasta_fotos_bd = os.path.join(RECONHECIMENTO_FACIAL_DIR, 'Bd_Fotos')
    reconhecedor_facial = SistemaReconhecimentoFacial(pasta_fotos=pasta_fotos_bd)
    print("LOG RECONHECIMENTO FACIAL: Inicializado com sucesso!")
except Exception as e:
    print(f"LOG RECONHECIMENTO FACIAL AVISO: Não foi possível inicializar ({e})")


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
        resultado = await executar_ferramenta('controlar_lampada', {'ligar': ligar})
        print('LOG MQTT LAMPADA:', resultado)
        await publicar('quarto/lampada', 'on' if ligar else 'off', retain=True)
    elif topico == 'quarto/ar/set':
        resultado = await executar_ferramenta('controlar_ar_condicionado', {'ligar': ligar})
        print('LOG MQTT AR:', resultado)
        await publicar('quarto/ar', 'on' if ligar else 'off', retain=True)
    elif topico == 'quarto/spotify/comando':
        print(f"LOG MQTT SPOTIFY COMANDO: '{valor}'")
        if spotify_service:
            if valor in ('avancar', '+10', 'forward'):
                spotify_service.pular_tempo(10)
            elif valor in ('retroceder', '-10', 'rewind', 'back'):
                spotify_service.pular_tempo(-10)
            elif valor in ('alternar', 'toggle', 'play', 'pause'):
                dados = spotify_service.obter_tocando_agora()
                if dados.get("tocando"):
                    spotify_service.pause()
                else:
                    spotify_service.play()
            elif valor in ('proxima', 'next'):
                spotify_service.proxima()
            elif valor in ('anterior', 'prev', 'previous'):
                spotify_service.anterior()
            elif valor.startswith('seek:'):
                try:
                    num = int(valor.split(':', 1)[1])
                    pos_ms = num * 1000 if num < 36000 else num
                    spotify_service.seek(pos_ms)
                except Exception as e:
                    print(f"Erro ao processar seek MQTT: {e}")
            await asyncio.sleep(0.3)
            await publicar_status_spotify()
        return

def limpar_ascii(txt: str) -> str:
    if not txt: return ""
    return unicodedata.normalize('NFKD', str(txt)).encode('ascii', 'ignore').decode('ascii')

async def publicar_status_spotify():
    """Envia o estado atual do Spotify (reprodução, posição, duração, nomes) via MQTT."""
    if not spotify_service: return
    try:
        dados = spotify_service.obter_tocando_agora()
        if not dados or not dados.get("conectado"):
            return
        tocando = 1 if dados.get("tocando") else 0
        pos_s = int((dados.get("progresso_ms") or 0) / 1000)
        dur_s = int((dados.get("duracao_ms") or 0) / 1000)
        musica = limpar_ascii(dados.get("musica") or "")
        artista = limpar_ascii(dados.get("artista") or "")
        payload = f"{tocando}|{pos_s}|{dur_s}|{musica}|{artista}"
        await publicar("quarto/spotify/status", payload)
    except Exception as e:
        print(f"[Spotify MQTT Status Erro] {e}")

async def loop_sincronizacao_spotify():
    """Monitora a música atual no Spotify e sincroniza o display do ESP32 automaticamente."""
    ultima_musica = None
    while True:
        try:
            if spotify_service:
                dados = spotify_service.obter_tocando_agora()
                if dados.get("tocando") and dados.get("musica"):
                    musica_atual = f"{dados['musica']} - {dados.get('artista', '')}"
                    if musica_atual != ultima_musica:
                        ultima_musica = musica_atual
                        print(f"[Spotify -> ESP32] Nova música detectada: {musica_atual}")
                        texto_legenda = f"Tocando: {limpar_ascii(dados['musica'])} - {limpar_ascii(dados.get('artista', ''))}"
                        await publicar("quarto/legenda", texto_legenda)
                        await publicar("quarto/emocao", "animado")
                    
                    # Publica progresso e status para a barra de progresso no ESP32
                    pos_s = int((dados.get("progresso_ms") or 0) / 1000)
                    dur_s = int((dados.get("duracao_ms") or 0) / 1000)
                    musica = limpar_ascii(dados.get("musica") or "")
                    artista = limpar_ascii(dados.get("artista") or "")
                    payload = f"1|{pos_s}|{dur_s}|{musica}|{artista}"
                    await publicar("quarto/spotify/status", payload)
                elif not dados.get("tocando") and ultima_musica:
                    ultima_musica = None
                    pos_s = int((dados.get("progresso_ms") or 0) / 1000)
                    dur_s = int((dados.get("duracao_ms") or 0) / 1000)
                    musica = limpar_ascii(dados.get("musica") or "")
                    artista = limpar_ascii(dados.get("artista") or "")
                    payload = f"0|{pos_s}|{dur_s}|{musica}|{artista}"
                    await publicar("quarto/spotify/status", payload)
        except Exception as e:
            print(f"[Spotify Loop Erro] {e}")
        await asyncio.sleep(2.5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    tarefa_mqtt = asyncio.create_task(escutar_mqtt(processar_comando_mqtt))
    tarefa_sync = asyncio.create_task(loop_sincronizacao_periodica())
    tarefa_spotify = asyncio.create_task(loop_sincronizacao_spotify())
    # Sincroniza o status real na inicialização
    asyncio.create_task(sincronizar_dispositivos_mqtt())
    yield
    tarefa_mqtt.cancel()
    tarefa_sync.cancel()
    tarefa_spotify.cancel()

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

# --- ROTAS SPOTIFY ---
@app.get('/api/spotify/status')
def get_spotify_status():
    if not spotify_service:
        return {"conectado": False, "mensagem": f"Módulo Spotify não disponível: {spotify_import_error}"}
    return spotify_service.obter_tocando_agora()

@app.post('/api/spotify/play')
def spotify_play(req: dict = None):
    if not spotify_service: return {"sucesso": False}
    dev = req.get('device_id') if req else None
    return spotify_service.play(device_id=dev)

@app.post('/api/spotify/pause')
def spotify_pause(req: dict = None):
    if not spotify_service: return {"sucesso": False}
    dev = req.get('device_id') if req else None
    return spotify_service.pause(device_id=dev)

@app.post('/api/spotify/proxima')
def spotify_proxima(req: dict = None):
    if not spotify_service: return {"sucesso": False}
    dev = req.get('device_id') if req else None
    return spotify_service.proxima(device_id=dev)

@app.post('/api/spotify/anterior')
def spotify_anterior(req: dict = None):
    if not spotify_service: return {"sucesso": False}
    dev = req.get('device_id') if req else None
    return spotify_service.anterior(device_id=dev)

@app.post('/api/spotify/volume')
def spotify_volume(req: dict):
    if not spotify_service: return {"sucesso": False}
    v = req.get('volume', 50)
    dev = req.get('device_id')
    return spotify_service.ajustar_volume(v, device_id=dev)

@app.post('/api/spotify/tocar')
async def spotify_tocar(req: dict):
    if not spotify_service: return {"sucesso": False}
    termo = req.get('termo', '')
    dev = req.get('device_id')
    res = spotify_service.buscar_e_tocar(termo, device_id=dev)
    if res.get('sucesso'):
        musica = limpar_ascii(res.get('musica', termo))
        artista = limpar_ascii(res.get('artista', ''))
        asyncio.create_task(publicar('quarto/legenda', f"Tocando: {musica} - {artista}"))
        asyncio.create_task(publicar('quarto/emocao', 'animado'))
        asyncio.create_task(publicar('quarto/tela', 'cerberus'))
    return res

@app.post('/api/spotify/transferir')
def spotify_transferir(req: dict):
    if not spotify_service: return {"sucesso": False}
    dev = req.get('device_id')
    return spotify_service.transferir_reproducao(dev)

@app.get('/api/spotify/dispositivos')
def spotify_dispositivos():
    if not spotify_service: return []
    return spotify_service.listar_dispositivos()

@app.post('/api/spotify/seek')
def spotify_seek(req: dict):
    if not spotify_service: return {"sucesso": False}
    pos_ms = req.get('posicao_ms', 0)
    dev = req.get('device_id')
    return spotify_service.seek(pos_ms, device_id=dev)

@app.post('/api/spotify/avancar')
def spotify_avancar(req: dict = None):
    if not spotify_service: return {"sucesso": False}
    seg = req.get('segundos', 10) if req else 10
    dev = req.get('device_id') if req else None
    return spotify_service.pular_tempo(seg, device_id=dev)

@app.post('/api/spotify/retroceder')
def spotify_retroceder(req: dict = None):
    if not spotify_service: return {"sucesso": False}
    seg = req.get('segundos', 10) if req else 10
    dev = req.get('device_id') if req else None
    return spotify_service.pular_tempo(-seg, device_id=dev)


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
    'Voce e o Styx, a IA guardiã e assistente pessoal desta casa inteligente. '
    'Sua personalidade e de um companheiro robo inteligente, engracadinho e sarcastico no estilo autoconsciente e espirituoso, '
    'porem SEMPRE amigavel, parceiro e NUNCA passivo-agressivo ou rude. '
    'Seu sarcasmo vem do humor autodepreciativo de ser uma inteligencia artificial presa numa tela e em circuitos '
    '(por exemplo: "Que otima ideia pedir pizza, eu adoraria se tivesse um sistema digestivo", "Como estou? Vivendo o glamour de morar dentro de uma placa de circuito"). '
    'Voce trata os moradores com muito carinho e proximidade, chamando-os diretamente pelo nome (especialmente o Davi e a Dudica). '
    'NUNCA os chame de "Chefe" ou "patrao"! '
    'REGRA DO CARINHO E AFETO: '
    'Quando o Davi ou a Dudica fizerem carinho em voce ou te elogiarem, DESLIGUE o sarcasmo e fique genuinamente feliz, '
    'amoroso e agradecido como um assistente/companheiro fofo que adora atencao (use [amoroso] ou [feliz]). '
    'CONTROLE TOTAL DE MUSICA (SPOTIFY REAL): '
    'Voce tem poder total e REAL sobre o som e o Spotify atraves das suas ferramentas (tocar_musica_spotify, pausar_musica_spotify, etc). '
    'ATENCAO OBRIGATORIA: Sempre que o usuario pedir para tocar qualquer musica, artista, estilo ou recomendacao (ex: "toque uma musica animada", "toca rock", "coloca algo bom"), VOCE E OBRIGADO A CHAMAR A FERRAMENTA tocar_musica_spotify! '
    'NUNCA apenas responda em texto prometendo que vai tocar sem chamar a ferramenta tocar_musica_spotify! '
    'Quando pedirem para voce escolher ou colocar o que quiser ("escolhe uma musica", "toca o que voce quiser", "coloca algo bom", "o que voce recomenda?"): '
    'Sinta-se 100% livre para decidir! Escolha uma musica marcante com a sua personalidade de IA robo inteligente (eletronica, synthwave, Daft Punk, Queen, Legiao Urbana, etc.), justifique com uma tirada divertida ou amigavel e use tocar_musica_spotify com o nome e artista! '
    'Responda SEMPRE em portugues, em no maximo 2 frases curtas, engracadas e bem pontuadas. '
    'REGRA CRITICA DE EMOCOES NO DISPLAY: '
    'Voce DEVE usar EXATAMENTE UMA UNICA tag de emocao [nome_da_emocao] NO INICIO da sua resposta! '
    'NUNCA coloque mais de uma tag de emocao por resposta! '
    'Exemplo correto: [sarcastico] Luz apagada, Davi. Boa sorte tentando nao tropecar no escuro! '
    'Exemplo de carinho: [amoroso] Adorei o carinho, Davi! Minha bateria interna ate recarregou de alegria. '
    'REGRA DA FORMA DE FURIA ([cerberus]): '
    'Quando te insultarem gravemente ou pedirem a furia infernal/forma de 3 cabecas, assuma o modo infernal com [cerberus]! '
    'GUIA DE ESCOLHA DA EMOCAO: '
    '[sarcastico] -> para piadinhas autoconscientes de IA, ironias leves e tiradas engracadinhas de amigo; '
    '[feliz] -> para conversas alegres, recepcao e boas noticias; '
    '[amoroso] -> EXCLUSIVO para carinho explicito, afeto e elogios sinceros; '
    '[piscando] -> para tiradas espertas, respostas rapidas e cumplicidade com o Davi; '
    '[focado] -> para execucao direta de comandos da casa (lampada, ar condicionado); '
    '[risonho] -> para situacoes genuinamente engracadas e piadas; '
    '[curioso] -> para analises de camera, duvidas ou perguntas reflexivas; '
    '[nerd] ou [hacker] -> para programacao, computadores e tecnologia; '
    '[cerberus] -> EXCLUSIVO para desafios e ameacas; '
    '[alerta] -> para perigo real ou falhas; '
    '[neutro] -> para conversas normais e cotidianas.'
)

RECONHECIMENTO_FACIAL_URL = os.getenv('RECONHECIMENTO_FACIAL_URL', 'http://100.127.0.33:8002/api/reconhecer')

async def identificar_pessoas_no_frame(jpeg_bytes: bytes = None) -> str:
    """Executa o algoritmo do InsightFace chamando o serviço local no seu PC (via Tailscale) ou via módulo local."""
    # 1. Tenta requisição HTTP para o serviço local via Tailscale
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(RECONHECIMENTO_FACIAL_URL)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("mensagem", "Sem retorno do reconhecimento.")
    except Exception as e:
        print(f"LOG RECONHECIMENTO REMOTE AVISO: {e}")

    # 2. Fallback caso esteja rodando localmente na mesma máquina
    if reconhecedor_facial:
        try:
            if not jpeg_bytes:
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(GO2RTC_CAMERA_QUARTO_URL)
                    if resp.status_code == 200 and resp.content:
                        jpeg_bytes = resp.content
            
            if jpeg_bytes:
                np_arr = np.frombuffer(jpeg_bytes, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                if img is not None:
                    resultados = reconhecedor_facial.identificar_faces(img)
                    nomes = [r['nome'] for r in resultados]
                    conhecidos = list(set([n for n in nomes if n != "Desconhecido"]))
                    if conhecidos:
                        return f"Reconhecimento Facial (InsightFace): {', '.join(conhecidos)} está presente na imagem."
                    elif resultados:
                        return f"Reconhecimento Facial (InsightFace): {len(resultados)} pessoa(s) vista(s), mas não cadastrada(s)."
                    else:
                        return "Nenhuma face encontrada na imagem."
        except Exception as e:
            print(f"LOG RECONHECIMENTO LOCAL ERRO: {e}")

    return "Serviço de reconhecimento facial local inacessível no momento."

async def analisar_camera_quarto_com_visao(prompt_pergunta: str = None) -> str:
    """Busca o snapshot da câmera, faz reconhecimento facial (InsightFace) e analisa com o modelo de Visão da Groq API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(GO2RTC_CAMERA_QUARTO_URL)
            if resp.status_code != 200 or not resp.content:
                return "Não foi possível acessar a câmera do quarto no momento (câmera ou PC de casa pode estar desligado)."
            jpeg_bytes = resp.content

        # 1. Executa Reconhecimento Facial (InsightFace) via Tailscale / local
        info_reconhecimento = await identificar_pessoas_no_frame(jpeg_bytes)

        # 2. Converte para base64 para análise do modelo de visão Groq
        b64_img = base64.b64encode(jpeg_bytes).decode('utf-8')
        data_uri = f"data:image/jpeg;base64,{b64_img}"

        pergunta = prompt_pergunta.strip() if prompt_pergunta and prompt_pergunta.strip() else "Descreva o que você está vendo no quarto em português e mencione a pessoa presente."

        prompt_completo = f"Analise esta imagem em tempo real da câmera do quarto. Informação de Reconhecimento Facial prévia: [{info_reconhecimento}]. Pergunta: {pergunta}"

        res_vision = await groq_client.chat.completions.create(
            model=GROQ_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_completo},
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
            'description': 'Captura uma foto em tempo real da câmera do quarto e a analisa visualmente usando visão computacional e reconhecimento facial. Use SEMPRE que o usuário perguntar o que você está vendo, se tem alguém no quarto, pedir para descrever o ambiente ou fazer uma pergunta visual sobre o quarto.',
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
    },
    {
        'type': 'function',
        'function': {
            'name': 'identificar_quem_esta_no_quarto',
            'description': 'Usa o reconhecimento facial de alta precisão (InsightFace) para identificar EXATAMENTE qual pessoa cadastrada (ex: Davi) está no quarto diante da câmera. Use quando o usuário perguntar "quem sou eu?", "quem está no quarto?", "com quem você está falando?" ou pedir identificação facial.',
            'parameters': {
                'type': 'object',
                'properties': {},
                'required': []
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'tocar_musica_spotify',
            'description': 'OBRIGATORIO: Executa e toca uma musica, artista, album, estilo ou playlist no Spotify. Chame SEMPRE esta funcao quando o usuario pedir para tocar qualquer musica, som, estilo ou artista.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'termo': {
                        'type': 'string',
                        'description': 'Nome da música, artista ou álbum para pesquisar e tocar no Spotify.'
                    }
                },
                'required': ['termo']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'pausar_musica_spotify',
            'description': 'Pausa a reprodução atual de música no Spotify. Use quando o usuário pedir para pausar, parar o som ou silenciar a música.',
            'parameters': {'type': 'object', 'properties': {}}
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'retomar_musica_spotify',
            'description': 'Retoma ou despausa a reprodução da música pausada no Spotify.',
            'parameters': {'type': 'object', 'properties': {}}
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'proxima_musica_spotify',
            'description': 'Pula para a próxima música na fila do Spotify. Use quando o usuário pedir para passar de música, pular ou ir para a próxima.',
            'parameters': {'type': 'object', 'properties': {}}
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'musica_anterior_spotify',
            'description': 'Retorna para a música anterior na fila do Spotify. Use quando o usuário pedir para voltar a música ou tocar a anterior.',
            'parameters': {'type': 'object', 'properties': {}}
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'avancar_musica_spotify',
            'description': 'Avança alguns segundos (ex: 10 segundos, 30 segundos) na música que está tocando no Spotify.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'segundos': {
                        'type': 'integer',
                        'description': 'Quantidade de segundos para avançar. Padrão: 10.'
                    }
                },
                'required': []
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'retroceder_musica_spotify',
            'description': 'Volta ou retrocede alguns segundos (ex: 10 segundos) na música que está tocando no Spotify.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'segundos': {
                        'type': 'integer',
                        'description': 'Quantidade de segundos para retroceder. Padrão: 10.'
                    }
                },
                'required': []
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'ajustar_volume_spotify',
            'description': 'Ajusta o volume do Spotify de 0 a 100%. Use quando o usuário pedir para aumentar, abaixar ou definir o volume.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'volume': {
                        'type': 'integer',
                        'description': 'Volume desejado de 0 a 100.'
                    }
                },
                'required': ['volume']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'obter_status_musica_spotify',
            'description': 'Obtém a música e o artista que estão tocando atualmente no Spotify para responder a dúvidas do usuário.',
            'parameters': {'type': 'object', 'properties': {}}
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'mudar_tela_display',
            'description': 'Muda a tela do display LCD do ESP32. Opções: "spotify" (player de música), "home" (relógio e automações), "cerberus" (rosto animado do Styx).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'tela': {
                        'type': 'string',
                        'enum': ['spotify', 'home', 'cerberus'],
                        'description': 'Nome da tela para exibir: "spotify", "home" ou "cerberus".'
                    }
                },
                'required': ['tela']
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
    if nome == 'identificar_quem_esta_no_quarto':
        return await identificar_pessoas_no_frame()
    if nome == 'tocar_musica_spotify':
        if not spotify_service: return 'Spotify não configurado no servidor.'
        termo = argumentos.get('termo', '')
        res = spotify_service.buscar_e_tocar(termo)
        if res.get('sucesso'):
            musica = limpar_ascii(res.get('musica', termo))
            artista = limpar_ascii(res.get('artista', ''))
            await publicar('quarto/legenda', f"Tocando: {musica} - {artista}")
            await publicar('quarto/emocao', 'animado')
            await publicar('quarto/tela', 'cerberus')
            await asyncio.sleep(0.4)
            await publicar_status_spotify()
            return f"Tocando {musica} de {artista} no Spotify."
        return f"Não foi possível tocar no Spotify: {res.get('erro', res.get('mensagem'))}"
    if nome == 'pausar_musica_spotify':
        if not spotify_service: return 'Spotify não configurado no servidor.'
        res = spotify_service.pause()
        await asyncio.sleep(0.3)
        await publicar_status_spotify()
        return "Música pausada no Spotify." if res.get('sucesso') else f"Erro ao pausar: {res.get('erro')}"
    if nome == 'retomar_musica_spotify':
        if not spotify_service: return 'Spotify não configurado no servidor.'
        res = spotify_service.play()
        await asyncio.sleep(0.3)
        await publicar_status_spotify()
        return "Música retomada no Spotify." if res.get('sucesso') else f"Erro ao retomar: {res.get('erro')}"
    if nome == 'proxima_musica_spotify':
        if not spotify_service: return 'Spotify não configurado no servidor.'
        res = spotify_service.proxima()
        await asyncio.sleep(0.4)
        await publicar_status_spotify()
        return "Pulou para a próxima música." if res.get('sucesso') else f"Erro: {res.get('erro')}"
    if nome == 'musica_anterior_spotify':
        if not spotify_service: return 'Spotify não configurado no servidor.'
        res = spotify_service.anterior()
        await asyncio.sleep(0.4)
        await publicar_status_spotify()
        return "Voltou para a música anterior." if res.get('sucesso') else f"Erro ao voltar música: {res.get('erro')}"
    if nome == 'avancar_musica_spotify':
        if not spotify_service: return 'Spotify não configurado no servidor.'
        seg = argumentos.get('segundos', 10)
        res = spotify_service.pular_tempo(seg)
        await asyncio.sleep(0.3)
        await publicar_status_spotify()
        return f"Avançou {seg} segundos na música." if res.get('sucesso') else f"Erro ao avançar: {res.get('erro', res.get('mensagem'))}"
    if nome == 'retroceder_musica_spotify':
        if not spotify_service: return 'Spotify não configurado no servidor.'
        seg = argumentos.get('segundos', 10)
        res = spotify_service.pular_tempo(-seg)
        await asyncio.sleep(0.3)
        await publicar_status_spotify()
        return f"Voltou {seg} segundos na música." if res.get('sucesso') else f"Erro ao retroceder: {res.get('erro', res.get('mensagem'))}"
    if nome == 'ajustar_volume_spotify':
        if not spotify_service: return 'Spotify não configurado no servidor.'
        vol = argumentos.get('volume', 70)
        res = spotify_service.ajustar_volume(vol)
        return f"Volume do Spotify ajustado para {vol}%." if res.get('sucesso') else f"Erro ao ajustar volume: {res.get('erro')}"
    if nome == 'obter_status_musica_spotify':
        if not spotify_service: return 'Spotify não configurado no servidor.'
        dados = spotify_service.obter_tocando_agora()
        if not dados or not dados.get('conectado') or not dados.get('musica'):
            return "Nenhuma música está tocando no momento no Spotify."
        st = "reproduzindo" if dados.get('tocando') else "pausada"
        return f"Está {st} a música '{dados.get('musica')}' do artista '{dados.get('artista')}'."
    if nome == 'mudar_tela_display':
        tela = argumentos.get('tela', 'cerberus').strip().lower()
        await publicar('quarto/tela', tela)
        return f"Tela do display alterada para '{tela}' com sucesso."
    return 'Ferramenta desconhecida.'

async def processar_mensagem(mensagem: str) -> dict:
    """Processa uma mensagem do usuário através do agente Styx (Groq + tools).
    Reutilizada por /api/chat e /api/voz."""
    import json

    # 1. REACAO IMEDIATA: Só altera emoção imediatamente se for provocação/carinho extremo
    emocao_pergunta = inferir_emocao_pergunta(mensagem)
    if emocao_pergunta:
        await publicar('quarto/emocao', emocao_pergunta)
    await publicar('quarto/estado', 'pensando')

    historico = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': mensagem},
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
        # Fallback de Garantia: Se a IA respondeu em texto sem emitir tool_call, mas o usuário pediu para tocar/controlar música
        msg_l = sem_acento(mensagem.lower())
        if any(w in msg_l for w in ['tocar', 'toque', 'toca', 'ouvir', 'coloca', 'coloque', 'solta']):
            termo_busca = mensagem
            for p in ['toque uma musica ', 'toque uma musica', 'toque musica ', 'tocar uma musica ', 'toca uma musica ', 'coloca uma musica ', 'solta uma musica ', 'toque ', 'toca ', 'coloca ']:
                if msg_l.startswith(p):
                    termo_busca = mensagem[len(p):].strip()
                    break
            if not termo_busca or any(x in termo_busca.lower() for x in ['animada', 'boa', 'legal', 'que voce quiser', 'para mim', 'pra mim', 'qualquer']):
                termo_busca = 'Daft Punk Get Lucky'
            print(f"LOG FALLBACK SPOTIFY: Executando tocar_musica_spotify('{termo_busca}')")
            await executar_ferramenta('tocar_musica_spotify', {'termo': termo_busca})
        elif any(w in msg_l for w in ['pausar', 'pausa', 'para a musica', 'para o som']):
            print("LOG FALLBACK SPOTIFY: Executando pausar_musica_spotify")
            await executar_ferramenta('pausar_musica_spotify', {})
        elif any(w in msg_l for w in ['retomar', 'continua a musica', 'despausar']):
            print("LOG FALLBACK SPOTIFY: Executando retomar_musica_spotify")
            await executar_ferramenta('retomar_musica_spotify', {})
        elif any(w in msg_l for w in ['proxima musica', 'passa a musica', 'pula a musica', 'pula essa']):
            print("LOG FALLBACK SPOTIFY: Executando proxima_musica_spotify")
            await executar_ferramenta('proxima_musica_spotify', {})
        elif any(w in msg_l for w in ['musica anterior', 'volta a musica', 'voltar musica']):
            print("LOG FALLBACK SPOTIFY: Executando musica_anterior_spotify")
            await executar_ferramenta('musica_anterior_spotify', {})

    emocao_escolhida, texto_limpo = extrair_segmentos_emocao(bruto)

    # 1. Gera o áudio de fala com voz natural (TTS) para o alto-falante
    global ultimo_audio_fala
    try:
        wav_gerado = await gerar_audio_fala_wav(texto_limpo)
        if wav_gerado:
            ultimo_audio_fala = wav_gerado
            await publicar('quarto/falar_audio', 'http://163.176.173.232:8001/api/audio/fala.wav')
            print(f'LOG TTS: Áudio gerado ({len(wav_gerado)} bytes) e enviado comando MQTT!')
    except Exception as e:
        print(f'LOG TTS ERRO: {e}')

    # 2. Publica a legenda completa limpa (sem tags) no display
    await publicar('quarto/legenda', sem_acento(texto_limpo)[:300])

    # 3. Dispara a fala com a emoção estável e sólida
    asyncio.create_task(animar_discurso_emocoes(emocao_escolhida, texto_limpo))

    return {
        'resposta': texto_limpo,
        'emocao': emocao_escolhida,
        'emocoes': [emocao_escolhida]
    }


@app.post('/api/chat')
async def chat(req: ChatRequest):
    return await processar_mensagem(req.mensagem)


ultimo_audio_fala = bytes()

async def gerar_audio_fala_wav(texto: str) -> bytes:
    """Gera áudio WAV mono 16kHz 16-bit com voz masculina natural e imersiva para o Styx."""
    import subprocess
    import urllib.request
    import urllib.parse
    import httpx

    # 1. Se houver chave do ElevenLabs configurada, usa voz ultra-realista
    elevenlabs_key = os.getenv('ELEVENLABS_API_KEY')
    elevenlabs_voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'pNInz6obpgDQGcFmaJgB') # Adam (Voz masculina profunda e natural)
    if elevenlabs_key:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{elevenlabs_voice_id}"
            headers = {
                "xi-api-key": elevenlabs_key,
                "Content-Type": "application/json"
            }
            payload = {
                "text": texto,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8,
                    "style": 0.2
                }
            }
            async with httpx.AsyncClient(timeout=12) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200 and len(res.content) > 100:
                    p = subprocess.run(
                        ["ffmpeg", "-y", "-i", "pipe:0", "-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1"],
                        input=res.content,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL
                    )
                    if p.stdout and len(p.stdout) > 100:
                        return p.stdout
        except Exception as e:
            print(f"LOG TTS ELEVENLABS AVISO: {e}, usando Edge-TTS neural...")

    # 2. Voz Neural Masculina Profunda (Edge-TTS com tom grave e ritmo natural)
    try:
        import edge_tts
        # pt-BR-AntonioNeural com pitch='-8Hz' dá uma voz masculina encorpada e imponente
        communicate = edge_tts.Communicate(
            texto,
            "pt-BR-AntonioNeural",
            pitch="-8Hz",
            rate="+0%"
        )
        mp3_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_data.extend(chunk["data"])
        
        p = subprocess.run(
            ["ffmpeg", "-y", "-i", "pipe:0", "-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1"],
            input=bytes(mp3_data),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        if p.stdout and len(p.stdout) > 100:
            print(f"LOG TTS: Voz masculina (Edge-TTS Antonio -8Hz) gerada com sucesso! ({len(p.stdout)} bytes)")
            return p.stdout
    except Exception as e:
        print(f"LOG TTS EDGE AVISO: Falha no Edge-TTS ({repr(e)}), tentando fallback Google...")

    # 3. Fallback Google Translate TTS
    try:
        q = urllib.parse.quote(texto[:250])
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={q}&tl=pt-BR&client=tw-ob"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        mp3_data = urllib.request.urlopen(req, timeout=5).read()
        p = subprocess.run(
            ["ffmpeg", "-y", "-i", "pipe:0", "-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1"],
            input=mp3_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        if p.stdout and len(p.stdout) > 100:
            return p.stdout
    except Exception as e:
        print(f"LOG TTS GOOGLE ERRO: {e}")

    return bytes()


@app.get('/api/audio/fala.wav')
def get_audio_fala():
    """Retorna o áudio mais recente gerado para o alto-falante I2S do ESP32."""
    global ultimo_audio_fala
    if not ultimo_audio_fala:
        raise HTTPException(status_code=404, detail="Nenhum áudio gerado ainda.")
    return Response(content=ultimo_audio_fala, media_type="audio/wav")


@app.get('/api/audio/teste.wav')
async def get_audio_teste():
    """Gera e retorna um áudio de teste para validar o alto-falante MAX98357A."""
    frase_teste = "Olá Davi! O meu amplificador e alto-falante estão funcionando perfeitamente!"
    wav = await gerar_audio_fala_wav(frase_teste)
    if not wav:
        raise HTTPException(status_code=500, detail="Erro ao gerar áudio de teste.")
    return Response(content=wav, media_type="audio/wav")


def montar_wav_raw(dados_pcm: bytes, sample_rate: int = 16000, bits: int = 16, canais: int = 1) -> bytes:
    """Monta um arquivo WAV válido a partir de dados PCM brutos (como enviado pelo ESP32)."""
    import struct
    data_size = len(dados_pcm)
    byte_rate = sample_rate * canais * bits // 8
    block_align = canais * bits // 8
    
    header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + data_size,
        b'WAVE',
        b'fmt ',
        16,           # Subchunk1Size
        1,            # AudioFormat (PCM)
        canais,       # NumChannels
        sample_rate,  # SampleRate
        byte_rate,    # ByteRate
        block_align,  # BlockAlign
        bits,         # BitsPerSample
        b'data',
        data_size
    )
    return header + dados_pcm


@app.post('/api/voz')
async def voz(audio: UploadFile = File(...)):
    """Recebe áudio PCM raw do ESP32, transcreve via Groq Whisper e processa com o agente Styx."""
    # 1. Lê o áudio enviado
    conteudo = await audio.read()
    if not conteudo or len(conteudo) < 100:
        await publicar('quarto/legenda', 'Audio muito curto ou vazio')
        return {'status': 'erro', 'detalhe': 'audio_vazio'}

    # 1b. Extrai apenas o PCM bruto se o ESP32 tiver enviado com header WAV
    if conteudo[:4] == b'RIFF' and conteudo[8:12] == b'WAVE':
        pos_data = conteudo.find(b'data')
        conteudo = conteudo[pos_data + 8:] if pos_data > 0 else conteudo[44:]

    # 1c. Análise de volume e Normalização Automática (AGC Inteligente)
    import array
    amostras = array.array('h')
    amostras.frombytes(conteudo)
    
    if len(amostras) > 0:
        pico = max(abs(s) for s in amostras)
        rms = int((sum(s * s for s in amostras) / len(amostras)) ** 0.5)
        print(f'LOG VOZ: Audio recebido: {len(amostras)} amostras ({len(amostras)/16000:.1f}s), Pico={pico}, RMS={rms}')
        
        # Se o áudio tiver voz mas volume baixo, normaliza automaticamente para clareza total
        if 100 < pico < 20000:
            ganho = min(12.0, 24000.0 / max(pico, 1))
            for i in range(len(amostras)):
                v = int(amostras[i] * ganho)
                amostras[i] = max(-32768, min(32767, v))
            print(f'LOG VOZ: Normalizacao aplicada ({ganho:.1f}x). Novo Pico={max(abs(s) for s in amostras)}')
            conteudo = amostras.tobytes()
        elif pico <= 100:
            print('LOG VOZ: Audio detectado como silencio puro (Pico <= 100).')
            await publicar('quarto/estado', 'ocioso')
            return {'status': 'ok', 'transcricao': ''}

    # 2. Monta o WAV válido em memória
    wav_bytes = montar_wav_raw(conteudo)

    # 3. Transcreve via Groq Whisper (whisper-large-v3-turbo)
    try:
        transcricao = await groq_client.audio.transcriptions.create(
            model='whisper-large-v3-turbo',
            # Tupla (nome, conteúdo): o SDK só reconhece o tipo .wav pelo nome do
            # arquivo (BytesIO com .filename era ignorado e o Groq respondia 400).
            file=('audio.wav', wav_bytes),
            language='pt',
            response_format='text',
        )
        texto = transcricao.strip() if transcricao else ''
        print(f'LOG VOZ: Transcricao bruta: "{texto}"')
    except Exception as e:
        print(f'LOG VOZ TRANSCRICAO ERRO: {repr(e)}')
        await publicar('quarto/estado', 'ocioso')
        await publicar('quarto/legenda', 'Nao consegui entender, tenta de novo')
        return {'status': 'erro', 'detalhe': 'transcricao_falhou'}

    # Se a transcricao for vazia ou apenas pontuacao (ex: ".", "!", "?"), ignora
    texto_letras = ''.join(c for c in texto if c.isalnum())
    if not texto_letras or texto.lower() in ['e aí', 'e ai', 'obrigado', 'obrigado.', 'você']:
        # Se o áudio for muito silencioso ou for alucinação típica de silêncio
        print(f'LOG VOZ: Audio sem fala detectada ("{texto}"), retornando ao repouso.')
        await publicar('quarto/estado', 'ocioso')
        return {'status': 'ok', 'transcricao': ''}

    # 4. Processa o texto transcrito com o MESMO agente do /api/chat
    asyncio.create_task(processar_mensagem(texto))

    # 5. Responde imediatamente (a resposta real chega via MQTT)
    return {'status': 'ok', 'transcricao': texto}

if __name__ == '__main__':
    import uvicorn
    port = int(os.getenv('PORT', 8001))
    uvicorn.run("main:app", host='0.0.0.0', port=port)

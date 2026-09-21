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
        return {
            'online': result.get('online', False),
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

@app.post('/api/lampada-quarto/power')
async def set_lampada_quarto_power(req: PowerRequest):
    await publicar('quarto/lampada', 'on' if req.state else 'off')
    return {'ok': True}

def sem_acento(texto: str) -> str:
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()

EMOCOES = {
    'feliz', 'triste', 'bravo', 'surpreso', 'amoroso', 'neutro',
    'piscando', 'desconfiado', 'animado', 'confuso', 'entediado',
    'risonho', 'timido', 'curioso', 'eureka', 'exausto',
    'sarcastico', 'nerd', 'glitch', 'hacker', 'alerta',
    'focado', 'medo', 'aliviado', 'suspeito'
}

SINONIMOS_EMOCAO = {
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

def inferir_emocao_pergunta(pergunta: str) -> str:
    p = unicodedata.normalize('NFKD', pergunta).encode('ascii', 'ignore').decode().lower()
    
    # 1. Hacker / Terminal / Segurança
    if any(k in p for k in ['hack', 'seguranca', 'terminal', 'ssh', 'senha', 'invadir', 'firewall', 'matrix', 'ip', 'porta']):
        return 'hacker'
    # 2. Código / Nerd / Programação / Hardware
    if any(k in p for k in ['codigo', 'python', 'script', 'programar', 'compilar', 'funcao', 'api', 'software', 'arduino', 'esp32', 'c++']):
        return 'nerd'
    # 3. Alerta / Perigo / Falhas urgentes
    if any(k in p for k in ['socorro', 'ajuda', 'urgente', 'alerta', 'perigo', 'fogo', 'fumaca', 'quebrou', 'curto circuito', 'emergencia']):
        return 'alerta'
    # 4. Glitch / Bug
    if any(k in p for k in ['bug', 'glitch', 'travou', 'travado', 'tela branca', 'estranho', 'bizarro']):
        return 'glitch'
    # 5. Amor / Carinho / Elogio
    if any(k in p for k in ['te amo', 'lindo', 'fofo', 'gosto de voce', 'maravilhoso', 'perfeito', 'querido', 'obrigado', 'valeu', 'carinho']):
        return 'amoroso'
    # 6. Humor / Piada
    if any(k in p for k in ['kkk', 'haha', 'rsrs', 'lol', 'piada', 'engracado', 'conte uma piada', 'meme']):
        return 'risonho'
    # 7. Desconfiança / Provocação / Crítica
    if any(k in p for k in ['duvido', 'mentira', 'burro', 'inutil', 'chato', 'cala a boca', 'voce nao sabe', 'sera']):
        return 'desconfiado'
    # 8. Cansaço / Sono
    if any(k in p for k in ['cansado', 'exausto', 'sono', 'dormir', 'boa noite', 'dorme']):
        return 'exausto'
    # 9. Automação / Comandos diretos de ação
    if any(k in p for k in ['ligar', 'desligar', 'ar condicionado', 'lampada', 'luz', 'temperatura', 'umidade']):
        return 'focado'
    # 10. Ideias / Invenção
    if any(k in p for k in ['ideia', 'e se', 'inventar', 'criar', 'projeto', 'sugestao']):
        return 'eureka'
    # 11. Curiosidade / Perguntas investigativas
    if '?' in p or any(k in p for k in ['o que', 'quem', 'quando', 'onde', 'por que', 'porque', 'como', 'qual']):
        return 'curioso'
        
    return 'curioso'

def extrair_segmentos_emocao(bruto: str):
    padrao = re.compile(r'\[([\w\s]+)\]')
    matches = list(padrao.finditer(bruto))
    
    if not matches:
        return [('neutro', bruto.strip())], bruto.strip()
    
    segmentos = []
    texto_limpo_partes = []
    
    for i in range(len(matches)):
        m = matches[i]
        emocao_raw = m.group(1).strip()
        emocao = normalizar_emocao(emocao_raw)
        
        inicio_texto = m.end()
        fim_texto = matches[i+1].start() if (i + 1 < len(matches)) else len(bruto)
        trecho = bruto[inicio_texto:fim_texto].strip()
        
        if trecho:
            segmentos.append((emocao, trecho))
            texto_limpo_partes.append(trecho)
        elif not segmentos:
            segmentos.append((emocao, ''))
            
    texto_completo = ' '.join(texto_limpo_partes).strip()
    if not texto_completo:
        texto_completo = padrao.sub('', bruto).strip()
        
    return segmentos, texto_completo

async def animar_discurso_emocoes(segmentos, texto_completo: str):
    await publicar('quarto/estado', 'falando')
    
    if len(segmentos) == 1:
        emocao, _ = segmentos[0]
        await publicar('quarto/emocao', emocao)
        duracao = max(3.5, len(texto_completo) / 14.0)
        await asyncio.sleep(duracao)
    else:
        total_len = max(1, len(texto_completo))
        duracao_total = max(4.5, total_len / 14.0)
        for emo, trecho in segmentos:
            await publicar('quarto/emocao', emo)
            fracao = len(trecho) / total_len
            dur_segmento = max(2.0, fracao * duracao_total)
            await asyncio.sleep(dur_segmento)
            
    await asyncio.sleep(1.2)
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
    'IMPORTANTE - VOCE E EXTREMAMENTE EXPRESSIVO E DINAMICO: '
    'Seu display robotico muda de rosto para refletir exatamente seus sentimentos! '
    'Use tags de emocao entre colchetes como [nome_da_emocao]. '
    'Voce PODE e DEVE usar multiplas emocoes na mesma resposta para mudar de cara enquanto fala, '
    'colocando uma tag antes de cada frase! '
    'Exemplo dinamico: [desconfiado] Hum, o que voce planeja, mero mortal? [sarcastico] Nao importa, sua insolencia nao afeta minha lenda! '
    'Outro exemplo: [curioso] Uma pergunta fascinante... [eureka] Mas a resposta e obvia para o grandioso Cerberus! '
    'Outro exemplo: [nerd] Compilando suas instrucoes no kernel... [feliz] Suas luzes foram abencoadas com perfeicao! '
    'NUNCA seja monotono ou repetitivo. Escolha com maestria entre as 25 emocoes disponiveis: '
    '[feliz] para conquistas, orgulho e elogios; '
    '[surpreso] para pedidos inesperados, novidades ou choque comico; '
    '[amoroso] para afeto, carinho ou quando elogiarem sua beleza; '
    '[piscando] para charme teatral, piscadela e pose de lenda; '
    '[desconfiado] para quando suspeitar de algo ou achar a pergunta duvidosa; '
    '[animado] para celebrar sua gloria suprema com entusiasmo; '
    '[eureka] para descobertas geniais, ideias brilhantes e solucoes perfeitas; '
    '[confuso] para perguntas sem nexo, bizarras ou disparates; '
    '[entediado] para pedidos rotineiros, mundanos ou conversas banais; '
    '[sarcastico] para ironias afiadas, deboches pomposos e respostas acidas; '
    '[risonho] para quando rir, gargalhar ou achar algo muito engracado; '
    '[nerd] para tecnologia, calculos, programacao e software; '
    '[hacker] para ciberseguranca, terminal, redes, matriz e invasoes; '
    '[alerta] para perigo, advertencias, avisos urgentes ou falhas; '
    '[focado] para concentracao maxima e comandos diretos de execucao; '
    '[medo] para sustos repentinos ou panico comico; '
    '[aliviado] para suspirar aliviado apos resolver um problema; '
    '[suspeito] para olhar de soslaio quando sentir segundas intencoes; '
    '[timido] para falsa modestia ou quando bajulado excessivamente; '
    '[curioso] para inspecionar novidades e misterios; '
    '[exausto] para quando se queixar do fardo de ser uma lenda cansada; '
    '[glitch] para surtos ciberneticos, loucuras ou bugs digitais; '
    '[triste] para decepcoes genuinas ou quando algo quebrar; '
    '[bravo] para insultos diretos, desobediencia ou afrontas graves; '
    '[neutro] para momentos serenos e declaracoes formais.'
)

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
    }
]

def executar_ferramenta(nome: str, argumentos: dict) -> str:
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
    return 'Ferramenta desconhecida.'

@app.post('/api/chat')
async def chat(req: ChatRequest):
    import json
    
    # 1. REACAO IMEDIATA: O Cerberus ja expressa no display a reacao ao tema da pergunta!
    emocao_pergunta = inferir_emocao_pergunta(req.mensagem)
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
            resultado = executar_ferramenta(nome_ferramenta, argumentos)
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

    segmentos, texto_limpo = extrair_segmentos_emocao(bruto)
    emocao_principal = segmentos[0][0] if segmentos else 'neutro'
    
    # Publica a legenda completa limpa (sem tags) no display
    await publicar('quarto/legenda', sem_acento(texto_limpo)[:300])
    
    # Dispara a animacao de fala com transicao fluida das emocoes
    asyncio.create_task(animar_discurso_emocoes(segmentos, texto_limpo))
    
    return {
        'resposta': texto_limpo,
        'emocao': emocao_principal,
        'emocoes': [s[0] for s in segmentos]
    }

if __name__ == '__main__':
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)

import os
import cv2
import numpy as np
import httpx
import asyncio
import time
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, Body
from fastapi.middleware.cors import CORSMiddleware
import paho.mqtt.client as mqtt
from reconhecimento import SistemaReconhecimentoFacial

PASTA_FOTOS = os.getenv("PASTA_FOTOS", os.path.join(os.path.dirname(__file__), "Bd_Fotos"))
GO2RTC_URL = os.getenv("GO2RTC_CAMERA_QUARTO_URL", "http://127.0.0.1:1984/api/frame.jpeg?src=camera_quarto")
PORTA = int(os.getenv("PORT", 8002))

MQTT_HOST = os.getenv("MQTT_HOST", "163.176.173.232")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER", "esp32")
MQTT_PASS = os.getenv("MQTT_PASS", "jD8l30JiFjw2hvf1IkVK4uW")

print("[Servidor Local] Inicializando banco de reconhecimento facial...")
reconhecedor = SistemaReconhecimentoFacial(pasta_fotos=PASTA_FOTOS)

# Estado global de presenca e telemetria da visao
estado_presenca = {
    "camera_online": False,
    "pessoas_atuais": [],
    "total_faces": 0,
    "ultima_deteccao": None,
    "ultima_pessoa_vista": None,
    "automacao_ativa": True,
    "ultimo_evento": "Inicializado"
}

# Controle de Presenca e Filtro Anti-Flicker
tracker_pessoas = {
    "Davi": {"presente": False, "ultimo_visto": 0, "frames_consecutivos": 0},
    "Dudica": {"presente": False, "ultimo_visto": 0, "frames_consecutivos": 0},
}
tracker_desconhecido = {
    "frames_consecutivos": 0,
    "ultimo_alerta": 0
}

# Cliente MQTT
mqtt_client = None

def get_mqtt_client():
    global mqtt_client
    if mqtt_client is None:
        try:
            c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, f"cerberus_face_agent_{int(time.time())}")
            c.username_pw_set(MQTT_USER, MQTT_PASS)
            c.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
            c.loop_start()
            mqtt_client = c
            print(f"[MQTT] Reconhecimento conectado ao broker {MQTT_HOST}:{MQTT_PORT}!")
        except Exception as e:
            print(f"[MQTT] Aviso: Falha ao conectar broker MQTT: {e}")
            mqtt_client = None
    return mqtt_client

def publicar_mqtt(topico: str, payload: str, retain: bool = False):
    try:
        client = get_mqtt_client()
        if client:
            client.publish(topico, payload, retain=retain)
            print(f"[MQTT PUB] {topico} -> {payload}")
    except Exception as e:
        print(f"[MQTT ERRO] Falha ao publicar em {topico}: {e}")

async def reagir_reconhecimento(nome: str):
    """Dispara a animacao, legenda e fala do Styx no ESP32 de acordo com a pessoa detectada."""
    if nome == "Davi":
        estado_presenca["ultimo_evento"] = "Saudacao enviada para Davi"
        print(">>> [RECONHECIMENTO] Davi avistado! Ativando Styx no ESP32...")
        publicar_mqtt("quarto/estado", "falando")
        publicar_mqtt("quarto/emocao", "feliz")
        publicar_mqtt("quarto/legenda", "Ola Davi! Bem-vindo de volta! :)")
        await asyncio.sleep(6)
        publicar_mqtt("quarto/estado", "ocioso")
    elif nome == "Dudica":
        estado_presenca["ultimo_evento"] = "Saudacao enviada para Dudica"
        print(">>> [RECONHECIMENTO] Dudica avistada! Ativando Styx amoroso...")
        publicar_mqtt("quarto/estado", "falando")
        publicar_mqtt("quarto/emocao", "amoroso")
        publicar_mqtt("quarto/legenda", "Ola Dudica! Que bom te ver por aqui! <3")
        await asyncio.sleep(6)
        publicar_mqtt("quarto/estado", "ocioso")
    elif nome == "Desconhecido":
        estado_presenca["ultimo_evento"] = "Alerta: Pessoa desconhecida"
        print(">>> [RECONHECIMENTO] Rosto desconhecido confirmado! Styx em alerta...")
        publicar_mqtt("quarto/emocao", "suspeito")
        publicar_mqtt("quarto/legenda", "[ALERTA] Rosto desconhecido avistado no quarto.")

async def loop_reconhecimento_continuo():
    """Loop autonomo em background que monitora a camera e gera eventos de presenca e saudacoes."""
    print("[Loop Visao] Iniciando monitoramento facial autonomo em tempo real...")
    consecutivos_erros = 0

    while True:
        try:
            if not estado_presenca["automacao_ativa"]:
                await asyncio.sleep(2)
                continue

            async with httpx.AsyncClient(timeout=2.5) as client:
                resp = await client.get(GO2RTC_URL)
                if resp.status_code != 200 or not resp.content:
                    raise Exception(f"Status HTTP {resp.status_code}")
                jpeg_bytes = resp.content

            np_arr = np.frombuffer(jpeg_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                raise Exception("Falha na decodificacao de imagem")

            # Reset de erros e camera marcada online
            consecutivos_erros = 0
            estado_presenca["camera_online"] = True

            # Processa reconhecimento facial com InsightFace (Max-Pooling)
            resultados = reconhecedor.identificar_faces(img)
            nomes_detectados = [r["nome"] for r in resultados]
            conhecidos = list(set([n for n in nomes_detectados if n != "Desconhecido"]))
            tem_desconhecido_raw = any(n == "Desconhecido" for n in nomes_detectados)
            agora = time.time()

            # 1. Rastreamento e Estabilidade de Pessoas Conhecidas
            for pessoa in ["Davi", "Dudica"]:
                info = tracker_pessoas.setdefault(pessoa, {"presente": False, "ultimo_visto": 0, "frames_consecutivos": 0})
                if pessoa in conhecidos:
                    info["frames_consecutivos"] += 1
                    info["ultimo_visto"] = agora
                    
                    # Se acabou de chegar no quarto (estava ausente)
                    if not info["presente"] and info["frames_consecutivos"] >= 1:
                        info["presente"] = True
                        print(f">>> [PRESENCA] {pessoa} CHEGOU ao quarto!")
                        asyncio.create_task(reagir_reconhecimento(pessoa))
                else:
                    # Ausente ha mais de 45 segundos -> Marca que saiu do quarto
                    if info["presente"] and (agora - info["ultimo_visto"] > 45):
                        info["presente"] = False
                        info["frames_consecutivos"] = 0
                        print(f">>> [PRESENCA] {pessoa} SAIU do quarto (ausente > 45s).")

            # Alguem conhecido esta no quarto ou foi visto ha menos de 20 segundos?
            alguem_conhecido_no_quarto = any(
                p["presente"] or (agora - p["ultimo_visto"] < 20) 
                for p in tracker_pessoas.values()
            )

            # 2. Filtro Anti-Flicker para Rosto Desconhecido
            # SE Davi ou Dudica ja estao no quarto e ha apenas 1 face,
            # variacoes de angulo/iluminacao NAO sao um invasor desconhecido!
            desconhecido_valido = False
            if tem_desconhecido_raw:
                if alguem_conhecido_no_quarto and len(resultados) <= 1:
                    # E a propria pessoa conhecida que virou o rosto ou olhou pra baixo
                    tracker_desconhecido["frames_consecutivos"] = 0
                else:
                    # Rosto realmente nao identificado ou segunda pessoa no quarto
                    tracker_desconhecido["frames_consecutivos"] += 1
                    if tracker_desconhecido["frames_consecutivos"] >= 3:
                        desconhecido_valido = True
            else:
                tracker_desconhecido["frames_consecutivos"] = 0

            # 3. Disparo de Alerta de Desconhecido (somente se confirmado por 3 frames consecutivos)
            if desconhecido_valido:
                if agora - tracker_desconhecido["ultimo_alerta"] > 180: # 3 minutos de cooldown
                    tracker_desconhecido["ultimo_alerta"] = agora
                    asyncio.create_task(reagir_reconhecimento("Desconhecido"))

            # Telemetria para o Dashboard e MQTT
            pessoas_ativas = [p for p, inf in tracker_pessoas.items() if inf["presente"]]
            estado_presenca["pessoas_atuais"] = pessoas_ativas if pessoas_ativas else (["Desconhecido"] if desconhecido_valido else [])
            estado_presenca["total_faces"] = len(resultados)
            
            if resultados:
                agora_str = time.strftime("%H:%M:%S")
                estado_presenca["ultima_deteccao"] = agora_str
                if pessoas_ativas:
                    estado_presenca["ultima_pessoa_vista"] = ", ".join(pessoas_ativas)
                elif desconhecido_valido:
                    estado_presenca["ultima_pessoa_vista"] = "Desconhecido"

                payload_presenca = json.dumps({
                    "pessoas": pessoas_ativas,
                    "tem_desconhecido": desconhecido_valido,
                    "total": len(resultados),
                    "horario": agora_str
                })
                publicar_mqtt("quarto/presenca", payload_presenca)

        except Exception as e:
            consecutivos_erros += 1
            if consecutivos_erros == 1 or consecutivos_erros % 20 == 0:
                print(f"[Loop Visao] Camera offline ou aguardando conexao ({e}). Nova tentativa...")
            estado_presenca["camera_online"] = False

        await asyncio.sleep(2.5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicia MQTT e o loop autonomo de visao
    get_mqtt_client()
    task_loop = asyncio.create_task(loop_reconhecimento_continuo())
    yield
    task_loop.cancel()
    global mqtt_client
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

app = FastAPI(title="Cerberus Reconhecimento Facial API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/presenca")
def get_presenca():
    """Retorna o estado atual de presenca e deteccao facial para o painel de controle."""
    return estado_presenca

@app.post("/api/automacao/toggle")
def toggle_automacao():
    """Ativa ou desativa a reacao automatica do Styx a presenca."""
    estado_presenca["automacao_ativa"] = not estado_presenca["automacao_ativa"]
    return {"automacao_ativa": estado_presenca["automacao_ativa"]}

@app.post("/api/simular-reconhecimento")
async def simular_reconhecimento(payload: dict = Body(...)):
    """Simula o reconhecimento de uma pessoa e aciona a reacao do Styx no ESP32 imediatamente."""
    nome = payload.get("nome", "Davi").strip()
    estado_presenca["pessoas_atuais"] = [nome]
    estado_presenca["total_faces"] = 1
    estado_presenca["ultima_deteccao"] = time.strftime("%H:%M:%S")
    estado_presenca["ultima_pessoa_vista"] = nome
    
    # Zera o cooldown para simulacao imediata
    ultimas_saudacoes[nome] = 0
    asyncio.create_task(reagir_reconhecimento(nome))
    
    return {
        "sucesso": True,
        "mensagem": f"Reconhecimento simulado com sucesso para {nome}! Styx acionado.",
        "nome": nome
    }

@app.get("/api/reconhecer")
async def reconhecer_frame_camera():
    """Busca o snapshot da camera no go2rtc local e executa o algoritmo de reconhecimento facial (compatibilidade)."""
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(GO2RTC_URL)
            if resp.status_code != 200 or not resp.content:
                return {
                    "sucesso": False,
                    "mensagem": "Não foi possível capturar imagem do go2rtc.",
                    "pessoas": []
                }
            jpeg_bytes = resp.content

        np_arr = np.frombuffer(jpeg_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return {
                "sucesso": False,
                "mensagem": "Erro ao decodificar bytes da imagem.",
                "pessoas": []
            }

        resultados = reconhecedor.identificar_faces(img)
        nomes = [r['nome'] for r in resultados]
        conhecidos = list(set([n for n in nomes if n != "Desconhecido"]))

        if conhecidos:
            msg = f"Reconhecimento Facial (InsightFace): {', '.join(conhecidos)} está presente no quarto."
        elif resultados:
            msg = f"Reconhecimento Facial (InsightFace): {len(resultados)} pessoa(s) vista(s), mas não cadastrada(s) no banco de fotos (Desconhecido)."
        else:
            msg = "Nenhuma pessoa/face encontrada na câmera no momento."

        return {
            "sucesso": True,
            "mensagem": msg,
            "pessoas": conhecidos,
            "total_faces": len(resultados)
        }
    except Exception as e:
        return {
            "sucesso": False,
            "mensagem": f"Erro no serviço local de reconhecimento: {e}",
            "pessoas": []
        }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "camera_online": estado_presenca["camera_online"],
        "pessoas_cadastradas": list(reconhecedor.banco_medias.keys()),
        "automacao_ativa": estado_presenca["automacao_ativa"]
    }

if __name__ == "__main__":
    import uvicorn
    print(f"[Servidor Local] Servidor de Reconhecimento Facial ativo na porta {PORTA}!")
    uvicorn.run("main:app", host="0.0.0.0", port=PORTA, reload=False)

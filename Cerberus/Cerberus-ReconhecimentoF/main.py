import os
import cv2
import numpy as np
import httpx
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from reconhecimento import SistemaReconhecimentoFacial

app = FastAPI(title="Cerberus Reconhecimento Facial API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PASTA_FOTOS = os.getenv("PASTA_FOTOS", os.path.join(os.path.dirname(__file__), "Bd_Fotos"))
GO2RTC_URL = os.getenv("GO2RTC_CAMERA_QUARTO_URL", "http://127.0.0.1:1984/api/frame.jpeg?src=camera_quarto")
PORTA = int(os.getenv("PORT", 8002))

print("[Servidor Local] Inicializando banco de reconhecimento facial...")
reconhecedor = SistemaReconhecimentoFacial(pasta_fotos=PASTA_FOTOS)

@app.get("/api/reconhecer")
async def reconhecer_frame_camera():
    """Busca o snapshot da câmera no go2rtc local e executa o algoritmo de reconhecimento facial."""
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
        "pessoas_cadastradas": list(reconhecedor.banco_medias.keys())
    }

if __name__ == "__main__":
    import uvicorn
    print(f"[Servidor Local] Servidor de Reconhecimento Facial ativo na porta {PORTA}!")
    uvicorn.run(app, host="0.0.0.0", port=PORTA)

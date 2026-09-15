import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tuya_connector import TuyaOpenAPI

load_dotenv()

ACCESS_ID = os.getenv("TUYA_ACCESS_ID", "gcdk8gx7s93srfwqur4t")
ACCESS_SECRET = os.getenv("TUYA_ACCESS_SECRET", "396e89d4a39a407d810d44b85019b4df")
ENDPOINT = os.getenv("TUYA_ENDPOINT", "https://openapi.tuyaus.com")

DEVICE_LAMPADA_ID = os.getenv("DEVICE_LAMPADA_ID", "eb3788ba5870fa2e95elbe")
DEVICE_TOMADA_AR_ID = os.getenv("DEVICE_TOMADA_AR_ID", "eb1ee375fca62d8c82dh7b")

openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_SECRET)
openapi.connect()

app = FastAPI(title="Cerberus Home API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

def check_tuya_response(response: dict):
    print("LOG TUYA API:", response)
    if not response.get("success", False):
        err_msg = response.get("msg", "Erro desconhecido")
        err_code = response.get("code", 500)
        raise HTTPException(status_code=400, detail=f"Erro Tuya {err_code}: {err_msg}")
    return response

@app.get("/api/lampada/status")
def get_lampada_status():
    res = openapi.get(f"/v1.0/iot-03/devices/{DEVICE_LAMPADA_ID}")
    if res.get("success"):
        result = res.get("result", {})
        return {
            "online": result.get("online", False),
            "name": result.get("name", "Lumi"),
            "status": result.get("status", [])
        }
    return {"online": False, "error": res}

@app.post("/api/lampada/power")
def set_lampada_power(req: PowerRequest):
    commands = [{'code': 'switch_led', 'value': req.state}]
    res = openapi.post(f"/v1.0/iot-03/devices/{DEVICE_LAMPADA_ID}/commands", {'commands': commands})
    return check_tuya_response(res)

@app.post("/api/lampada/white")
def set_lampada_white(req: WhiteRequest):
    commands = [
        {'code': 'work_mode', 'value': 'white'},
        {'code': 'bright_value_v2', 'value': req.bright},
        {'code': 'temp_value_v2', 'value': req.temp}
    ]
    res = openapi.post(f"/v1.0/iot-03/devices/{DEVICE_LAMPADA_ID}/commands", {'commands': commands})
    return check_tuya_response(res)

@app.post("/api/lampada/color")
def set_lampada_color(req: ColorRequest):
    commands = [
        {'code': 'work_mode', 'value': 'colour'},
        {'code': 'colour_data_v2', 'value': {'h': req.h, 's': req.s, 'v': req.v}}
    ]
    res = openapi.post(f"/v1.0/iot-03/devices/{DEVICE_LAMPADA_ID}/commands", {'commands': commands})
    return check_tuya_response(res)

@app.post("/api/lampada/mode")
def set_lampada_mode(req: dict):
    mode = req.get("mode", "white")
    commands = [{'code': 'work_mode', 'value': mode}]
    res = openapi.post(f"/v1.0/iot-03/devices/{DEVICE_LAMPADA_ID}/commands", {'commands': commands})
    return check_tuya_response(res)

@app.get("/api/ar-condicionado/status")
def get_tomada_ar_status():
    res = openapi.get(f"/v1.0/iot-03/devices/{DEVICE_TOMADA_AR_ID}")
    if res.get("success"):
        result = res.get("result", {})
        return {
            "online": result.get("online", False),
            "name": result.get("name", "Lumi ar condicionado"),
            "status": result.get("status", [])
        }
    return {"online": False, "error": res}

@app.post("/api/ar-condicionado/power")
def set_tomada_ar_power(req: PowerRequest):
    commands = [{'code': 'switch_1', 'value': req.state}]
    res = openapi.post(f"/v1.0/iot-03/devices/{DEVICE_TOMADA_AR_ID}/commands", {'commands': commands})
    return check_tuya_response(res)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "ff6012370682453faf646c15e6a491cd")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "8ceb60bbaec84a9fb02a1468a3529108")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
SCOPE = "user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private user-library-read"

CACHE_PATH = os.path.join(os.path.dirname(__file__), ".spotify_cache")

def get_sp_oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=CACHE_PATH
    )

def get_spotify_client():
    sp_oauth = get_sp_oauth()
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        return None
    return spotipy.Spotify(auth=token_info['access_token'])

def obter_tocando_agora():
    """Retorna os dados da musica atualmente em reproducao."""
    try:
        sp = get_spotify_client()
        if not sp:
            return {"conectado": False, "mensagem": "Spotify nao autenticado."}

        atual = sp.current_playback()
        if not atual or not atual.get("item"):
            return {
                "conectado": True,
                "tocando": False,
                "musica": None,
                "artista": None,
                "album": None,
                "capa_url": None,
                "progresso_ms": 0,
                "duracao_ms": 0,
                "dispositivo": None,
                "volume": 0
            }

        item = atual["item"]
        artistas = ", ".join([a["name"] for a in item.get("artists", [])])
        capa_url = None
        if item.get("album") and item["album"].get("images") and len(item["album"]["images"]) > 0:
            capa_url = item["album"]["images"][0]["url"]

        dispositivo = atual.get("device", {}).get("name")
        volume = atual.get("device", {}).get("volume_percent", 50)

        return {
            "conectado": True,
            "tocando": atual.get("is_playing", False),
            "musica": item.get("name"),
            "artista": artistas,
            "album": item.get("album", {}).get("name"),
            "capa_url": capa_url,
            "progresso_ms": atual.get("progress_ms", 0),
            "duracao_ms": item.get("duration_ms", 0),
            "dispositivo": dispositivo,
            "volume": volume
        }
    except Exception as e:
        print(f"[Spotify] Erro ao obter musica atual: {e}")
        return {"conectado": False, "erro": str(e)}

def play():
    """Resume ou inicia a reproducao."""
    try:
        sp = get_spotify_client()
        if sp:
            sp.start_playback()
            return {"sucesso": True, "acao": "play"}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}
    return {"sucesso": False, "mensagem": "Nao autenticado"}

def pause():
    """Pausa a reproducao."""
    try:
        sp = get_spotify_client()
        if sp:
            sp.pause_playback()
            return {"sucesso": True, "acao": "pause"}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}
    return {"sucesso": False, "mensagem": "Nao autenticado"}

def proxima():
    """Avanca para a proxima faixa."""
    try:
        sp = get_spotify_client()
        if sp:
            sp.next_track()
            return {"sucesso": True, "acao": "proxima"}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}
    return {"sucesso": False, "mensagem": "Nao autenticado"}

def anterior():
    """Retorna para a faixa anterior."""
    try:
        sp = get_spotify_client()
        if sp:
            sp.previous_track()
            return {"sucesso": True, "acao": "anterior"}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}
    return {"sucesso": False, "mensagem": "Nao autenticado"}

def ajustar_volume(volume_percent: int):
    """Ajusta o volume do Spotify (0 a 100)."""
    try:
        sp = get_spotify_client()
        if sp:
            v = max(0, min(100, volume_percent))
            sp.volume(v)
            return {"sucesso": True, "volume": v}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}
    return {"sucesso": False, "mensagem": "Nao autenticado"}

def buscar_e_tocar(termo: str):
    """Busca uma musica ou artista no Spotify e inicia a reproducao imediatamente."""
    try:
        sp = get_spotify_client()
        if not sp:
            return {"sucesso": False, "mensagem": "Spotify nao autenticado"}

        resultados = sp.search(q=termo, limit=1, type="track")
        tracks = resultados.get("tracks", {}).get("items", [])
        if not tracks:
            return {"sucesso": False, "mensagem": f"Nenhuma musica encontrada para '{termo}'."}

        track_uri = tracks[0]["uri"]
        nome_musica = tracks[0]["name"]
        artista = tracks[0]["artists"][0]["name"]

        sp.start_playback(uris=[track_uri])
        return {
            "sucesso": True,
            "musica": nome_musica,
            "artista": artista,
            "mensagem": f"Tocando {nome_musica} de {artista}"
        }
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

def listar_dispositivos():
    """Lista os dispositivos disponiveis do Spotify Connect (computador, celular, etc)."""
    try:
        sp = get_spotify_client()
        if sp:
            devs = sp.devices()
            return devs.get("devices", [])
    except Exception as e:
        print(f"[Spotify] Erro ao listar dispositivos: {e}")
    return []

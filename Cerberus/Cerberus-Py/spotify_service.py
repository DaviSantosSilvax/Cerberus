import os
import sys
import time
import subprocess
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "ff6012370682453faf646c15e6a491cd")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "8ceb60bbaec84a9fb02a1468a3529108")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
SCOPE = "user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private user-library-read"

CACHE_PATH = os.path.join(os.path.dirname(__file__), ".spotify_cache")

# Teclas Multimídia Nativas do Windows (apenas para emergências)
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF

def simular_tecla_windows(vk_code: int):
    """Envia evento de tecla multimídia para o Windows."""
    if sys.platform != 'win32':
        return False
    try:
        import ctypes
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        time.sleep(0.04)
        ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
        return True
    except Exception as e:
        print(f"[Spotify Keybd] Erro ao simular tecla: {e}")
        return False

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

def resolver_device_id(sp, preferred_id: str = None):
    """
    Identifica o ID do dispositivo ativo do Spotify Connect.
    Garante que o ID seja válido na lista atual e nunca retorne um ID fantasma/antigo.
    """
    try:
        res = sp.devices()
        devs = res.get("devices", []) if res else []

        # Se não há dispositivos, tenta acordar o app Spotify Desktop no Windows
        if not devs and sys.platform == 'win32':
            try:
                subprocess.Popen(['cmd.exe', '/c', 'start', 'spotify:'], shell=True)
                time.sleep(1.8)
                res = sp.devices()
                devs = res.get("devices", []) if res else []
            except Exception as e_start:
                print(f"[Spotify] Tentativa de acordar app: {e_start}")

        if not devs:
            return None

        # 1. Se o preferred_id foi passado e existe na lista atual, usa ele
        if preferred_id:
            for d in devs:
                if d.get("id") == preferred_id:
                    return d["id"]

        # 2. Dispositivo atualmente ativo
        for d in devs:
            if d.get("is_active"):
                return d["id"]

        # 3. Dispositivo do tipo computador
        for d in devs:
            if d.get("type", "").lower() == "computer":
                return d["id"]

        # 4. Primeiro da lista
        return devs[0].get("id")
    except Exception as e:
        print(f"[Spotify] Erro ao resolver dispositivo: {e}")
        return None

def executar_start_playback(sp, target_dev: str = None, **kwargs) -> bool:
    """
    Inicia a reprodução de forma resiliente:
    1. Tenta no dispositivo especificado se fornecido.
    2. Se falhar, tenta transferir a reprodução ativamente via transfer_playback.
    3. Se falhar, tenta sem device_id (no dispositivo ativo).
    """
    if target_dev:
        try:
            sp.start_playback(device_id=target_dev, **kwargs)
            return True
        except Exception as e1:
            print(f"[Spotify Playback] Falha direta com device_id={target_dev}: {e1}, tentando transfer_playback...")
            try:
                sp.transfer_playback(device_id=target_dev, force_play=True)
                time.sleep(0.4)
                if kwargs:
                    sp.start_playback(device_id=target_dev, **kwargs)
                return True
            except Exception as e_trans:
                print(f"[Spotify Playback] Falha no transfer_playback: {e_trans}")

    try:
        sp.start_playback(**kwargs)
        return True
    except Exception as e2:
        print(f"[Spotify Playback] Falha sem device_id: {e2}")
        return False

def obter_tocando_agora():
    """Retorna os dados da música atualmente em reprodução."""
    try:
        sp = get_spotify_client()
        if not sp:
            return {"conectado": False, "mensagem": "Spotify não autenticado."}

        atual = sp.current_playback()

        if not atual or not atual.get("item"):
            devs = sp.devices().get("devices", [])
            dev_nome = None
            if devs:
                for d in devs:
                    if d.get("is_active"):
                        dev_nome = d["name"]
                        break
                if not dev_nome and devs:
                    dev_nome = devs[0]["name"]

            return {
                "conectado": True,
                "tocando": False,
                "musica": None,
                "artista": None,
                "album": None,
                "capa_url": None,
                "progresso_ms": 0,
                "duracao_ms": 0,
                "dispositivo": dev_nome,
                "volume": 70,
                "is_free": False
            }

        item = atual["item"]
        artistas = ", ".join([a["name"] for a in item.get("artists", [])])
        capa_url = None
        if item.get("album") and item["album"].get("images") and len(item["album"]["images"]) > 0:
            capa_url = item["album"]["images"][0]["url"]

        dispositivo = atual.get("device", {}).get("name")
        volume = atual.get("device", {}).get("volume_percent", 70)

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
            "volume": volume,
            "is_free": False
        }
    except Exception as e:
        print(f"[Spotify] Erro ao obter musica atual: {e}")
        return {"conectado": False, "erro": str(e)}

def play(device_id: str = None):
    """Resume ou inicia a reprodução no Spotify."""
    try:
        sp = get_spotify_client()
        if not sp: return {"sucesso": False, "mensagem": "Não autenticado"}

        target_dev = resolver_device_id(sp, device_id)
        if executar_start_playback(sp, target_dev):
            return {"sucesso": True, "acao": "play"}

        # Se nenhuma chamada da API funcionou, tenta a tecla física do Windows
        simular_tecla_windows(VK_MEDIA_PLAY_PAUSE)
        return {"sucesso": True, "acao": "play_key"}
    except Exception as e:
        print(f"[Spotify play] Erro: {e}")
        return {"sucesso": False, "erro": str(e)}

def pause(device_id: str = None):
    """Pausa a reprodução no Spotify."""
    try:
        sp = get_spotify_client()
        if not sp: return {"sucesso": False, "mensagem": "Não autenticado"}

        target_dev = resolver_device_id(sp, device_id)
        if target_dev:
            try:
                sp.pause_playback(device_id=target_dev)
                return {"sucesso": True, "acao": "pause"}
            except Exception:
                pass
        try:
            sp.pause_playback()
            return {"sucesso": True, "acao": "pause"}
        except Exception:
            pass

        return {"sucesso": True, "acao": "pause"}
    except Exception as e:
        print(f"[Spotify pause] Erro: {e}")
        return {"sucesso": False, "erro": str(e)}

def proxima(device_id: str = None):
    """Avança para a próxima faixa."""
    try:
        sp = get_spotify_client()
        if not sp: return {"sucesso": False, "mensagem": "Não autenticado"}

        target_dev = resolver_device_id(sp, device_id)
        if target_dev:
            try:
                sp.next_track(device_id=target_dev)
                return {"sucesso": True, "acao": "proxima"}
            except Exception:
                pass
        try:
            sp.next_track()
            return {"sucesso": True, "acao": "proxima"}
        except Exception:
            simular_tecla_windows(VK_MEDIA_NEXT_TRACK)

        return {"sucesso": True, "acao": "proxima"}
    except Exception as e:
        print(f"[Spotify proxima] Erro: {e}")
        return {"sucesso": False, "erro": str(e)}

def anterior(device_id: str = None):
    """Retorna para a faixa anterior."""
    try:
        sp = get_spotify_client()
        if not sp: return {"sucesso": False, "mensagem": "Não autenticado"}

        target_dev = resolver_device_id(sp, device_id)
        if target_dev:
            try:
                sp.previous_track(device_id=target_dev)
                return {"sucesso": True, "acao": "anterior"}
            except Exception:
                pass
        try:
            sp.previous_track()
            return {"sucesso": True, "acao": "anterior"}
        except Exception:
            simular_tecla_windows(VK_MEDIA_PREV_TRACK)

        return {"sucesso": True, "acao": "anterior"}
    except Exception as e:
        print(f"[Spotify anterior] Erro: {e}")
        return {"sucesso": False, "erro": str(e)}

def ajustar_volume(volume_percent: int, device_id: str = None):
    """Ajusta o volume do Spotify (0 a 100)."""
    try:
        sp = get_spotify_client()
        if not sp: return {"sucesso": False, "mensagem": "Não autenticado"}
        v = max(0, min(100, int(volume_percent)))
        target_dev = resolver_device_id(sp, device_id)
        if target_dev:
            try:
                sp.volume(v, device_id=target_dev)
                return {"sucesso": True, "volume": v}
            except Exception:
                pass
        try:
            sp.volume(v)
            return {"sucesso": True, "volume": v}
        except Exception:
            pass
        return {"sucesso": True, "volume": v}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

def buscar_e_tocar(termo: str, device_id: str = None):
    """
    Busca inteligentemente músicas, artistas ou playlists no Spotify e toca no dispositivo ativo.
    Suporta termos gerais, nomes de faixas, artistas completos e URIs diretas.
    """
    try:
        sp = get_spotify_client()
        if not sp:
            return {"sucesso": False, "mensagem": "Spotify não autenticado"}

        termo = termo.strip().strip('"').strip("'")
        if not termo:
            return {"sucesso": False, "mensagem": "Termo de busca vazio."}

        target_dev = resolver_device_id(sp, device_id)

        # 1. Se for uma URI direta do Spotify (ex: playlist rápida)
        if termo.startswith("spotify:"):
            tipo_uri = termo.split(":")[1] if len(termo.split(":")) > 1 else ""
            if tipo_uri in ["playlist", "album", "artist"]:
                ok = executar_start_playback(sp, target_dev, context_uri=termo)
            else:
                ok = executar_start_playback(sp, target_dev, uris=[termo])
            return {"sucesso": ok, "mensagem": "Reprodução iniciada!", "uri": termo}

        # 2. Limpeza do termo de busca
        termo_busca = termo
        for prefix in ["tocar ", "toca ", "ouvir ", "coloque ", "colocar ", "play "]:
            if termo_busca.lower().startswith(prefix):
                termo_busca = termo_busca[len(prefix):].strip()

        # Atalhos rápidos de playlists conhecidas
        atalhos_playlists = {
            "lofi": "Lofi 90's Hip Hop",
            "lo-fi": "Lofi 90's Hip Hop",
            "lo fi": "Lofi 90's Hip Hop",
            "synthwave": "Synthwave Cyberpunk",
            "cyberpunk": "Cyberpunk 2077 radio",
            "rock classico": "Rock Classics",
            "rock clássico": "Rock Classics",
            "classic rock": "Rock Classics",
            "foco": "Deep Focus",
            "deep focus": "Deep Focus",
            "deep work": "Deep Focus"
        }
        termo_lower = termo_busca.lower()
        termo_playlist_alias = None
        for k, v in atalhos_playlists.items():
            if k in termo_lower:
                termo_playlist_alias = v
                break

        busca_termo = termo_playlist_alias if termo_playlist_alias else termo_busca
        resultados = sp.search(q=busca_termo, limit=3, type="track,playlist,artist")

        # Prioriza playlist se foi acionada por atalho ou busca de playlist
        playlists = [p for p in resultados.get("playlists", {}).get("items", []) if p]
        if termo_playlist_alias and playlists:
            p = playlists[0]
            p_uri = p["uri"]
            p_nome = p["name"]
            capa = p["images"][0]["url"] if p.get("images") else None
            ok = executar_start_playback(sp, target_dev, context_uri=p_uri)
            if ok:
                return {
                    "sucesso": True,
                    "musica": p_nome,
                    "artista": "Playlist Spotify",
                    "capa_url": capa,
                    "uri": p_uri,
                    "mensagem": f"Tocando playlist {p_nome}!"
                }

        # Prioriza artista se for uma busca por artista (ex: "Djonga", "Queen")
        artists = [a for a in resultados.get("artists", {}).get("items", []) if a]
        if artists and artists[0]["name"].lower() == termo_busca.lower():
            art = artists[0]
            art_uri = art["uri"]
            art_nome = art["name"]
            capa = art["images"][0]["url"] if art.get("images") else None
            ok = executar_start_playback(sp, target_dev, context_uri=art_uri)
            if ok:
                return {
                    "sucesso": True,
                    "musica": f"Top Faixas de {art_nome}",
                    "artista": art_nome,
                    "capa_url": capa,
                    "uri": art_uri,
                    "mensagem": f"Tocando músicas de {art_nome}!"
                }

        # Caso padrão: Toca a melhor faixa encontrada
        tracks = [t for t in resultados.get("tracks", {}).get("items", []) if t]
        if not tracks:
            # Se não encontrou faixas, tenta primeira playlist encontrada
            if playlists:
                p = playlists[0]
                ok = executar_start_playback(sp, target_dev, context_uri=p["uri"])
                if ok:
                    return {
                        "sucesso": True,
                        "musica": p["name"],
                        "artista": "Playlist Spotify",
                        "capa_url": p["images"][0]["url"] if p.get("images") else None,
                        "uri": p["uri"]
                    }
            return {"sucesso": False, "mensagem": f"Nenhuma música ou playlist encontrada para '{termo}'."}

        track_data = tracks[0]
        track_uri = track_data["uri"]
        nome_musica = track_data["name"]
        artista = track_data["artists"][0]["name"]
        album_uri = track_data.get("album", {}).get("uri")
        capa_url = track_data["album"]["images"][0]["url"] if track_data.get("album", {}).get("images") else None

        # Tentativa 1: Tocar via context_uri do álbum com offset da música (mantém fila contínua de reprodução)
        tocado = False
        if album_uri:
            tocado = executar_start_playback(sp, target_dev, context_uri=album_uri, offset={"uri": track_uri})

        # Tentativa 2: Tocar via uris direta
        if not tocado:
            tocado = executar_start_playback(sp, target_dev, uris=[track_uri])

        if not tocado:
            return {
                "sucesso": False,
                "mensagem": "Não foi possível enviar a música para o Spotify. Certifique-se de que o aplicativo do Spotify está aberto no seu PC!"
            }

        return {
            "sucesso": True,
            "musica": nome_musica,
            "artista": artista,
            "capa_url": capa_url,
            "uri": track_uri,
            "mensagem": f"Tocando {nome_musica} de {artista} no Spotify!"
        }
    except Exception as e:
        print(f"[Spotify] Erro crítico ao buscar e tocar: {e}")
        return {"sucesso": False, "erro": str(e)}

def seek(position_ms: int, device_id: str = None):
    """Avança ou retrocede para uma posição específica na música (em milissegundos)."""
    try:
        sp = get_spotify_client()
        if not sp: return {"sucesso": False, "mensagem": "Não autenticado"}
        target_dev = resolver_device_id(sp, device_id)
        pos = max(0, int(position_ms))
        if target_dev:
            try:
                sp.seek_track(pos, device_id=target_dev)
                return {"sucesso": True, "posicao_ms": pos}
            except Exception as e:
                print(f"[Spotify seek] Falha com device_id={target_dev}: {e}")
        try:
            sp.seek_track(pos)
            return {"sucesso": True, "posicao_ms": pos}
        except Exception as e2:
            print(f"[Spotify seek] Falha sem device_id: {e2}")
            return {"sucesso": False, "erro": str(e2)}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

def pular_tempo(segundos: int, device_id: str = None):
    """Avança ou retrocede N segundos na música atual (ex: +10 ou -10)."""
    try:
        sp = get_spotify_client()
        if not sp: return {"sucesso": False, "mensagem": "Não autenticado"}
        atual = sp.current_playback()
        if not atual or "progress_ms" not in atual:
            return {"sucesso": False, "mensagem": "Nenhuma música tocando no momento."}

        progresso_atual = atual.get("progress_ms", 0)
        duracao = atual.get("item", {}).get("duration_ms", 0) if atual.get("item") else 0

        nova_pos = progresso_atual + (segundos * 1000)
        if duracao > 0:
            nova_pos = min(duracao, nova_pos)
        nova_pos = max(0, nova_pos)

        return seek(nova_pos, device_id=device_id)
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

def listar_dispositivos():
    """Lista os dispositivos disponíveis do Spotify Connect."""
    try:
        sp = get_spotify_client()
        if sp:
            devs = sp.devices()
            return devs.get("devices", []) if devs else []
    except Exception as e:
        print(f"[Spotify] Erro ao listar dispositivos: {e}")
    return []

def transferir_reproducao(device_id: str):
    """Transfere a reprodução para um dispositivo específico."""
    try:
        sp = get_spotify_client()
        if sp and device_id:
            sp.transfer_playback(device_id=device_id, force_play=True)
            return {"sucesso": True, "device_id": device_id}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}
    return {"sucesso": False}

import { useState, useEffect, useRef } from "react";
import CerberusBackground from "../assets/CerberusBackground.png";
import SideBar from "../Components/DashBoard/SideBar";
import SideBarMobile from "../Components/DashBoard/SideBarMobile";
import { 
    Music, 
    Play, 
    Pause, 
    SkipBack, 
    SkipForward, 
    RotateCcw,
    RotateCw,
    Volume2, 
    VolumeX, 
    Search, 
    Sparkles, 
    Radio, 
    Laptop, 
    Disc3 
} from "lucide-react";

export default function Musica() {
    const [status, setStatus] = useState<any>({
        conectado: false,
        tocando: false,
        musica: null,
        artista: null,
        album: null,
        capa_url: null,
        progresso_ms: 0,
        duracao_ms: 0,
        dispositivo: null,
        volume: 70
    });

    const [dispositivos, setDispositivos] = useState<any[]>([]);
    const [dispositivoSelecionado, setDispositivoSelecionado] = useState<string>("");
    const [busca, setBusca] = useState<string>("");
    const [buscando, setBuscando] = useState<boolean>(false);
    const [volumeLocal, setVolumeLocal] = useState<number>(70);
    const [mensagemStatus, setMensagemStatus] = useState<string | null>(null);

    const API_CLOUD = `http://${window.location.hostname || "localhost"}:8001/api`;

    // 1. Polling do status do Spotify (a cada 2 segundos quando aberto)
    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const res = await fetch(`${API_CLOUD}/spotify/status`);
                const data = await res.json();
                setStatus(data);
                if (data.volume !== undefined) {
                    setVolumeLocal(data.volume);
                }
            } catch (err) {
                console.error("Erro ao buscar status do Spotify:", err);
            }
        };

        const fetchDispositivos = async () => {
            try {
                const res = await fetch(`${API_CLOUD}/spotify/dispositivos`);
                const data = await res.json();
                if (Array.isArray(data)) {
                    setDispositivos(data);
                    const ativo = data.find((d: any) => d.is_active);
                    const aindaExiste = data.some((d: any) => d.id === dispositivoSelecionado);
                    if (ativo && (!dispositivoSelecionado || !aindaExiste)) {
                        setDispositivoSelecionado(ativo.id);
                    } else if (!aindaExiste && data.length > 0) {
                        setDispositivoSelecionado(data[0].id);
                    }
                }
            } catch (err) {
                console.error("Erro ao buscar dispositivos:", err);
            }
        };

        fetchStatus();
        fetchDispositivos();

        const intStatus = setInterval(fetchStatus, 2500);
        const intDevs = setInterval(fetchDispositivos, 10000);
        return () => {
            clearInterval(intStatus);
            clearInterval(intDevs);
        };
    }, [API_CLOUD, dispositivoSelecionado]);

    // Incremento suave em tempo real a cada 1s quando tocando
    useEffect(() => {
        if (!status.tocando) return;
        const tick = setInterval(() => {
            setStatus((prev: any) => {
                if (!prev.tocando || prev.duracao_ms <= 0) return prev;
                const novo = prev.progresso_ms + 1000;
                return { ...prev, progresso_ms: Math.min(prev.duracao_ms, novo) };
            });
        }, 1000);
        return () => clearInterval(tick);
    }, [status.tocando]);

    // Trocar de dispositivo
    const trocarDispositivo = async (devId: string) => {
        setDispositivoSelecionado(devId);
        try {
            await fetch(`${API_CLOUD}/spotify/transferir`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ device_id: devId }),
            });
        } catch (err) {
            console.error("Erro ao transferir dispositivo:", err);
        }
    };

    // Ações de Reprodução
    const alternarPlayPause = async () => {
        const acao = status.tocando ? "pause" : "play";
        setStatus((prev: any) => ({ ...prev, tocando: !prev.tocando }));
        try {
            await fetch(`${API_CLOUD}/spotify/${acao}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ device_id: dispositivoSelecionado }),
            });
        } catch (err) {
            console.error(err);
        }
    };

    const pularFaixa = async () => {
        try {
            await fetch(`${API_CLOUD}/spotify/proxima`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ device_id: dispositivoSelecionado }),
            });
        } catch (err) {
            console.error(err);
        }
    };

    const voltarFaixa = async () => {
        try {
            await fetch(`${API_CLOUD}/spotify/anterior`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ device_id: dispositivoSelecionado }),
            });
        } catch (err) {
            console.error(err);
        }
    };

    // Pular para posição específica na música (Seek)
    const clicarBarraProgresso = async (e: React.MouseEvent<HTMLDivElement>) => {
        if (!status.duracao_ms || status.duracao_ms <= 0) return;
        const rect = e.currentTarget.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const ratio = Math.max(0, Math.min(1, clickX / rect.width));
        const novaPosicaoMs = Math.round(ratio * status.duracao_ms);

        setStatus((prev: any) => ({ ...prev, progresso_ms: novaPosicaoMs }));

        try {
            await fetch(`${API_CLOUD}/spotify/seek`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    posicao_ms: novaPosicaoMs, 
                    device_id: dispositivoSelecionado || undefined 
                }),
            });
        } catch (err) {
            console.error("Erro ao mudar posição da música:", err);
        }
    };

    // Avançar 10 segundos
    const avancar10s = async () => {
        const novaPos = Math.min(status.duracao_ms || Infinity, (status.progresso_ms || 0) + 10000);
        setStatus((prev: any) => ({ ...prev, progresso_ms: novaPos }));
        try {
            await fetch(`${API_CLOUD}/spotify/avancar`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ segundos: 10, device_id: dispositivoSelecionado || undefined }),
            });
        } catch (err) {
            console.error("Erro ao avançar 10s:", err);
        }
    };

    // Retroceder 10 segundos
    const retroceder10s = async () => {
        const novaPos = Math.max(0, (status.progresso_ms || 0) - 10000);
        setStatus((prev: any) => ({ ...prev, progresso_ms: novaPos }));
        try {
            await fetch(`${API_CLOUD}/spotify/retroceder`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ segundos: 10, device_id: dispositivoSelecionado || undefined }),
            });
        } catch (err) {
            console.error("Erro ao retroceder 10s:", err);
        }
    };

    const timerVolume = useRef<any>(null);
    const mudarVolume = (novoVol: number) => {
        setVolumeLocal(novoVol);
        if (timerVolume.current) clearTimeout(timerVolume.current);
        timerVolume.current = setTimeout(async () => {
            try {
                await fetch(`${API_CLOUD}/spotify/volume`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ volume: novoVol, device_id: dispositivoSelecionado || undefined }),
                });
            } catch (err) {
                console.error("Erro ao ajustar volume:", err);
            }
        }, 250);
    };

    const buscarETocar = async (termo: string) => {
        if (!termo.trim()) return;
        setBuscando(true);
        setMensagemStatus(`Buscando "${termo}" no Spotify...`);
        try {
            const res = await fetch(`${API_CLOUD}/spotify/tocar`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ termo, device_id: dispositivoSelecionado || undefined }),
            });
            const data = await res.json();
            if (data.sucesso) {
                setMensagemStatus(`♫ Tocando: ${data.musica} - ${data.artista}`);
                setStatus((prev: any) => ({
                    ...prev,
                    musica: data.musica,
                    artista: data.artista,
                    capa_url: data.capa_url || prev.capa_url,
                    tocando: true
                }));
                setBusca("");
            } else {
                setMensagemStatus(`Aviso: ${data.erro || data.mensagem || "Não foi possível tocar."}`);
            }
        } catch (err) {
            setMensagemStatus("Erro ao conectar com o serviço do Spotify.");
        }
        setBuscando(false);
        setTimeout(() => setMensagemStatus(null), 5000);
    };

    // Formatador de tempo MM:SS
    const formatarTempo = (ms: number) => {
        const totalSeg = Math.floor(ms / 1000);
        const min = Math.floor(totalSeg / 60);
        const seg = totalSeg % 60;
        return `${min}:${seg < 10 ? "0" : ""}${seg}`;
    };

    const progressoPorcento = status.duracao_ms > 0 
        ? Math.min(100, (status.progresso_ms / status.duracao_ms) * 100) 
        : 0;

    return (
        <div className="relative min-h-screen w-full flex flex-col md:flex-row overflow-x-hidden">
            <img
                src={CerberusBackground}
                alt="Spotify Player"
                className="fixed inset-0 w-full h-full object-cover object-center -z-10"
            />
            <div className="fixed inset-0 bg-black/65 backdrop-blur-[3px] -z-10" />

            <div className="hidden sm:block">
                <SideBar />
            </div>
            <div className="sm:hidden">
                <SideBarMobile />
            </div>

            <div className="relative z-10 flex-1 p-3 sm:p-6 md:p-8 text-white flex flex-col items-center justify-start md:justify-center overflow-y-auto py-6">
                <div className="w-full max-w-4xl backdrop-blur-[6px] bg-[#000b4277] border border-[#0066ff88] shadow-[0_0_35px_rgba(0,183,255,0.2)] rounded-2xl sm:rounded-3xl p-4 sm:p-8 flex flex-col gap-6 sm:gap-8">

                    {/* CABEÇALHO */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#004bbb88] pb-4">
                        <div className="flex flex-col gap-1">
                            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                                <Music className="w-8 h-8 text-[#1ed760] drop-shadow-[0_0_12px_#1ed760]" />
                                <h1 className="text-xl sm:text-4xl font-semibold font-ibm-plex drop-shadow-[0_0_12px_#008cff] text-[#ffffff]">
                                    SPOTIFY MEDIA CENTER
                                </h1>

                                <div className={`mb-1 flex items-center gap-2 px-2.5 py-0.5 sm:px-3 sm:py-1 rounded-xl border text-[10px] sm:text-xs font-rajdhani font-bold uppercase tracking-wider ${
                                    status.conectado
                                        ? "bg-emerald-500/20 border-emerald-400 text-emerald-300 shadow-[0_0_10px_#10b981]"
                                        : "bg-amber-500/20 border-amber-400 text-amber-300"
                                }`}>
                                    <span className="w-2 h-2 rounded-full bg-[#1ed760] animate-pulse" />
                                    <span>{status.conectado ? "SPOTIFY CONNECT (PREMIUM)" : "CONECTANDO"}</span>
                                </div>
                            </div>

                            <p className="font-rajdhani text-[#00b7ffb7] text-xs sm:text-sm tracking-wider uppercase">
                                Controle Remoto • Sincronizado com Styx (ESP32) & IA
                            </p>
                        </div>

                        {/* Seletor de Dispositivo Ativo */}
                        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#091544]/80 border border-[#0066ff55] text-xs font-rajdhani">
                            <Laptop className="w-4 h-4 text-[#1ed760]" />
                            <span className="text-[#a4e2ff]">Tocar em:</span>
                            <select
                                value={dispositivoSelecionado}
                                onChange={(e) => trocarDispositivo(e.target.value)}
                                className="bg-[#0c184d] text-white font-bold font-rajdhani rounded-lg px-2 py-1 border border-[#0077ff]/60 focus:outline-none focus:border-[#1ed760] cursor-pointer text-xs"
                            >
                                {dispositivos.length === 0 ? (
                                    <option value="">Nenhum dispositivo aberto</option>
                                ) : (
                                    dispositivos.map((d: any) => (
                                        <option key={d.id} value={d.id}>
                                            {d.name} {d.is_active ? "● (Ativo)" : ""}
                                        </option>
                                    ))
                                )}
                            </select>
                        </div>
                    </div>

                    {mensagemStatus && (
                        <div className="flex items-center gap-3 p-3 bg-emerald-500/15 border border-emerald-400/40 rounded-xl text-emerald-300 text-xs sm:text-sm font-rajdhani animate-fade-in">
                            <Sparkles className="w-4 h-4 shrink-0 text-[#1ed760]" />
                            <span>{mensagemStatus}</span>
                        </div>
                    )}

                    {/* PLAYER PRINCIPAL */}
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center p-6 sm:p-8 bg-gradient-to-br from-[#0c184d]/90 via-[#0a143f]/80 to-[#050b24]/90 rounded-2xl border border-[#0077ff]/60 shadow-[0_0_25px_rgba(0,119,255,0.15)]">

                        {/* CAPA DO ÁLBUM COM EFEITO DISCO */}
                        <div className="md:col-span-4 flex flex-col items-center justify-center">
                            <div className="relative group">
                                {status.capa_url ? (
                                    <img
                                        src={status.capa_url}
                                        alt={status.musica || "Álbum"}
                                        className={`w-44 h-44 sm:w-52 sm:h-52 object-cover rounded-2xl shadow-[0_0_30px_rgba(30,215,96,0.3)] border-2 border-[#1ed760]/60 transition-all duration-700 ${
                                            status.tocando ? "scale-102" : "opacity-90"
                                        }`}
                                    />
                                ) : (
                                    <div className="w-44 h-44 sm:w-52 sm:h-52 rounded-2xl bg-[#08123b] border-2 border-[#0077ff]/40 flex flex-col items-center justify-center gap-3 text-slate-500">
                                        <Disc3 className={`w-20 h-20 text-[#0077ff]/60 ${status.tocando ? "animate-spin" : ""}`} />
                                        <span className="text-xs font-rajdhani uppercase">Nenhuma faixa ativa</span>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* DETALHES DA MÚSICA & CONTROLES */}
                        <div className="md:col-span-8 flex flex-col gap-4">

                            {/* TÍTULO E ARTISTA */}
                            <div className="flex flex-col gap-1">
                                <h2 className="text-xl sm:text-3xl font-bold font-rajdhani text-white drop-shadow-[0_0_10px_#00e5ff] line-clamp-1">
                                    {status.musica || "Spotify em Pausa"}
                                </h2>
                                <p className="text-sm sm:text-base font-rajdhani text-[#1ed760] font-semibold line-clamp-1">
                                    {status.artista || "Abra o Spotify no seu PC ou celular e dê Play"}
                                </p>
                                {status.album && (
                                    <p className="text-xs font-rajdhani text-cyan-200/60 line-clamp-1">
                                        Álbum: {status.album}
                                    </p>
                                )}
                            </div>

                            {/* BARRA DE PROGRESSO */}
                            {/* BARRA DE PROGRESSO INTERATIVA (CLICÁVEL / SCRUBBER) */}
                            <div className="flex flex-col gap-1.5 pt-2">
                                <div 
                                    onClick={clicarBarraProgresso}
                                    className="group relative w-full h-3 bg-[#091544] rounded-full overflow-visible border border-[#0051d344] cursor-pointer flex items-center hover:border-[#1ed760]/80 transition-colors"
                                    title="Clique para pular para esta parte da música"
                                >
                                    {/* Trilho de Progresso */}
                                    <div className="w-full h-2 rounded-full overflow-hidden relative pointer-events-none">
                                        <div
                                            className="h-full bg-gradient-to-r from-[#00b7ff] to-[#1ed760] rounded-full shadow-[0_0_12px_#1ed760] transition-all duration-150"
                                            style={{ width: `${progressoPorcento}%` }}
                                        />
                                    </div>
                                    
                                    {/* Indicador Scrubber (Dot) */}
                                    <div 
                                        className="absolute w-3.5 h-3.5 bg-white rounded-full border-2 border-[#1ed760] shadow-[0_0_8px_#1ed760] -translate-x-1/2 pointer-events-none opacity-0 group-hover:opacity-100 group-hover:scale-125 transition-all"
                                        style={{ left: `${progressoPorcento}%` }}
                                    />
                                </div>
                                <div className="flex justify-between items-center text-[11px] font-rajdhani text-slate-400 select-none">
                                    <span>{formatarTempo(status.progresso_ms)}</span>
                                    <span className="text-[10px] text-cyan-400/60 uppercase tracking-widest hidden sm:inline">
                                        Clique na barra para mudar de parte
                                    </span>
                                    <span>{formatarTempo(status.duracao_ms)}</span>
                                </div>
                            </div>

                            {/* BOTÕES DE CONTROLE MULTIMÍDIA */}
                            <div className="flex items-center justify-between pt-2">
                                <div className="flex items-center gap-2 sm:gap-3">
                                    {/* VOLTAR FAIXA */}
                                    <button
                                        onClick={voltarFaixa}
                                        className="p-2.5 sm:p-3 rounded-full bg-[#002fff18] border border-[#0077ff]/40 text-cyan-300 hover:scale-110 hover:bg-[#002fff33] transition-all cursor-pointer"
                                        title="Faixa Anterior"
                                    >
                                        <SkipBack className="w-4 h-4 sm:w-5 sm:h-5" />
                                    </button>

                                    {/* RETROCEDER 10s */}
                                    <button
                                        onClick={retroceder10s}
                                        className="relative p-2.5 sm:p-3 rounded-full bg-[#002fff18] border border-[#0077ff]/40 text-cyan-300 hover:border-[#00b7ff] hover:scale-110 hover:bg-[#002fff33] transition-all cursor-pointer flex items-center justify-center group"
                                        title="Voltar 10 segundos"
                                    >
                                        <RotateCcw className="w-4 h-4 sm:w-4.5 sm:h-4.5 text-cyan-300" />
                                        <span className="absolute -bottom-1 text-[9px] font-bold font-rajdhani text-cyan-200 bg-[#061033] px-1 rounded border border-[#0077ff]/60 leading-none">
                                            10
                                        </span>
                                    </button>

                                    {/* PLAY / PAUSE */}
                                    <button
                                        onClick={alternarPlayPause}
                                        className="p-3.5 sm:p-4.5 rounded-full bg-gradient-to-br from-[#1ed760] to-[#00b7ff] text-black hover:scale-108 transition-all cursor-pointer shadow-[0_0_25px_rgba(30,215,96,0.5)] mx-1"
                                        title={status.tocando ? "Pausar" : "Tocar"}
                                    >
                                        {status.tocando ? (
                                            <Pause className="w-6 h-6 sm:w-7 sm:h-7 fill-black" />
                                        ) : (
                                            <Play className="w-6 h-6 sm:w-7 sm:h-7 fill-black ml-0.5" />
                                        )}
                                    </button>

                                    {/* AVANÇAR 10s */}
                                    <button
                                        onClick={avancar10s}
                                        className="relative p-2.5 sm:p-3 rounded-full bg-[#002fff18] border border-[#0077ff]/40 text-cyan-300 hover:border-[#00b7ff] hover:scale-110 hover:bg-[#002fff33] transition-all cursor-pointer flex items-center justify-center group"
                                        title="Avançar 10 segundos"
                                    >
                                        <RotateCw className="w-4 h-4 sm:w-4.5 sm:h-4.5 text-cyan-300" />
                                        <span className="absolute -bottom-1 text-[9px] font-bold font-rajdhani text-cyan-200 bg-[#061033] px-1 rounded border border-[#0077ff]/60 leading-none">
                                            10
                                        </span>
                                    </button>

                                    {/* PRÓXIMA FAIXA */}
                                    <button
                                        onClick={pularFaixa}
                                        className="p-2.5 sm:p-3 rounded-full bg-[#002fff18] border border-[#0077ff]/40 text-cyan-300 hover:scale-110 hover:bg-[#002fff33] transition-all cursor-pointer"
                                        title="Próxima Faixa"
                                    >
                                        <SkipForward className="w-4 h-4 sm:w-5 sm:h-5" />
                                    </button>
                                </div>

                                {/* CONTROLE DE VOLUME */}
                                <div className="flex items-center gap-2 max-w-[160px] w-full">
                                    <button
                                        onClick={() => mudarVolume(volumeLocal === 0 ? 50 : 0)}
                                        className="text-slate-400 hover:text-white transition-all cursor-pointer"
                                    >
                                        {volumeLocal === 0 ? (
                                            <VolumeX className="w-5 h-5 text-rose-400" />
                                        ) : (
                                            <Volume2 className="w-5 h-5 text-cyan-300" />
                                        )}
                                    </button>
                                    <input
                                        type="range"
                                        min="0"
                                        max="100"
                                        value={volumeLocal}
                                        onChange={(e) => mudarVolume(Number(e.target.value))}
                                        className="w-full h-1.5 bg-[#091544] rounded-lg appearance-none cursor-pointer accent-[#1ed760]"
                                    />
                                    <span className="text-xs font-rajdhani text-slate-400 min-w-[28px]">
                                        {volumeLocal}%
                                    </span>
                                </div>
                            </div>

                        </div>
                    </div>

                    {/* BARRA DE PESQUISA RÁPIDA */}
                    <div className="flex flex-col gap-2">
                        <span className="text-xs font-rajdhani text-[#a8e6ff] uppercase tracking-wider flex items-center gap-2">
                            <Search className="w-4 h-4 text-[#00b7ff]" />
                            Tocar Música ou Artista no Spotify:
                        </span>

                        <div className="flex gap-2">
                            <input
                                type="text"
                                placeholder="Digite o nome da música, banda ou álbum (ex: Queen, Linkin Park, Lo-Fi)..."
                                value={busca}
                                onChange={(e) => setBusca(e.target.value)}
                                onKeyDown={(e) => e.key === "Enter" && buscarETocar(busca)}
                                className="flex-1 px-4 py-3 rounded-xl bg-[#091136]/80 border border-[#0066ff66] text-white text-sm font-rajdhani placeholder-slate-500 focus:outline-none focus:border-[#1ed760] transition-all"
                            />
                            <button
                                onClick={() => buscarETocar(busca)}
                                disabled={buscando}
                                className="px-5 py-3 rounded-xl bg-gradient-to-r from-[#0051d3] to-[#1ed760] text-black font-rajdhani font-bold text-sm tracking-wider uppercase cursor-pointer hover:scale-[1.02] transition-all flex items-center gap-2 shadow-[0_0_15px_rgba(30,215,96,0.3)]"
                            >
                                <Sparkles className="w-4 h-4" />
                                <span>{buscando ? "Tocando..." : "Tocar"}</span>
                            </button>
                        </div>
                    </div>

                    {/* ATALHOS RÁPIDOS DE PLAYLISTS E GÊNEROS */}
                    <div className="flex flex-col gap-2 pt-2">
                        <span className="text-xs font-rajdhani text-[#a8e6ff] uppercase tracking-wider flex items-center gap-2">
                            <Radio className="w-4 h-4 text-[#1ed760]" />
                            Atalhos Rápidos de Estudo e Foco:
                        </span>

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            {[
                                { nome: "Lo-Fi Beats", termo: "Lofi Beats" },
                                { nome: "Synthwave Cyberpunk", termo: "Synthwave" },
                                { nome: "Rock Clássico", termo: "Rock Classico" },
                                { nome: "Deep Work / Foco", termo: "Deep Focus" },
                            ].map((p, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => buscarETocar(p.termo)}
                                    className="p-3 rounded-xl bg-[#091136]/70 border border-[#0066ff44] hover:border-[#1ed760] hover:bg-[#1ed760]/10 text-white font-rajdhani text-xs font-semibold tracking-wider transition-all cursor-pointer flex items-center justify-between"
                                >
                                    <span>{p.nome}</span>
                                    <Play className="w-3.5 h-3.5 text-[#1ed760]" />
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* NOTA DE INTEGRAÇÃO COM ESP32 */}
                    <div className="p-3.5 bg-[#091136]/60 border border-[#0066ff44] rounded-xl flex items-center gap-3 text-xs font-rajdhani text-slate-300">
                        <Sparkles className="w-5 h-5 text-[#00b7ff] shrink-0" />
                        <span>
                            <strong>Integração com Styx (ESP32):</strong> Ao tocar uma música, o Styx exibe o nome da faixa na tela de legenda e ativa a expressão animada no visor LCD!
                        </span>
                    </div>

                </div>
            </div>
        </div>
    );
}

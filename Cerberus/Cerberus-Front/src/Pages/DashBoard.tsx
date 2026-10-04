import { useState, useEffect } from "react";
import backgroundCerberus from "../assets/CerberusBackground.png";
import SideBar from "../Components/DashBoard/SideBar";
import SideBarMobile from "../Components/DashBoard/SideBarMobile";
import { 
    Thermometer, 
    Droplets, 
    Lightbulb, 
    Snowflake, 
    Bot, 
    UserCheck, 
    UserX, 
    Eye, 
    Sparkles, 
    Heart, 
    Power, 
    Activity, 
    ArrowRight 
} from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function DashBoard() {
    const navigate = useNavigate();

    // Estados do Clima e Dispositivos (Cloud Backend)
    const [temp, setTemp] = useState<number | null>(null);
    const [umid, setUmid] = useState<number | null>(null);
    const [lampada, setLampada] = useState<string>("off");
    const [ar, setAr] = useState<string>("off");

    // Estados do Reconhecimento Facial (Local API 8002)
    const [presenca, setPresenca] = useState<any>({
        camera_online: false,
        pessoas_atuais: [],
        total_faces: 0,
        ultima_pessoa_vista: null,
        ultima_deteccao: null,
        automacao_ativa: true
    });
    const [simulando, setSimulando] = useState<string | null>(null);

    const API_CLOUD = import.meta.env.VITE_BACKEND_URL || `http://${window.location.hostname}:8001/api`;
    const API_RECONHECIMENTO = "http://127.0.0.1:8002/api";

    // 1. Polling de status do quarto (DHT22 e Tuya)
    useEffect(() => {
        const fetchQuarto = async () => {
            try {
                const res = await fetch(`${API_CLOUD}/dashboard/quarto`);
                const data = await res.json();
                if (data.temperatura !== undefined) setTemp(data.temperatura);
                if (data.umidade !== undefined) setUmid(data.umidade);
                if (data.lampada !== undefined) setLampada(data.lampada);
                if (data.ar !== undefined) setAr(data.ar);
            } catch (err) {
                console.error("Erro ao buscar dados do quarto:", err);
            }
        };

        fetchQuarto();
        const intQuarto = setInterval(fetchQuarto, 4000);
        return () => clearInterval(intQuarto);
    }, [API_CLOUD]);

    // 2. Polling de status da visão computacional / reconhecimento facial
    useEffect(() => {
        const fetchPresenca = async () => {
            try {
                const res = await fetch(`${API_RECONHECIMENTO}/presenca`);
                const data = await res.json();
                setPresenca(data);
            } catch (err) {
                // Reconhecimento local pode estar ocupado ou iniciando
            }
        };

        fetchPresenca();
        const intPresenca = setInterval(fetchPresenca, 3000);
        return () => clearInterval(intPresenca);
    }, []);

    // Ações de Dispositivos
    const toggleLampada = async () => {
        const novo = lampada === "on" ? false : true;
        setLampada(novo ? "on" : "off");
        try {
            await fetch(`${API_CLOUD}/lampada/power`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ state: novo }),
            });
        } catch (err) {
            console.error("Erro ao alternar lâmpada:", err);
        }
    };

    const toggleAr = async () => {
        const novo = ar === "on" ? false : true;
        setAr(novo ? "on" : "off");
        try {
            await fetch(`${API_CLOUD}/ar-condicionado/power`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ state: novo }),
            });
        } catch (err) {
            console.error("Erro ao alternar ar-condicionado:", err);
        }
    };

    // Ação: Simular Saudação / Reconhecimento no ESP32
    const dispararSaudacao = async (nome: string) => {
        setSimulando(nome);
        try {
            await fetch(`${API_RECONHECIMENTO}/simular-reconhecimento`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ nome }),
            });
        } catch (err) {
            console.error("Erro ao simular reconhecimento:", err);
        }
        setTimeout(() => setSimulando(null), 3000);
    };

    return (
        <div
            className="relative min-h-screen w-full flex flex-col md:flex-row bg-cover bg-center overflow-x-hidden"
            style={{ backgroundImage: `url(${backgroundCerberus})` }}
        >
            <div className="fixed inset-0 bg-black/65 backdrop-blur-[3px] -z-10" />

            <div className="hidden sm:block">
                <SideBar />
            </div>
            <div className="sm:hidden">
                <SideBarMobile />
            </div>

            <div className="flex-1 p-4 sm:p-8 flex flex-col justify-start items-center text-white overflow-y-auto">
                <div className="w-full max-w-5xl flex flex-col gap-6">

                    {/* CABEÇALHO DO DASHBOARD */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 sm:p-6 backdrop-blur-[6px] bg-[#000b4277] border border-[#0066ff88] rounded-2xl sm:rounded-3xl shadow-[0_0_25px_rgba(0,119,255,0.2)]">
                        <div>
                            <div className="flex items-center gap-3">
                                <Sparkles className="w-7 h-7 text-[#00b7ff] drop-shadow-[0_0_10px_#00b7ff]" />
                                <h1 className="text-2xl sm:text-4xl font-bold font-zen-dots drop-shadow-[0_0_15px_#6085ff] text-white">
                                    CERBERUS COMMAND
                                </h1>
                            </div>
                            <p className="font-rajdhani text-cyan-200/80 text-xs sm:text-sm mt-1 uppercase tracking-wider">
                                Central de Automação, Visão Computacional e Inteligência Artificial
                            </p>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-500/20 border border-emerald-400 text-emerald-300 text-xs font-rajdhani font-bold tracking-widest uppercase shadow-[0_0_10px_#10b98144]">
                                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                                SISTEMA OPERACIONAL
                            </span>
                        </div>
                    </div>

                    {/* GRID PRINCIPAL DE WIDGETS */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                        {/* WIDGET 1: CLIMA DO QUARTO (DHT22 ESP32) */}
                        <div className="p-5 sm:p-6 backdrop-blur-[6px] bg-[#000b4266] border border-[#0066ff66] rounded-2xl shadow-[0_0_20px_rgba(0,119,255,0.1)] flex flex-col justify-between gap-4">
                            <div className="flex items-center justify-between border-b border-[#004bbb55] pb-3">
                                <div className="flex items-center gap-2.5">
                                    <Thermometer className="w-6 h-6 text-[#ff8c42] drop-shadow-[0_0_8px_#ff8c42]" />
                                    <div>
                                        <h3 className="font-ibm-plex font-bold text-base sm:text-lg text-white">CLIMA NO QUARTO</h3>
                                        <p className="text-[11px] font-rajdhani text-cyan-300/70 uppercase">Sensor DHT22 • ESP32 (GPIO 4)</p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => navigate("/climatizacao")}
                                    className="p-1.5 hover:bg-cyan-500/20 rounded-lg text-cyan-300 transition-all cursor-pointer"
                                    title="Ir para Climatização"
                                >
                                    <ArrowRight className="w-5 h-5" />
                                </button>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                {/* TEMPERATURA */}
                                <div className="p-4 bg-[#08123b]/80 border border-[#0066ff44] rounded-xl flex flex-col gap-1">
                                    <span className="text-xs font-rajdhani text-[#a8e6ff] uppercase tracking-wider">Temperatura</span>
                                    <div className="flex items-baseline gap-1.5">
                                        <span className="text-3xl sm:text-4xl font-bold font-rajdhani text-white drop-shadow-[0_0_10px_#ff8c42]">
                                            {temp !== null ? temp.toFixed(1) : "--"}
                                        </span>
                                        <span className="text-lg font-semibold text-[#ff8c42]">°C</span>
                                    </div>
                                    <span className="text-[11px] font-rajdhani text-emerald-400 font-semibold mt-1">
                                        ● {temp !== null && temp <= 26 ? "Agradável" : "Clima do Quarto"}
                                    </span>
                                </div>

                                {/* UMIDADE */}
                                <div className="p-4 bg-[#08123b]/80 border border-[#0066ff44] rounded-xl flex flex-col gap-1">
                                    <span className="text-xs font-rajdhani text-[#a8e6ff] uppercase tracking-wider flex items-center gap-1.5">
                                        <Droplets className="w-3.5 h-3.5 text-[#00e5ff]" />
                                        Umidade
                                    </span>
                                    <div className="flex items-baseline gap-1.5">
                                        <span className="text-3xl sm:text-4xl font-bold font-rajdhani text-white drop-shadow-[0_0_10px_#00e5ff]">
                                            {umid !== null ? umid.toFixed(0) : "--"}
                                        </span>
                                        <span className="text-lg font-semibold text-[#00e5ff]">%</span>
                                    </div>
                                    <span className="text-[11px] font-rajdhani text-cyan-300 font-semibold mt-1">
                                        ● {umid !== null && umid >= 40 && umid <= 70 ? "Faixa Confortável" : "Umidade Relativa"}
                                    </span>
                                </div>
                            </div>

                            <div className="flex items-center justify-between pt-2 border-t border-[#004bbb44] text-xs font-rajdhani text-slate-300">
                                <span className="flex items-center gap-1.5">
                                    <Activity className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
                                    Leituras ao vivo a cada 30s
                                </span>
                                <span className="text-[#00e5ff] font-semibold">Exibido também no Styx</span>
                            </div>
                        </div>

                        {/* WIDGET 2: RECONHECIMENTO FACIAL E PRESENÇA (INSIGHTFACE) */}
                        <div className="p-5 sm:p-6 backdrop-blur-[6px] bg-[#000b4266] border border-[#0066ff66] rounded-2xl shadow-[0_0_20px_rgba(0,119,255,0.1)] flex flex-col justify-between gap-4">
                            <div className="flex items-center justify-between border-b border-[#004bbb55] pb-3">
                                <div className="flex items-center gap-2.5">
                                    <Eye className="w-6 h-6 text-[#00e5ff] drop-shadow-[0_0_8px_#00e5ff]" />
                                    <div>
                                        <h3 className="font-ibm-plex font-bold text-base sm:text-lg text-white">VISÃO & PRESENÇA</h3>
                                        <p className="text-[11px] font-rajdhani text-cyan-300/70 uppercase">InsightFace • Câmera do Quarto</p>
                                    </div>
                                </div>
                                <span className={`text-[10px] font-rajdhani font-bold px-2.5 py-0.5 rounded-full border ${
                                    presenca.camera_online 
                                        ? "bg-emerald-500/20 border-emerald-400 text-emerald-300" 
                                        : "bg-amber-500/20 border-amber-400 text-amber-300"
                                }`}>
                                    {presenca.camera_online ? "CÂMERA ATIVA" : "AGUARDANDO STREAM"}
                                </span>
                            </div>

                            <div className="p-4 bg-[#08123b]/80 border border-[#0066ff44] rounded-xl flex flex-col gap-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs font-rajdhani text-[#a8e6ff] uppercase tracking-wider">Identificação Atual:</span>
                                    <span className="text-xs font-rajdhani text-slate-400">
                                        Última detecção: {presenca.ultima_deteccao || "--:--"}
                                    </span>
                                </div>

                                <div className="flex items-center gap-3">
                                    {presenca.pessoas_atuais && presenca.pessoas_atuais.length > 0 ? (
                                        <div className="flex items-center gap-2 text-emerald-300 font-bold font-rajdhani text-lg">
                                            <UserCheck className="w-5 h-5 text-emerald-400" />
                                            <span>{presenca.pessoas_atuais.join(", ")} presente(s)</span>
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2 text-slate-400 font-rajdhani text-base">
                                            <UserX className="w-5 h-5 text-slate-500" />
                                            <span>Nenhuma pessoa em frente à câmera</span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* BOTÕES DE SAUDAÇÃO / SIMULAÇÃO */}
                            <div className="flex flex-col gap-1.5 pt-1">
                                <span className="text-[11px] font-rajdhani text-[#a8e6ff] uppercase tracking-wider">
                                    Testar Reação Facial no Styx (ESP32):
                                </span>
                                <div className="grid grid-cols-2 gap-2">
                                    <button
                                        onClick={() => dispararSaudacao("Davi")}
                                        disabled={simulando !== null}
                                        className={`px-3 py-2 rounded-xl border text-xs font-rajdhani font-bold uppercase tracking-wider cursor-pointer transition-all flex items-center justify-center gap-1.5 ${
                                            simulando === "Davi"
                                                ? "bg-emerald-500 border-emerald-300 text-white shadow-[0_0_15px_#10b981]"
                                                : "bg-[#002fff22] border-[#0077ff] text-[#64c6ff] hover:bg-[#002fff44]"
                                        }`}
                                    >
                                        <UserCheck className="w-4 h-4" />
                                        <span>{simulando === "Davi" ? "Enviado!" : "Saudar Davi"}</span>
                                    </button>

                                    <button
                                        onClick={() => dispararSaudacao("Dudica")}
                                        disabled={simulando !== null}
                                        className={`px-3 py-2 rounded-xl border text-xs font-rajdhani font-bold uppercase tracking-wider cursor-pointer transition-all flex items-center justify-center gap-1.5 ${
                                            simulando === "Dudica"
                                                ? "bg-pink-500 border-pink-300 text-white shadow-[0_0_15px_#ec4899]"
                                                : "bg-pink-500/15 border-pink-500/50 text-pink-300 hover:bg-pink-500/30"
                                        }`}
                                    >
                                        <Heart className="w-4 h-4" />
                                        <span>{simulando === "Dudica" ? "Enviado!" : "Saudar Dudica"}</span>
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* WIDGET 3: CONTROLES RÁPIDOS TUYA (LÂMPADA & AR) */}
                        <div className="p-5 sm:p-6 backdrop-blur-[6px] bg-[#000b4266] border border-[#0066ff66] rounded-2xl shadow-[0_0_20px_rgba(0,119,255,0.1)] flex flex-col justify-between gap-4">
                            <div className="flex items-center justify-between border-b border-[#004bbb55] pb-3">
                                <div className="flex items-center gap-2.5">
                                    <Power className="w-6 h-6 text-[#0077ff] drop-shadow-[0_0_8px_#0077ff]" />
                                    <div>
                                        <h3 className="font-ibm-plex font-bold text-base sm:text-lg text-white">CONTROLE RÁPIDO</h3>
                                        <p className="text-[11px] font-rajdhani text-cyan-300/70 uppercase">Dispositivos Inteligentes Tuya</p>
                                    </div>
                                </div>
                                <span className="text-[11px] font-rajdhani text-[#64c6ff]">
                                    Sincronizado via MQTT
                                </span>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                {/* BOTÃO LÂMPADA */}
                                <button
                                    onClick={toggleLampada}
                                    className={`p-4 rounded-xl border transition-all duration-300 flex flex-col items-center justify-center gap-2 cursor-pointer ${
                                        lampada === "on"
                                            ? "bg-[#002fff2a] border-[#00e5ff] text-[#00e5ff] shadow-[0_0_15px_rgba(0,229,255,0.3)]"
                                            : "bg-slate-800/40 border-slate-600/60 text-slate-400 hover:border-slate-400"
                                    }`}
                                >
                                    <Lightbulb className={`w-8 h-8 ${lampada === "on" ? "text-amber-300 drop-shadow-[0_0_10px_#fde047]" : "text-slate-500"}`} />
                                    <span className="font-rajdhani font-bold text-sm tracking-wider uppercase">
                                        Lâmpada {lampada === "on" ? "Ligada" : "Desligada"}
                                    </span>
                                </button>

                                {/* BOTÃO AR */}
                                <button
                                    onClick={toggleAr}
                                    className={`p-4 rounded-xl border transition-all duration-300 flex flex-col items-center justify-center gap-2 cursor-pointer ${
                                        ar === "on"
                                            ? "bg-[#002fff2a] border-[#0077ff] text-[#0077ff] shadow-[0_0_15px_rgba(0,119,255,0.3)]"
                                            : "bg-slate-800/40 border-slate-600/60 text-slate-400 hover:border-slate-400"
                                    }`}
                                >
                                    <Snowflake className={`w-8 h-8 ${ar === "on" ? "text-cyan-300 drop-shadow-[0_0_10px_#67e8f9]" : "text-slate-500"}`} />
                                    <span className="font-rajdhani font-bold text-sm tracking-wider uppercase">
                                        Ar {ar === "on" ? "Ligado" : "Desligado"}
                                    </span>
                                </button>
                            </div>

                            <div className="flex items-center justify-between text-xs font-rajdhani text-slate-300 pt-2 border-t border-[#004bbb44]">
                                <span>Alterne instantaneamente</span>
                                <span className="text-[#a8e6ff]">Reflete na tela Home do ESP32</span>
                            </div>
                        </div>

                        {/* WIDGET 4: MASCOTE STYX & IA */}
                        <div className="p-5 sm:p-6 backdrop-blur-[6px] bg-[#000b4266] border border-[#0066ff66] rounded-2xl shadow-[0_0_20px_rgba(0,119,255,0.1)] flex flex-col justify-between gap-4">
                            <div className="flex items-center justify-between border-b border-[#004bbb55] pb-3">
                                <div className="flex items-center gap-2.5">
                                    <Bot className="w-6 h-6 text-[#ff5588] drop-shadow-[0_0_8px_#ff5588]" />
                                    <div>
                                        <h3 className="font-ibm-plex font-bold text-base sm:text-lg text-white">MASCOTE STYX</h3>
                                        <p className="text-[11px] font-rajdhani text-cyan-300/70 uppercase">Display LCD TFT • 26 Emoções</p>
                                    </div>
                                </div>
                                <span className="text-[10px] font-rajdhani font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-400 text-emerald-300">
                                    ONLINE
                                </span>
                            </div>

                            <div className="flex items-center gap-4 p-3.5 bg-[#08123b]/80 border border-[#0066ff44] rounded-xl">
                                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#0051d3] to-[#ff5588]/40 flex items-center justify-center border border-[#00b7ff]">
                                    <Bot className="w-7 h-7 text-white drop-shadow-[0_0_8px_#ffffff]" />
                                </div>
                                <div>
                                    <h4 className="font-rajdhani font-bold text-white text-base">Styx Companheiro</h4>
                                    <p className="font-rajdhani text-xs text-cyan-300/80">
                                        Exibindo rosto animado, legendas e comandos touch
                                    </p>
                                </div>
                            </div>

                            <div className="flex items-center justify-between gap-3 pt-1">
                                <button
                                    onClick={() => navigate("/cerberus")}
                                    className="flex-1 py-2.5 px-4 rounded-xl bg-gradient-to-r from-[#0051d3] to-[#002fff] text-white font-rajdhani font-bold text-sm tracking-wider uppercase border border-[#00b7ff] shadow-[0_0_15px_rgba(0,183,255,0.25)] hover:scale-[1.02] transition-all cursor-pointer flex items-center justify-center gap-2"
                                >
                                    <Bot className="w-4 h-4" />
                                    <span>Conversar com a IA</span>
                                </button>
                            </div>
                        </div>

                    </div>

                </div>
            </div>
        </div>
    );
}
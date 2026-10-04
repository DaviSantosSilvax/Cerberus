import { useState, useEffect } from "react";
import CerberusBackground from "../assets/CerberusBackground.png";
import SideBar from "../Components/DashBoard/SideBar";
import { Power, Zap, Timer, AlertCircle, Wifi, WifiOff, Snowflake, Thermometer, Droplets, Activity } from "lucide-react";
import SideBarMobile from "../Components/DashBoard/SideBarMobile";

export default function Climatizacao() {
    const [power, setPower] = useState<boolean>(false);
    const [isOnline, setIsOnline] = useState<boolean | null>(null);
    const [temp, setTemp] = useState<number | null>(null);
    const [umid, setUmid] = useState<number | null>(null);
    const [sensorAtivo, setSensorAtivo] = useState<boolean>(false);
    const [ultimaAtualizacao, setUltimaAtualizacao] = useState<string>("--:--");

    const API_BASE = import.meta.env.VITE_BACKEND_URL || `http://${window.location.hostname}:8001/api`;
    const BACKEND_URL = `${API_BASE}/ar-condicionado`;

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                // 1. Busca status da tomada Tuya do Ar
                const resAr = await fetch(`${BACKEND_URL}/status`);
                const dataAr = await resAr.json();
                if (dataAr.online !== undefined) {
                    setIsOnline(dataAr.online);
                }
                if (dataAr.status && Array.isArray(dataAr.status)) {
                    const switchItem = dataAr.status.find((s: any) => s.code === "switch_1");
                    if (switchItem !== undefined) {
                        setPower(Boolean(switchItem.value));
                    }
                }
            } catch (err) {
                console.error("Erro ao buscar status do ar:", err);
                setIsOnline(false);
            }

            try {
                // 2. Busca temperatura e umidade em tempo real vindas do ESP32 (DHT22 via MQTT)
                const resQuarto = await fetch(`${API_BASE}/dashboard/quarto`);
                const dataQuarto = await resQuarto.json();
                if (dataQuarto.temperatura !== undefined && dataQuarto.temperatura !== null) {
                    setTemp(dataQuarto.temperatura);
                    setSensorAtivo(true);
                }
                if (dataQuarto.umidade !== undefined && dataQuarto.umidade !== null) {
                    setUmid(dataQuarto.umidade);
                }
                const agora = new Date();
                setUltimaAtualizacao(agora.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
            } catch (err) {
                console.error("Erro ao buscar clima do quarto:", err);
            }
        };

        fetchStatus();
        const interval = setInterval(fetchStatus, 5000);
        return () => clearInterval(interval);
    }, [API_BASE, BACKEND_URL]);

    const togglePower = async () => {
        const nextState = !power;
        setPower(nextState);
        try {
            await fetch(`${BACKEND_URL}/power`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ state: nextState }),
            });
        } catch (err) {
            console.error("Erro ao alternar energia do ar:", err);
        }
    };

    const getStatusTemp = (t: number | null) => {
        if (t === null) return { texto: "Aguardando leitura...", cor: "text-slate-400" };
        if (t < 20) return { texto: "Ambiente Fresco / Frio", cor: "text-blue-400" };
        if (t <= 26) return { texto: "Temperatura Agradável / Ideal", cor: "text-emerald-400" };
        return { texto: "Ambiente Aquecido", cor: "text-amber-400" };
    };

    const getStatusUmid = (u: number | null) => {
        if (u === null) return { texto: "Aguardando leitura...", cor: "text-slate-400" };
        if (u < 40) return { texto: "Ar Seco (Hidrate-se)", cor: "text-amber-400" };
        if (u <= 70) return { texto: "Faixa Ideal de Umidade", cor: "text-cyan-400" };
        return { texto: "Umidade Elevada", cor: "text-indigo-400" };
    };

    const statusTemp = getStatusTemp(temp);
    const statusUmid = getStatusUmid(umid);

    return (
        <div className="relative min-h-screen w-full flex flex-col md:flex-row overflow-x-hidden">
            <img
                src={CerberusBackground}
                alt="Climatização"
                className="fixed inset-0 w-full h-full object-cover object-center -z-10"
            />
            <div className="fixed inset-0 bg-black/60 backdrop-blur-[2px] -z-10" />

            <div className="hidden sm:block">
                <SideBar />
            </div>
            <div className="sm:hidden">
                <SideBarMobile />
            </div>

            <div className="relative z-10 flex-1 p-3 sm:p-6 md:p-8 text-white flex flex-col items-center justify-start md:justify-center overflow-y-auto py-6">
                <div className="w-full max-w-4xl backdrop-blur-[6px] bg-[#000b426e] border border-[#0066ff8c] shadow-[0_0_35px_rgba(0,183,255,0.2)] rounded-2xl sm:rounded-3xl p-4 sm:p-8 flex flex-col gap-6 sm:gap-8">

                    {/* CABEÇALHO */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#004bbb8c] pb-4">
                        <div className="flex flex-col gap-1">
                            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                                <Snowflake className="w-9 h-9 text-[#39a6ff] drop-shadow-[1px_1px_12px_#39a6ff]" />
                                <h1 className="text-xl sm:text-4xl font-semibold font-ibm-plex drop-shadow-[0_0_12px_#008cff] text-[#ffffff]">
                                    CLIMATIZAÇÃO & AMBIENTE
                                </h1>

                                <div className={`mb-1 flex items-center gap-2 px-2.5 py-0.5 sm:px-3 sm:py-1 rounded-xl border text-[10px] sm:text-xs font-rajdhani font-bold uppercase tracking-wider ${isOnline === true
                                    ? "bg-emerald-500/20 border-emerald-400 text-emerald-300 shadow-[0_0_10px_#10b981]"
                                    : isOnline === false
                                        ? "bg-rose-500/20 border-rose-500 text-rose-400 shadow-[0_0_10px_#f43f5e]"
                                        : "bg-slate-800 border-slate-600 text-slate-400"
                                    }`}>
                                    {isOnline === true ? (
                                        <>
                                            <Wifi className="w-4 h-4 text-emerald-400 animate-pulse" strokeWidth={3} />
                                            <span>TUYA ONLINE</span>
                                        </>
                                    ) : isOnline === false ? (
                                        <>
                                            <WifiOff className="w-4 h-4 text-rose-400" strokeWidth={3} />
                                            <span>TUYA OFFLINE</span>
                                        </>
                                    ) : (
                                        <span>VERIFICANDO...</span>
                                    )}
                                </div>
                            </div>

                            <p className="font-rajdhani text-[#00b7ffb7] text-xs sm:text-sm tracking-wider uppercase">
                                Telemetria DHT22 • Tomada Inteligente Lumi Ar Condicionado
                            </p>
                        </div>

                        <div className="flex items-center gap-3">
                            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#091544]/80 border border-[#0066ff55] text-xs font-rajdhani">
                                <Activity className={`w-4 h-4 ${sensorAtivo ? "text-emerald-400 animate-pulse" : "text-slate-500"}`} />
                                <span className="text-[#a4e2ff]">ESP32 DHT22:</span>
                                <span className={sensorAtivo ? "text-emerald-300 font-bold" : "text-slate-400"}>
                                    {sensorAtivo ? "TRANSMITINDO" : "AGUARDANDO"}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* SEÇÃO 1: TELEMETRIA EM TEMPO REAL DO SENSOR DHT22 */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {/* CARD TEMPERATURA */}
                        <div className="relative overflow-hidden p-5 sm:p-6 bg-gradient-to-br from-[#0c184d]/90 via-[#0a143f]/80 to-[#050b24]/90 rounded-2xl border border-[#0077ff]/60 shadow-[0_0_20px_rgba(0,119,255,0.15)] flex flex-col gap-3">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Thermometer className="w-6 h-6 text-[#ff8c42] drop-shadow-[0_0_8px_#ff8c42]" />
                                    <span className="font-rajdhani font-semibold text-xs sm:text-sm uppercase tracking-wider text-[#a8e6ff]">
                                        Temperatura Ambiente
                                    </span>
                                </div>
                                <span className="text-[11px] font-rajdhani text-slate-400">
                                    Atualizado: {ultimaAtualizacao}
                                </span>
                            </div>

                            <div className="flex items-baseline gap-2 mt-1">
                                <span className="text-4xl sm:text-6xl font-bold font-rajdhani text-white drop-shadow-[0_0_15px_#ff8c42]">
                                    {temp !== null ? temp.toFixed(1) : "--"}
                                </span>
                                <span className="text-2xl sm:text-3xl font-semibold text-[#ff8c42]">°C</span>
                            </div>

                            <div className="flex items-center justify-between pt-2 border-t border-[#0051d344]">
                                <span className={`text-xs font-rajdhani font-bold ${statusTemp.cor}`}>
                                    ● {statusTemp.texto}
                                </span>
                                <span className="text-[11px] font-rajdhani text-[#68abff]">
                                    Sensor: Quarto (D4)
                                </span>
                            </div>
                        </div>

                        {/* CARD UMIDADE */}
                        <div className="relative overflow-hidden p-5 sm:p-6 bg-gradient-to-br from-[#0c184d]/90 via-[#0a143f]/80 to-[#050b24]/90 rounded-2xl border border-[#0077ff]/60 shadow-[0_0_20px_rgba(0,119,255,0.15)] flex flex-col gap-3">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Droplets className="w-6 h-6 text-[#00e5ff] drop-shadow-[0_0_8px_#00e5ff]" />
                                    <span className="font-rajdhani font-semibold text-xs sm:text-sm uppercase tracking-wider text-[#a8e6ff]">
                                        Umidade Relativa do Ar
                                    </span>
                                </div>
                                <span className="text-[11px] font-rajdhani text-slate-400">
                                    Atualizado: {ultimaAtualizacao}
                                </span>
                            </div>

                            <div className="flex items-baseline gap-2 mt-1">
                                <span className="text-4xl sm:text-6xl font-bold font-rajdhani text-white drop-shadow-[0_0_15px_#00e5ff]">
                                    {umid !== null ? umid.toFixed(0) : "--"}
                                </span>
                                <span className="text-2xl sm:text-3xl font-semibold text-[#00e5ff]">%</span>
                            </div>

                            <div className="flex items-center justify-between pt-2 border-t border-[#0051d344]">
                                <span className={`text-xs font-rajdhani font-bold ${statusUmid.cor}`}>
                                    ● {statusUmid.texto}
                                </span>
                                <span className="text-[11px] font-rajdhani text-[#68abff]">
                                    Padrão Conforto: 40% a 70%
                                </span>
                            </div>
                        </div>
                    </div>

                    {isOnline === false && (
                        <div className="flex items-center gap-3 p-3.5 sm:p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-300 text-xs sm:text-sm font-rajdhani">
                            <AlertCircle className="w-5 h-5 shrink-0 text-amber-400" />
                            <span>
                                Dispositivo <strong>Lumi Ar Condicionado</strong> consta como deslogado/offline no aplicativo Tuya. Conecte a tomada à rede física para controle em tempo real.
                            </span>
                        </div>
                    )}

                    {/* SEÇÃO 2: CONTROLE DA TOMADA DO AR CONDICIONADO */}
                    <div className="flex flex-col items-center justify-center p-6 sm:p-8 bg-[#091136]/70 backdrop-blur-[2px] rounded-2xl border-[0.1px] border-[#0077ff] gap-4 sm:gap-6 shadow-[0_0_25px_rgba(0,119,255,0.1)]">
                        <button
                            onClick={togglePower}
                            className={`p-6 sm:p-8 rounded-full cursor-pointer transition-all duration-300 border ${power
                                ? "bg-[#002fff1a] border-[#0077ff] text-[#0077ff] shadow-[0_0_30px_#0077ff] scale-105"
                                : "bg-slate-800/60 border-slate-600 text-slate-400 hover:border-slate-400"
                                }`}
                        >
                            <Power className="w-12 h-12 sm:w-16 sm:h-16" />
                        </button>
                        <div className="text-center">
                            <span className="font-rajdhani font-bold text-lg sm:text-2xl text-[#ffffff] tracking-wider drop-shadow-[0_0_8px_#008cff]">
                                {power ? "TOMADA DO AR ALIMENTADA" : "TOMADA DO AR DESLIGADA"}
                            </span>
                            <p className="font-rajdhani text-xs sm:text-sm text-[#00b7ffb7] mt-1 uppercase tracking-wider">
                                Clique para ligar ou desligar o fornecimento de energia ao Ar-Condicionado
                            </p>
                        </div>
                    </div>

                    {/* SEÇÃO 3: MÉTRICAS E CARGA */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                        <div className="flex items-center gap-3 sm:gap-4 p-4 sm:p-5 bg-[#091136]/60 backdrop-blur-[2px] rounded-2xl border-[0.1px] border-[#0077ff]">
                            <Zap className="w-7 h-7 sm:w-8 sm:h-8 text-[#0077ff] drop-shadow-[0_0_10px_#0077ff]" />
                            <div>
                                <span className="font-rajdhani text-xs sm:text-sm text-[#00b7ffb7] uppercase tracking-wider">Carga Estimada</span>
                                <h4 className="font-rajdhani font-bold text-base sm:text-xl text-white">{power ? "1.200 W" : "0 W"}</h4>
                            </div>
                        </div>

                        <div className="flex items-center gap-3 sm:gap-4 p-4 sm:p-5 bg-[#091136]/60 backdrop-blur-[2px] rounded-2xl border-[0.1px] border-[#0077ff]">
                            <Timer className="w-7 h-7 sm:w-8 sm:h-8 text-[#0077ff] drop-shadow-[0_0_10px_#0077ff]" />
                            <div>
                                <span className="font-rajdhani text-xs sm:text-sm text-[#00b7ffb7] uppercase tracking-wider">Desligamento Automático</span>
                                <h4 className="font-rajdhani font-bold text-base sm:text-xl text-white">Desativado</h4>
                            </div>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
}

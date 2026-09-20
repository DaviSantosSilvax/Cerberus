import { useState, useEffect } from "react";
import CerberusBackground from "../assets/CerberusBackground.png";
import SideBar from "../Components/DashBoard/SideBar";
import { Power, Zap, Timer, AlertCircle, Wifi, WifiOff, Snowflake, Thermometer } from "lucide-react";
import SideBarMobile from "../Components/DashBoard/SideBarMobile";

export default function Climatizacao() {
    const [power, setPower] = useState<boolean>(false);
    const [isOnline, setIsOnline] = useState<boolean | null>(null);

    const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ? `${import.meta.env.VITE_BACKEND_URL}/ar-condicionado` : `http://${window.location.hostname}:8001/api/ar-condicionado`;

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const res = await fetch(`${BACKEND_URL}/status`);
                const data = await res.json();
                if (data.online !== undefined) {
                    setIsOnline(data.online);
                }
                if (data.status && Array.isArray(data.status)) {
                    const switchItem = data.status.find((s: any) => s.code === "switch_1");
                    if (switchItem !== undefined) {
                        setPower(Boolean(switchItem.value));
                    }
                }
            } catch (err) {
                console.error(err);
                setIsOnline(false);
            }
        };

        fetchStatus();
        const interval = setInterval(fetchStatus, 10000);
        return () => clearInterval(interval);
    }, [BACKEND_URL]);

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
            console.error(err);
        }
    };

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
                <div className="w-full max-w-3xl backdrop-blur-[4px] bg-[#000b425e] border border-[#0066ff8c] shadow-[0_0_35px_rgba(0,183,255,0.2)] rounded-2xl sm:rounded-3xl p-4 sm:p-8 flex flex-col gap-6 sm:gap-8">

                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#004bbb8c] pb-4">
                        <div className="flex flex-col gap-1">

                            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                                <Snowflake className="w-10 h-10 text-[#39a6ff] drop-shadow-[1px_1px_12px_#39a6ff]" />
                                <h1 className="text-xl sm:text-4xl font-semibold font-ibm-plex drop-shadow-[0_0_12px_#008cff] text-[#ffffff]">
                                    CLIMATIZAÇÃO
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
                                            <span>ONLINE</span>
                                        </>
                                    ) : isOnline === false ? (
                                        <>
                                            <WifiOff className="w-4 h-4 text-rose-400" strokeWidth={3} />
                                            <span>OFFLINE</span>
                                        </>
                                    ) : (
                                        <span>VERIFICANDO...</span>
                                    )}
                                </div>
                            </div>

                            <p className="font-rajdhani text-[#00b7ffb7] text-xs sm:text-sm tracking-wider uppercase">
                                Tomada Inteligente • Lumi Ar Condicionado
                            </p>
                        </div>

                        <div className="flex justify-end">
                            <button
                                onClick={togglePower}
                                className={`p-3 sm:p-4 rounded-4xl cursor-pointer transition-all duration-300 border ${power
                                    ? "bg-[#002fff1a] border-[#0077ff] text-[#0077ff] shadow-[0_0_20px_#0077ff] scale-105"
                                    : "bg-slate-800/60 border-slate-600 text-slate-400 hover:border-slate-400"
                                    }`}
                            >
                                <Power className="w-6 h-6 sm:w-8 sm:h-8" />
                            </button>
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

                    <div className="flex flex-col items-center justify-center p-6 sm:p-8 bg-[#091136]/60 backdrop-blur-[2px] rounded-2xl border-[0.1px] border-[#0077ff] gap-4 sm:gap-6">
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
                                {power ? "TOMADA ALIMENTADA" : "TOMADA DESLIGADA"}
                            </span>
                            <p className="font-rajdhani text-xs sm:text-sm text-[#00b7ffb7] mt-1 uppercase tracking-wider">
                                Clique para ligar ou desligar o fornecimento de energia ao Ar-Condicionado
                            </p>
                        </div>
                    </div>

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

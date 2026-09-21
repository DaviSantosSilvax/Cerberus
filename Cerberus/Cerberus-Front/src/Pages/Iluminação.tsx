import { useState, useEffect } from "react";
import CerberusBackground from "../assets/CerberusBackground.png";
import SideBar from "../Components/DashBoard/SideBar";
import SideBarMobile from "../Components/DashBoard/SideBarMobile";
import { Power, Sun, Palette, Sparkles, Music, Sliders, Pipette, Wifi, WifiOff, Activity, Lightbulb } from "lucide-react";

export default function Iluminação() {
    const [power, setPower] = useState<boolean>(true);
    const [activeMode, setActiveMode] = useState<"white" | "colour" | "scene" | "music">("white");
    const [brightness, setBrightness] = useState<number>(80);
    const [colorTemp, setColorTemp] = useState<number>(50);
    const [selectedColorName, setSelectedColorName] = useState<string>("Cyan");
    const [customHex, setCustomHex] = useState<string>("#00f0ff");
    const [hueDegree, setHueDegree] = useState<number>(180);
    const [isOnline, setIsOnline] = useState<boolean | null>(null);

    const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ? `${import.meta.env.VITE_BACKEND_URL}/lampada` : `http://${window.location.hostname}:8001/api/lampada`;

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const res = await fetch(`${BACKEND_URL}/status`);
                const data = await res.json();
                if (data.online !== undefined) {
                    setIsOnline(data.online);
                }
                if (data.status && Array.isArray(data.status)) {
                    const switchItem = data.status.find((s: any) => s.code === 'switch_led');
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

    const hexToHsv = (hex: string) => {
        let r = parseInt(hex.slice(1, 3), 16) / 255;
        let g = parseInt(hex.slice(3, 5), 16) / 255;
        let b = parseInt(hex.slice(5, 7), 16) / 255;

        let max = Math.max(r, g, b), min = Math.min(r, g, b);
        let h = 0, s = 0, v = max;
        let d = max - min;

        s = max === 0 ? 0 : d / max;

        if (max !== min) {
            switch (max) {
                case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                case g: h = (b - r) / d + 2; break;
                case b: h = (r - g) / d + 4; break;
            }
            h /= 6;
        }

        return {
            h: Math.round(h * 360),
            s: Math.round(s * 1000),
            v: Math.round(v * 1000)
        };
    };

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

    const handleModeChange = async (mode: "white" | "colour" | "scene" | "music") => {
        setActiveMode(mode);
        try {
            await fetch(`${BACKEND_URL}/mode`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mode }),
            });
        } catch (err) {
            console.error(err);
        }
    };

    const handleWhiteChange = async (newBright: number, newTemp: number) => {
        setBrightness(newBright);
        setColorTemp(newTemp);
        try {
            await fetch(`${BACKEND_URL}/white`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    bright: Math.round((newBright / 100) * 1000),
                    temp: Math.round(((100 - newTemp) / 100) * 1000),
                }),
            });
        } catch (err) {
            console.error(err);
        }
    };

    const sendHsvColor = async (h: number, s: number = 1000, v: number = 1000) => {
        setActiveMode("colour");
        try {
            await fetch(`${BACKEND_URL}/color`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ h, s, v }),
            });
        } catch (err) {
            console.error(err);
        }
    };

    const handleCustomHexChange = (hex: string) => {
        setCustomHex(hex);
        setSelectedColorName(`Personalizado (${hex.toUpperCase()})`);
        const hsv = hexToHsv(hex);
        setHueDegree(hsv.h);
        sendHsvColor(hsv.h, hsv.s, hsv.v);
    };

    const handleHueSliderChange = (h: number) => {
        setHueDegree(h);
        setSelectedColorName(`Matiz (${h}°)`);
        sendHsvColor(h, 1000, 1000);
    };

    return (
        <div className="relative min-h-screen w-full flex flex-col md:flex-row overflow-x-hidden">
            <img
                src={CerberusBackground}
                alt="Iluminação"
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
                                <Lightbulb className="w-10 h-10 text-[#39a6ff] drop-shadow-[1px_1px_12px_#39a6ff]" />
                                <h1 className="text-xl sm:text-4xl font-semibold font-ibm-plex drop-shadow-[0_0_12px_#008cff] text-[#ffffff]">
                                    ILUMINAÇÃO
                                </h1>

                                <div className={`mb-1 flex items-center gap-2 mb-1 px-2.5 py-0.5 sm:px-3 sm:py-1 rounded-xl border text-[10px] sm:text-xs font-rajdhani font-bold uppercase tracking-wider ${isOnline === true
                                    ? "bg-emerald-500/20 border-emerald-400 text-emerald-300 shadow-[0_0_10px_#10b981]"
                                    : isOnline === false
                                        ? "bg-rose-500/20 border-rose-500 text-rose-400 shadow-[0_0_10px_#f43f5e]"
                                        : "bg-slate-800 border-slate-600 text-slate-400"
                                    }`}>
                                    {isOnline === true ? (
                                        <>
                                            <Wifi className="w-4 h-4 text-emerald-400 animate-pulse" strokeWidth={3} />
                                            <span className="">ONLINE</span>
                                        </>
                                    ) : isOnline === false ? (
                                        <>
                                            <WifiOff className="w-4 h-4 text-rose-400 strokeWidth={3}" />
                                            <span>OFFLINE</span>
                                        </>
                                    ) : (
                                        <span>VERIFICANDO...</span>
                                    )}
                                </div>
                            </div>

                            <p className="font-rajdhani text-[#00b7ffb7] text-xs sm:text-sm tracking-wider uppercase">
                                Lâmpada Inteligente Steck • Quarto Principal
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

                    <div className="flex flex-col gap-2 sm:gap-3">
                        <label className="font-rajdhani text-xs sm:text-sm text-[#288cff] font-semibold tracking-wider uppercase">
                            Modo de Operação
                        </label>
                        <div className="rounded-2xl border-1 border-[#0077ff] font-bold grid grid-cols-2 sm:grid-cols-4 gap-2.5 sm:gap-4">
                            {[
                                { id: "white", label: "Tonalidade", icon: Sun },
                                { id: "colour", label: "Cores (RGB)", icon: Palette },
                                { id: "scene", label: "Cenas", icon: Sparkles },
                                { id: "music", label: "Music Sync", icon: Music },
                            ].map((mode) => {
                                const Icon = mode.icon;
                                const isActive = activeMode === mode.id;
                                return (
                                    <button
                                        key={mode.id}
                                        onClick={() => handleModeChange(mode.id as any)}
                                        className={`flex flex-col items-center gap-1.5 sm:gap-2 p-3 sm:p-4 rounded-xl border transition-all cursor-pointer font-rajdhani font-semibold text-xs sm:text-base ${isActive
                                            ? "backdrop-blur-[4px] bg-[#003afa2d] border-[#0077ff] rounded-r-[10px] text-[#0077ff] shadow-[0_0_5px_#0077ff,inset_0_0_10px_#0077ff]"
                                            : "border-none text-[#0077ff] hover:border-[#0077ff]/50 hover:text-[#3d98ff]"
                                            }`}
                                    >
                                        <Icon className={`w-5 h-5 sm:w-6 sm:h-6 ${isActive ? "text-[#008cff] drop-shadow-[0_0_12px_#0077ff]" : ""}`} />
                                        <span className="drop-shadow-[0_0_5px_#0077ff]">{mode.label}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {activeMode === "white" && (
                        <div className="flex flex-col gap-4 sm:gap-6 bg-[#091136]/60 p-4 sm:p-6 rounded-2xl border border-cyan-900/40">
                            <div className="flex items-center gap-2.5 sm:gap-3 text-[#45a7ff] font-rajdhani font-bold text-base sm:text-lg">
                                <Sliders className="w-5 h-5 text-[#0077ff]" />
                                <span className="drop-shadow-[0_0_5px_#0077ff]">Ajuste de Luz Branca</span>
                            </div>

                            <div className="flex flex-col gap-2">
                                <div className="flex justify-between text-xs sm:text-sm font-rajdhani text-cyan-200">
                                    <span>Brilho</span>
                                    <span className="font-bold text-[#0077ff]">{brightness}%</span>
                                </div>
                                <input
                                    type="range"
                                    min="1"
                                    max="100"
                                    value={brightness}
                                    onChange={(e) => handleWhiteChange(Number(e.target.value), colorTemp)}
                                    className="w-full accent-[#006fc5] cursor-pointer"
                                />
                            </div>

                            <div className="flex flex-col gap-2">
                                <div className="flex justify-between text-xs sm:text-sm font-rajdhani text-cyan-200">
                                    <span>Tonalidade (Branco Frio / Amarelo)</span>
                                    <span className="font-bold text-amber-400">
                                        {colorTemp < 50 ? "Branco Frio" : "Amarelo (Quente)"} ({colorTemp}%)
                                    </span>
                                </div>
                                <input
                                    type="range"
                                    min="0"
                                    max="100"
                                    value={colorTemp}
                                    onChange={(e) => handleWhiteChange(brightness, Number(e.target.value))}
                                    className="w-full h-3 rounded-lg cursor-pointer appearance-none accent-amber-400"
                                    style={{
                                        background: "linear-gradient(to right, #e0f7fa, #fef08a, #f59e0b)",
                                    }}
                                />
                            </div>
                        </div>
                    )}

                    {activeMode === "colour" && (
                        <div className="flex flex-col gap-4 sm:gap-6 bg-[#091136]/60 backdrop-blur-[2px] p-4 sm:p-6 rounded-2xl border-[0.1px] border-[#0077ff]">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                                <div className="flex items-center gap-2 text-[#0077ff] font-rajdhani font-bold text-base sm:text-lg">
                                    <Pipette className="w-5 h-5 text-[#0077ff]" />
                                    <span>Seletor de Cor Exata</span>
                                </div>
                                <span className="text-xs sm:text-sm font-rajdhani text-[#00f0ff] font-semibold">
                                    {selectedColorName}
                                </span>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 items-center">
                                <div className="flex flex-col items-center gap-1.5">
                                    <label className="relative cursor-pointer group flex items-center justify-center">
                                        <div
                                            style={{ backgroundColor: customHex, boxShadow: `0 0 25px ${customHex}` }}
                                            className="w-16 h-16 sm:w-20 sm:h-20 rounded-full border-4 border-white/80 transition-all duration-300 group-hover:scale-105 flex items-center justify-center"
                                        >
                                            <Pipette className="w-6 h-6 sm:w-8 sm:h-8 text-white drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)]" />
                                        </div>
                                        <input
                                            type="color"
                                            value={customHex}
                                            onChange={(e) => handleCustomHexChange(e.target.value)}
                                            className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                                        />
                                    </label>
                                    <span className="text-[10px] sm:text-xs font-rajdhani text-cyan-200/80">Clique para abrir a paleta</span>
                                </div>

                                <div className="sm:col-span-2 flex flex-col gap-2.5">
                                    <div className="flex justify-between text-xs sm:text-sm font-rajdhani text-cyan-200">
                                        <span>Espectro de Cores (360°)</span>
                                        <span className="font-bold text-[#00f0ff]">{hueDegree}°</span>
                                    </div>
                                    <input
                                        type="range"
                                        min="0"
                                        max="360"
                                        value={hueDegree}
                                        onChange={(e) => handleHueSliderChange(Number(e.target.value))}
                                        className="w-full h-3.5 sm:h-4 rounded-lg cursor-pointer appearance-none"
                                        style={{
                                            background: "linear-gradient(to right, #ff0000, #ffff00, #00ff00, #00ffff, #0000ff, #ff00ff, #ff0000)",
                                        }}
                                    />
                                </div>
                            </div>

                            <div className="flex flex-col gap-2.5 border-t border-cyan-900/40 pt-3.5">
                                <span className="font-rajdhani font-semibold text-xs sm:text-sm text-cyan-300/80 uppercase">Atalhos Rápidos</span>
                                <div className="flex items-center gap-3 sm:gap-4 flex-wrap">
                                    {[
                                        { name: "Cyan", hex: "#00f0ff", h: 180 },
                                        { name: "Purple", hex: "#a855f7", h: 270 },
                                        { name: "Neon Red", hex: "#ff0055", h: 345 },
                                        { name: "Electric Blue", hex: "#3b82f6", h: 220 },
                                        { name: "Emerald Green", hex: "#10b981", h: 140 },
                                        { name: "Gold", hex: "#eab308", h: 45 },
                                    ].map((c) => (
                                        <button
                                            key={c.name}
                                            onClick={() => {
                                                setCustomHex(c.hex);
                                                setSelectedColorName(c.name);
                                                setHueDegree(c.h);
                                                sendHsvColor(c.h, 1000, 1000);
                                            }}
                                            style={{ backgroundColor: c.hex, boxShadow: `0 0 14px ${c.hex}` }}
                                            className={`w-9 h-9 sm:w-10 sm:h-10 rounded-full cursor-pointer hover:scale-115 transition-all border-2 ${customHex.toLowerCase() === c.hex.toLowerCase() ? "border-white scale-110 shadow-lg" : "border-white/50"
                                                }`}
                                            title={c.name}
                                        />
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {activeMode === "music" && (
                        <div className="flex flex-col items-center justify-center p-5 sm:p-8 bg-[#091136]/60 rounded-2xl border border-cyan-900/40 text-center gap-3 sm:gap-4">
                            <div className="p-3 sm:p-4 rounded-full bg-[#00f0ff]/10 border border-[#0077ff]/40 shadow-[0_0_20px_#0077ff] animate-pulse">
                                <Activity className="w-8 h-8 sm:w-10 sm:h-10 text-[#0077ff]" />
                            </div>

                            <h3 className="font-zen-dots text-lg sm:text-xl text-[#0077ff]">
                                MODO RITMO & SOM ATIVO
                            </h3>

                            <p className="text-xs sm:text-sm font-rajdhani text-[#0077ff] max-w-md">
                                O sensor acústico interno da própria lâmpada está ativo. Coloque uma música para tocar no seu quarto ou fale no ambiente e a lâmpada responderá automaticamente!
                            </p>
                        </div>
                    )}

                </div>
            </div>
        </div>
    );
}
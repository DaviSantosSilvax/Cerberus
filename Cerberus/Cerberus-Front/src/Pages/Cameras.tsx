import { useState, useRef } from 'react'
import SideBar from '../Components/DashBoard/SideBar'
import SideBarMobile from '../Components/DashBoard/SideBarMobile'
import Background from '../assets/CerberusBackground.png'
import { Video, ShieldCheck, RefreshCw, Maximize, Wifi, Cpu, Camera, Radio } from 'lucide-react'

export default function Cameras() {
    const [offline, setOffline] = useState(false)
    const [reloadKey, setReloadKey] = useState(0)
    const videoContainerRef = useRef<HTMLDivElement>(null)

    const baseUrl = import.meta.env.VITE_BACKEND_URL
        ? import.meta.env.VITE_BACKEND_URL.replace(/\/chat$/, '')
        : `http://${window.location.hostname}:8001/api`

    // Rota de streaming contínuo MJPEG (sem polling no frontend)
    const mjpegStreamUrl = `${baseUrl}/dashboard/camera-quarto/stream?t=${reloadKey}`

    const toggleFullscreen = () => {
        if (videoContainerRef.current) {
            if (!document.fullscreenElement) {
                videoContainerRef.current.requestFullscreen().catch(err => console.error(err))
            } else {
                document.exitFullscreen().catch(err => console.error(err))
            }
        }
    }

    const handleReload = () => {
        setOffline(false)
        setReloadKey(prev => prev + 1)
    }


    return (
        <div className="flex min-h-screen text-white font-sans">
            <div className="hidden sm:block">
                <SideBar />
            </div>
            <div className="sm:hidden">
                <SideBarMobile />
            </div>
            <img src={Background} alt="Background" className="fixed inset-0 w-full h-full object-cover object-center -z-10" />

            <div className="flex-1 p-4 sm:p-8 flex flex-col items-center">
                <div className="w-full max-w-6xl backdrop-blur-[8px] bg-[#000b425e] border border-[#0066ff8c] shadow-[0_0_35px_rgba(0,183,255,0.2)] rounded-2xl sm:rounded-3xl p-4 sm:p-8 flex flex-col gap-6 sm:gap-8">
                    
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-[#0066ff40] pb-5 gap-4">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-cyan-950/70 border border-cyan-500/40 rounded-2xl shadow-[0_0_15px_rgba(0,240,255,0.25)]">
                                <Video className="w-9 h-9 text-[#39a6ff] drop-shadow-[0_0_12px_#39a6ff]" strokeWidth={1.5} />
                            </div>
                            <div>
                                <h1 className="text-3xl sm:text-4xl font-semibold font-ibm-plex drop-shadow-[0_0_12px_#008cff] text-[#ffffff]">
                                    Câmeras de Segurança
                                </h1>
                                <p className="text-sm text-cyan-300/80 flex items-center gap-2 mt-0.5">
                                    <span className={`w-2.5 h-2.5 rounded-full ${offline ? 'bg-amber-500' : 'bg-emerald-400 animate-ping'}`}></span>
                                    Câmera Quarto — via go2rtc & Tailscale
                                </p>
                            </div>
                        </div>

                        {/* Botões de Ação */}
                        <div className="flex items-center gap-3">
                            <button
                                onClick={handleReload}
                                className="flex items-center gap-2 px-4 py-2 bg-cyan-950/60 hover:bg-cyan-900/80 border border-cyan-500/40 rounded-xl text-cyan-300 text-sm font-medium transition-all shadow-[0_0_10px_rgba(0,240,255,0.15)] active:scale-95"
                                title="Recarregar Imagem"
                            >
                                <RefreshCw className="w-4 h-4" />
                                <span>Recarregar</span>
                            </button>
                            <button
                                onClick={toggleFullscreen}
                                className="flex items-center gap-2 px-4 py-2 bg-blue-950/60 hover:bg-blue-900/80 border border-blue-500/40 rounded-xl text-blue-300 text-sm font-medium transition-all active:scale-95"
                                title="Tela Cheia"
                            >
                                <Maximize className="w-4 h-4" />
                                <span className="hidden sm:inline">Tela Cheia</span>
                            </button>
                        </div>
                    </div>

                    {/* Main Camera Feed */}
                    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                        
                        {/* Feed de Vídeo Principal (3/4 da tela) */}
                        <div className="lg:col-span-3 flex flex-col gap-4">
                            <div 
                                ref={videoContainerRef}
                                className="relative group bg-slate-950/90 rounded-2xl overflow-hidden border border-cyan-500/40 shadow-[0_0_25px_rgba(0,140,255,0.2)] flex items-center justify-center min-h-[320px] sm:min-h-[460px]"
                            >
                                {/* Overlay Badges de Status (Canto Superior) */}
                                <div className="absolute top-4 left-4 z-20 flex flex-wrap items-center gap-2">
                                    <div className="flex items-center gap-2 bg-black/70 backdrop-blur-md px-3.5 py-1.5 rounded-full border border-emerald-500/40 text-xs font-semibold text-emerald-400 shadow-md">
                                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                                        <span>LIVE STREAM</span>
                                    </div>
                                    <div className="flex items-center gap-1.5 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-full border border-cyan-500/30 text-xs text-cyan-300">
                                        <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                                        <span>TAPO TC60</span>
                                    </div>
                                </div>

                                <div className="absolute top-4 right-4 z-20">
                                    <span className="bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-full border border-blue-500/30 text-xs font-mono text-blue-300">
                                        MJPEG • 1080p FHD
                                    </span>
                                </div>

                                {/* Imagem de Stream Contínuo MJPEG */}
                                {!offline ? (
                                    <img
                                        key={reloadKey}
                                        src={mjpegStreamUrl}
                                        alt="Câmera do quarto (MJPEG Stream)"
                                        className="w-full h-full max-h-[560px] object-contain bg-black transition-opacity duration-200"
                                        onError={() => setOffline(true)}
                                        onLoad={() => setOffline(false)}
                                    />
                                ) : (
                                    <div className="flex flex-col items-center justify-center p-8 text-center gap-4 text-cyan-300/80">
                                        <Camera className="w-16 h-16 text-cyan-500/40 animate-bounce" />
                                        <div className="space-y-1">
                                            <p className="text-lg font-medium text-white">Câmera indisponível (PC desligado?)</p>
                                            <p className="text-xs text-cyan-300/60 max-w-md">
                                                Verifique se o seu PC local está ligado e se o <code className="text-cyan-400">go2rtc</code> está rodando no Tailscale (<code className="text-cyan-400">100.127.0.33:1984</code>).
                                            </p>
                                        </div>
                                        <button
                                            onClick={handleReload}
                                            className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold rounded-xl text-sm transition-all shadow-[0_0_15px_rgba(0,240,255,0.4)] active:scale-95"
                                        >
                                            Tentar Reconectar
                                        </button>
                                    </div>
                                )}


                                {/* Barra inferior de informações da imagem */}
                                <div className="absolute bottom-0 inset-x-0 p-3 bg-gradient-to-t from-black/90 via-black/50 to-transparent flex justify-between items-center text-xs text-cyan-200/80 font-mono">
                                    <span>Stream: camera_quarto</span>
                                    <span>Tailscale IP: 100.127.0.33</span>
                                    <span>Intervalo: 1.5s</span>
                                </div>
                            </div>
                        </div>

                        {/* Painel Lateral de Informações (1/4 da tela) */}
                        <div className="flex flex-col gap-4">
                            
                            {/* Card de Especificações */}
                            <div className="bg-slate-950/60 backdrop-blur-md border border-cyan-500/30 rounded-2xl p-4 flex flex-col gap-4">
                                <h3 className="text-sm font-semibold text-cyan-300 uppercase tracking-wider flex items-center gap-2">
                                    <Cpu className="w-4 h-4 text-cyan-400" />
                                    Dispositivo
                                </h3>

                                <div className="space-y-3 text-xs">
                                    <div className="flex justify-between pb-2 border-b border-cyan-500/20">
                                        <span className="text-slate-400">Modelo:</span>
                                        <span className="font-semibold text-white">Tapo TC60</span>
                                    </div>
                                    <div className="flex justify-between pb-2 border-b border-cyan-500/20">
                                        <span className="text-slate-400">Origem:</span>
                                        <span className="text-white">go2rtc / Tailscale</span>
                                    </div>
                                    <div className="flex justify-between pb-2 border-b border-cyan-500/20">
                                        <span className="text-slate-400">Resolução:</span>
                                        <span className="text-emerald-400 font-semibold">1080p (Full HD)</span>
                                    </div>
                                    <div className="flex justify-between pb-2 border-b border-cyan-500/20">
                                        <span className="text-slate-400">Endpoint:</span>
                                        <span className="text-cyan-300 font-mono truncate max-w-[120px]">/dashboard/camera-quarto</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-slate-400">Rede Wi-Fi:</span>
                                        <span className="text-white flex items-center gap-1">
                                            <Wifi className="w-3.5 h-3.5 text-emerald-400" /> Casa (2.4 GHz)
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {/* Card de Atualização do Feed */}
                            <div className="bg-slate-950/60 backdrop-blur-md border border-blue-500/30 rounded-2xl p-4 flex flex-col gap-3">
                                <h3 className="text-sm font-semibold text-blue-300 uppercase tracking-wider flex items-center gap-2">
                                    <Radio className="w-4 h-4 text-blue-400" />
                                    Status da Conexão
                                </h3>
                                <div className={`p-3 rounded-xl text-xs font-semibold text-center border ${
                                    offline 
                                        ? 'bg-amber-950/60 border-amber-500/40 text-amber-300' 
                                        : 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300'
                                }`}>
                                    {offline ? '⚠️ Câmera indisponível (PC desligado?)' : '🟢 Câmera Online (Polling 1.5s)'}
                                </div>
                                <p className="text-[11px] text-slate-400 mt-1">
                                    Busca automática de snapshot no backend a cada 1.5 segundos com cache-busting.
                                </p>
                            </div>

                        </div>

                    </div>

                </div>
            </div>
        </div>
    )
}




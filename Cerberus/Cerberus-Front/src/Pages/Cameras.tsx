import { useState, useRef } from 'react'
import SideBar from '../Components/DashBoard/SideBar'
import SideBarMobile from '../Components/DashBoard/SideBarMobile'
import Background from '../assets/CerberusBackground.png'
import { Video, ShieldCheck, RefreshCw, Maximize, Wifi, Cpu, Camera } from 'lucide-react'

export default function Cameras() {
    const [reloadKey, setReloadKey] = useState(0)
    const [streamQuality, setStreamQuality] = useState<'stream1' | 'stream2'>('stream1')
    const [hasError, setHasError] = useState(false)
    const videoContainerRef = useRef<HTMLDivElement>(null)

    const baseUrl = import.meta.env.VITE_BACKEND_URL
        ? import.meta.env.VITE_BACKEND_URL.replace(/\/chat$/, '')
        : `http://${window.location.hostname}:8001/api`

    const streamUrl = `${baseUrl}/camera/stream?quality=${streamQuality}&t=${reloadKey}`

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
        setHasError(false)
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
                                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                                    TP-Link Tapo TC60 1080p — Sistema Cerberus
                                </p>
                            </div>
                        </div>

                        {/* Botões de Ação */}
                        <div className="flex items-center gap-3">
                            <button
                                onClick={handleReload}
                                className="flex items-center gap-2 px-4 py-2 bg-cyan-950/60 hover:bg-cyan-900/80 border border-cyan-500/40 rounded-xl text-cyan-300 text-sm font-medium transition-all shadow-[0_0_10px_rgba(0,240,255,0.15)] active:scale-95"
                                title="Recarregar Feed de Vídeo"
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
                                        <span>REC</span>
                                        <span className="text-emerald-300/50">|</span>
                                        <span>LIVE</span>
                                    </div>
                                    <div className="flex items-center gap-1.5 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-full border border-cyan-500/30 text-xs text-cyan-300">
                                        <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                                        <span>TAPO TC60</span>
                                    </div>
                                </div>

                                <div className="absolute top-4 right-4 z-20">
                                    <span className="bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-full border border-blue-500/30 text-xs font-mono text-blue-300">
                                        1080p FHD • 554/RTSP
                                    </span>
                                </div>

                                {/* Imagem de Stream MJPEG */}
                                {!hasError ? (
                                    <img
                                        key={reloadKey}
                                        src={streamUrl}
                                        alt="Feed Câmera Tapo TC60"
                                        className="w-full h-full max-h-[560px] object-contain bg-black"
                                        onError={() => setHasError(true)}
                                    />
                                ) : (
                                    <div className="flex flex-col items-center justify-center p-8 text-center gap-4 text-cyan-300/80">
                                        <Camera className="w-16 h-16 text-cyan-500/40 animate-bounce" />
                                        <div className="space-y-1">
                                            <p className="text-lg font-medium text-white">Aguardando feed da Câmera Tapo...</p>
                                            <p className="text-xs text-cyan-300/60 max-w-md">
                                                Conectando ao RTSP em <code className="text-cyan-400">192.168.1.103:554</code>.
                                                Certifique-se de que a câmera está ligada à mesma rede do backend.
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
                                    <span>IP: 192.168.1.103</span>
                                    <span>Usuário: Cerberus</span>
                                    <span>Fuso: GMT-3</span>
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
                                        <span className="text-slate-400">Fabricante:</span>
                                        <span className="text-white">TP-Link</span>
                                    </div>
                                    <div className="flex justify-between pb-2 border-b border-cyan-500/20">
                                        <span className="text-slate-400">Resolução:</span>
                                        <span className="text-emerald-400 font-semibold">1080p (Full HD)</span>
                                    </div>
                                    <div className="flex justify-between pb-2 border-b border-cyan-500/20">
                                        <span className="text-slate-400">Protocolo:</span>
                                        <span className="text-cyan-300 font-mono">RTSP / H.264</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-slate-400">Rede Wi-Fi:</span>
                                        <span className="text-white flex items-center gap-1">
                                            <Wifi className="w-3.5 h-3.5 text-emerald-400" /> 2.4 GHz
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {/* Card de Configuração de Stream */}
                            <div className="bg-slate-950/60 backdrop-blur-md border border-blue-500/30 rounded-2xl p-4 flex flex-col gap-3">
                                <h3 className="text-sm font-semibold text-blue-300 uppercase tracking-wider">
                                    Qualidade do Stream
                                </h3>
                                <div className="grid grid-cols-2 gap-2">
                                    <button
                                        onClick={() => { setStreamQuality('stream1'); handleReload(); }}
                                        className={`py-2 px-3 rounded-xl text-xs font-semibold transition-all ${
                                            streamQuality === 'stream1'
                                                ? 'bg-cyan-600 text-slate-950 shadow-[0_0_12px_rgba(0,240,255,0.4)]'
                                                : 'bg-slate-900/80 text-cyan-300 hover:bg-slate-800'
                                        }`}
                                    >
                                        1080p High
                                    </button>
                                    <button
                                        onClick={() => { setStreamQuality('stream2'); handleReload(); }}
                                        className={`py-2 px-3 rounded-xl text-xs font-semibold transition-all ${
                                            streamQuality === 'stream2'
                                                ? 'bg-cyan-600 text-slate-950 shadow-[0_0_12px_rgba(0,240,255,0.4)]'
                                                : 'bg-slate-900/80 text-cyan-300 hover:bg-slate-800'
                                        }`}
                                    >
                                        360p Fast
                                    </button>
                                </div>
                                <p className="text-[11px] text-slate-400 mt-1">
                                    Use 360p se a conexão estiver lenta ou se houver travamentos no stream.
                                </p>
                            </div>

                        </div>

                    </div>

                </div>
            </div>
        </div>
    )
}



import { useState } from "react";
import { useNavigate } from "react-router-dom";
import SideBar from "../Components/DashBoard/SideBar";
import SideBarMobile from "../Components/DashBoard/SideBarMobile";
import BackGround from "../assets/CerberusBackgroundMobile.jpg";
import { Bot, Send, Loader2, Heart, Home, Monitor, Smile, Check, Flame } from "lucide-react";

export default function Cerberus() {
    const navigate = useNavigate();
    const [inputMessage, setInputMessage] = useState("");
    const [messages, setMessages] = useState<Array<{ sender: "user" | "bot"; text: string }>>([]);
    const [loading, setLoading] = useState(false);
    const [displayMode, setDisplayMode] = useState<"rosto" | "home">("rosto");
    const [displayLoading, setDisplayLoading] = useState<boolean>(false);
    const [displayStatusMsg, setDisplayStatusMsg] = useState<string | null>(null);

    const BACKEND_URL = import.meta.env.VITE_BACKEND_URL
        ? `${import.meta.env.VITE_BACKEND_URL}/chat`
        : `http://${window.location.hostname}:8001/api/chat`;

    const mudarTelaDisplay = async (tela: "home" | "rosto") => {
        setDisplayLoading(true);
        try {
            const baseUrl = import.meta.env.VITE_BACKEND_URL
                ? import.meta.env.VITE_BACKEND_URL.replace(/\/chat$/, "")
                : `http://${window.location.hostname}:8001/api`;

            const res = await fetch(`${baseUrl}/cerberus/tela`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tela }),
            });

            if (res.ok) {
                setDisplayMode(tela);
                setDisplayStatusMsg(`Display ESP32: tela alterada para ${tela === "home" ? "HOME 🏠" : "ROSTO 🤖"}!`);
            } else {
                setDisplayStatusMsg("Erro ao enviar comando para o display.");
            }
        } catch (error) {
            console.error("Erro ao alterar display:", error);
            setDisplayStatusMsg("Falha ao conectar ao backend.");
        } finally {
            setDisplayLoading(false);
            setTimeout(() => setDisplayStatusMsg(null), 3500);
        }
    };

    const sendMessage = async (customMsg?: string) => {
        const textToSend = customMsg || inputMessage;
        if (!textToSend.trim()) return;

        setMessages((prev) => [...prev, { sender: "user", text: textToSend }]);
        if (!customMsg) setInputMessage("");
        setLoading(true);

        try {
            const response = await fetch(BACKEND_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mensagem: textToSend }),
            });

            const data = await response.json();
            setMessages((prev) => [...prev, { sender: "bot", text: data.resposta || "Sem resposta." }]);

        } catch (error) {
            console.error(error);
            setMessages((prev) => [
                ...prev,
                { sender: "bot", text: "Erro ao conectar com o assistente Cerberus." }
            ]);
        } finally {
            setLoading(false);
        }
    };

    const sendCarinho = () => {
        sendMessage("*faço carinho na sua cabeça, bom garoto!*");
    };

    return (
        <div className="flex min-h-screen">
            <div className="hidden sm:block">
                <SideBar />
            </div>
            <div className="sm:hidden">
                <SideBarMobile />
            </div>

            <div className="relative flex-1 flex justify-center items-center p-4">
                <img src={BackGround} className="fixed inset-0 w-full h-full object-cover -z-10" />

                <div className="w-full max-w-3xl backdrop-blur-[4px] bg-[#000b425e] border border-[#0066ff8c] shadow-[0_0_35px_rgba(0,183,255,0.2)] rounded-2xl p-4 sm:p-6 flex flex-col gap-4 h-[85vh]">

                    {/* CABEÇALHO */}
                    <div className="flex flex-wrap items-center justify-between border-b border-[#004bbb8c] pb-3 gap-2">
                        <div className="flex items-center gap-3">
                            <Bot className="w-9 h-9 text-[#39a6ff] drop-shadow-[1px_1px_12px_#39a6ff]" />
                            <div>
                                <h1 className="text-xl sm:text-2xl font-semibold font-ibm-plex text-[#ffffff] drop-shadow-[0_0_12px_#008cff]">
                                    ASSISTENTE CERBERUS IA
                                </h1>
                                <p className="text-xs font-rajdhani text-cyan-300/70">Comando de Voz & Automação Inteligente</p>
                            </div>
                        </div>

                        {/* BOTÕES DE AÇÃO NO TOPO */}
                        <div className="flex items-center gap-2 flex-wrap">
                            {/* BOTÃO 1: IR PARA HOME / DASHBOARD DO REACT */}
                            <button
                                onClick={() => navigate("/dashboard")}
                                type="button"
                                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-blue-600/20 hover:bg-blue-600/40 text-cyan-300 border border-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.25)] transition-all cursor-pointer text-xs sm:text-sm font-rajdhani font-semibold active:scale-95"
                                title="Voltar para a página inicial (DashBoard)"
                            >
                                <Home className="w-4 h-4 text-cyan-400" />
                                <span>DashBoard</span>
                            </button>

                            {/* BOTÃO 2: ALTERNAR DISPLAY FÍSICO DO ESP32 */}
                            {displayMode === "rosto" ? (
                                <button
                                    onClick={() => mudarTelaDisplay("home")}
                                    disabled={displayLoading}
                                    type="button"
                                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-cyan-600/20 hover:bg-cyan-600/40 text-cyan-300 border border-cyan-500/50 shadow-[0_0_15px_rgba(6,182,212,0.25)] transition-all cursor-pointer text-xs sm:text-sm font-rajdhani font-semibold active:scale-95 disabled:opacity-50"
                                    title="Alternar Display do ESP32 para a Tela Home"
                                >
                                    {displayLoading ? (
                                        <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
                                    ) : (
                                        <Monitor className="w-4 h-4 text-cyan-400" />
                                    )}
                                    <span>Display Home</span>
                                </button>
                            ) : (
                                <button
                                    onClick={() => mudarTelaDisplay("rosto")}
                                    disabled={displayLoading}
                                    type="button"
                                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/50 shadow-[0_0_15px_rgba(99,102,241,0.25)] transition-all cursor-pointer text-xs sm:text-sm font-rajdhani font-semibold active:scale-95 disabled:opacity-50"
                                    title="Voltar Display do ESP32 para o Rosto animado"
                                >
                                    {displayLoading ? (
                                        <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                                    ) : (
                                        <Smile className="w-4 h-4 text-indigo-400" />
                                    )}
                                    <span>Display Rosto</span>
                                </button>
                            )}

                            {/* BOTÃO 3: FAZER CARINHO */}
                            <button
                                onClick={sendCarinho}
                                disabled={loading}
                                type="button"
                                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-pink-600/20 hover:bg-pink-600/40 text-pink-300 border border-pink-500/50 shadow-[0_0_15px_rgba(236,72,153,0.3)] transition-all cursor-pointer disabled:opacity-50 text-xs sm:text-sm font-rajdhani font-semibold active:scale-95"
                                title="Fazer Carinho no Cerberus"
                            >
                                <Heart className="w-4 h-4 fill-pink-400 text-pink-400 animate-pulse" />
                                <span>Carinho</span>
                            </button>
                        </div>
                    </div>

                    {/* TOAST / FEEDBACK DO DISPLAY */}
                    {displayStatusMsg && (
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-[#091136]/95 border border-cyan-500/60 rounded-xl text-cyan-300 text-xs font-rajdhani shadow-[0_0_15px_#00f0ff44] animate-pulse self-end">
                            <Check className="w-3.5 h-3.5 text-cyan-400" />
                            <span>{displayStatusMsg}</span>
                        </div>
                    )}

                    {/* ÁREA DE MENSAGENS (CHAT) */}
                    <div className="flex-1 overflow-y-auto flex flex-col gap-3 p-2">
                        {messages.length === 0 && (
                            <div className="text-center text-cyan-200/50 my-auto font-rajdhani flex flex-col items-center gap-2">
                                <span>Digite um comando para o assistente Cerberus...</span>
                                <button
                                    onClick={sendCarinho}
                                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-pink-600/20 hover:bg-pink-600/40 text-pink-300 border border-pink-500/40 text-sm font-rajdhani cursor-pointer transition-all mt-2"
                                >
                                    <Heart className="w-4 h-4 fill-pink-400 text-pink-400" />
                                    <span>Dar carinho no Cerberus agora</span>
                                </button>
                            </div>
                        )}
                        {messages.map((msg, index) => (
                            <div
                                key={index}
                                className={`max-w-[80%] p-3 rounded-xl font-rajdhani text-sm sm:text-base ${msg.sender === "user"
                                    ? "ml-auto bg-[#0051d3]/80 text-white border border-[#008cff]"
                                    : "mr-auto bg-[#091136]/90 text-cyan-100 border border-cyan-800"
                                    }`}
                            >
                                {msg.text}
                            </div>
                        ))}
                        {loading && (
                            <div className="mr-auto bg-[#091136]/90 text-cyan-400 p-3 rounded-xl border border-cyan-800 flex items-center gap-2 font-rajdhani text-sm">
                                <Loader2 className="w-4 h-4 animate-spin text-[#00f0ff]" />
                                <span>Cerberus está processando...</span>
                            </div>
                        )}
                    </div>

                    {/* CAMPO DE DIGITAÇÃO + BOTÕES */}
                    <div className="flex items-center gap-2 border-t border-[#004bbb8c] pt-3">
                        <button
                            onClick={sendCarinho}
                            disabled={loading}
                            type="button"
                            className="p-2.5 rounded-xl bg-pink-600/20 hover:bg-pink-600/40 text-pink-300 border border-pink-500/50 shadow-[0_0_15px_rgba(236,72,153,0.25)] transition-all cursor-pointer disabled:opacity-50"
                            title="Fazer Carinho no Cerberus"
                        >
                            <Heart className="w-5 h-5 fill-pink-400 text-pink-400" />
                        </button>
                        <button
                            onClick={() => sendMessage("Mostre sua forma verdadeira agora, Cerberus!")}
                            disabled={loading}
                            type="button"
                            className="p-2.5 rounded-xl bg-red-600/20 hover:bg-red-600/40 text-red-400 border border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.25)] transition-all cursor-pointer disabled:opacity-50"
                            title="Despertar Forma Verdadeira (Cão de 3 Cabeças)"
                        >
                            <Flame className="w-5 h-5 fill-red-500 text-red-500 animate-pulse" />
                        </button>
                        <input
                            type="text"
                            value={inputMessage}
                            onChange={(e) => setInputMessage(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                            placeholder="Pergunte ou ordene algo ao Cerberus..."
                            className="flex-1 bg-[#091136]/80 border border-[#0077ff]/50 rounded-xl px-4 py-2.5 text-white placeholder-cyan-300/40 text-sm outline-none focus:border-[#00f0ff] focus:shadow-[0_0_15px_#00f0ffaa] transition-all font-rajdhani"
                        />
                        <button
                            onClick={() => sendMessage()}
                            disabled={loading}
                            className="p-2.5 rounded-xl bg-[#0051d3] hover:bg-[#0077ff] text-white border border-[#008cff] shadow-[0_0_15px_#0077ff] transition-all cursor-pointer disabled:opacity-50"
                        >
                            <Send className="w-5 h-5" />
                        </button>
                    </div>

                </div>
            </div>
        </div>
    );
}

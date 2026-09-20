import { useState } from "react";
import SideBar from "../Components/DashBoard/SideBar";
import SideBarMobile from "../Components/DashBoard/SideBarMobile";
import BackGround from "../assets/CerberusBackgroundMobile.jpg";
import { Bot, Send, Loader2 } from "lucide-react";

export default function Cerberus() {
    const [inputMessage, setInputMessage] = useState("");
    const [messages, setMessages] = useState<Array<{ sender: "user" | "bot"; text: string }>>([]);
    const [loading, setLoading] = useState(false);

    const BACKEND_URL = import.meta.env.VITE_BACKEND_URL
        ? `${import.meta.env.VITE_BACKEND_URL}/chat`
        : `http://${window.location.hostname}:8001/api/chat`;

    const sendMessage = async () => {
        if (!inputMessage.trim()) return;

        const userText = inputMessage;
        setMessages((prev) => [...prev, { sender: "user", text: userText }]);
        setInputMessage("");
        setLoading(true);

        try {
            const response = await fetch(BACKEND_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mensagem: userText }),
            });

            const data = await response.json();
            // Agora lê data.resposta:
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
                    <div className="flex items-center gap-3 border-b border-[#004bbb8c] pb-3">
                        <Bot className="w-9 h-9 text-[#39a6ff] drop-shadow-[1px_1px_12px_#39a6ff]" />
                        <div>
                            <h1 className="text-xl sm:text-2xl font-semibold font-ibm-plex text-[#ffffff] drop-shadow-[0_0_12px_#008cff]">
                                ASSISTENTE CERBERUS IA
                            </h1>
                            <p className="text-xs font-rajdhani text-cyan-300/70">Comando de Voz & Automação Inteligente</p>
                        </div>
                    </div>

                    {/* ÁREA DE MENSAGENS (CHAT) */}
                    <div className="flex-1 overflow-y-auto flex flex-col gap-3 p-2">
                        {messages.length === 0 && (
                            <div className="text-center text-cyan-200/50 my-auto font-rajdhani">
                                Digite um comando para o assistente Cerberus...
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
                            <div className="mr-auto flex items-center gap-2 p-3 bg-[#091136]/90 text-cyan-400 rounded-xl border border-cyan-800 text-sm font-rajdhani">
                                <Loader2 className="w-4 h-4 animate-spin text-[#0077ff]" />
                                <span>Cerberus está pensando...</span>
                            </div>
                        )}
                    </div>

                    {/* CAMPO DE DIGITAÇÃO + BOTÃO */}
                    <div className="flex items-center gap-2 border-t border-[#004bbb8c] pt-3">
                        <input
                            type="text"
                            value={inputMessage}
                            onChange={(e) => setInputMessage(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                            placeholder="Pergunte ou ordene algo ao Cerberus..."
                            className="flex-1 bg-[#091136]/80 border border-[#0077ff]/50 rounded-xl px-4 py-2.5 text-white placeholder-cyan-300/40 text-sm outline-none focus:border-[#00f0ff] focus:shadow-[0_0_15px_#00f0ffaa] transition-all font-rajdhani"
                        />
                        <button
                            onClick={sendMessage}
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

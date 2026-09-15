import { Skull } from "lucide-react";
import { useNavigate } from "react-router-dom"
import TelaDesenvolvimento from "../assets/TelaDesenvolvimento.png"
export default function Desenvolvimento() {
    const navigate = useNavigate();
    return (
        <div className="w-screen h-screen overflow-hidden">
            <img
                src={TelaDesenvolvimento}
                alt="Em Desenvolvimento"
                className="w-full h-full object-cover object-center"
            />
            <div className="fixed inset-0 bg-black/40" />
            <div className="absolute bottom-0 left-0 right-0 h-1/4 bg-linear-to-b from-transparent to-black opacity-50" />
            <div className="absolute inset-0 bg-linear-to-br from-transparent via-transparent to-[#2535cf]" />
            <div className="absolute inset-0 bg-linear-to-t from-black via-transparent to-transparent opacity-75" />
            <div className="absolute inset-0 flex items-start justify-center z-10 mt-10">
                <div className="relative flex flex-col gap-y- items-center">
                    <div className="backdrop-blur-[1px] border-b-1 border-r-1 from-linear-to-t to-[#020314] flex flex-col justify-center items-center gap-y-2 bg-linear-to-b from-[#0a116349] via-[#08105728] to-[#08105731] p-5 rounded-xl border-[#258db6] shadow-lg shadow-blue-500/50">
                        <h1 className="drop-shadow-[0px_0px_10px_#0877b8] font-ibm-plex text-6xl font-semibold text-[#0877b8]">
                            EM DESENVOLVIMENTO
                        </h1>
                        <div className="flex items-center gap-3">
                            <div className="drop-shadow-[0px_0px_10px_#0877b8] w-2.5 h-2.5 bg-[#00e5ff] rounded-full animate-ping duration-1000"></div>
                            <h2 className="font-ibm_plex font-bold text-[16px] drop-shadow-[0px_0px_10px_#0877b8] text-[#1087cc94]">
                                Volte Mais Tarde! Ou não

                            </h2>
                        </div>
                        <div className="flex items-center justify-center">

                        </div>
                    </div>
                    <button className="animate-pulse duration-700 mt-30 absolute bg-linear-to-b from-[#50bee988] via-[#0d1847b6] to-[#0d1847b6] text-white px-4 py-2 rounded-lg text-2xl font-bold  cursor-pointer whitespace-nowrap transition-all hover:scale-110 hover:bg-[#00c3ff9c] hover:drop-shadow-[0_0_5px_#00c3ff] hover:text-[#2caaff]"
                        onClick={() => navigate('/Dashboard')}>
                        Voltar Ao Dashboard
                    </button>
                </div>

            </div>
        </div >
    )
}

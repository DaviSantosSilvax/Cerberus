import { UserRound, KeyRound } from "lucide-react";
import DivisorL from "./LoginDivisor";
import { useNavigate } from "react-router-dom";

export default function LoginAba() {
    const navigate = useNavigate();

    return (
        <div className="w-full flex flex-col items-center">
            <div className="w-full flex flex-col items-center gap-1 sm:gap-1.5">
                <h1 className="text-2xl sm:text-4xl md:text-5xl text-[#ffffff] [text-shadow:0_0_20px_#6085ff] font-zen-dots font-bold text-center tracking-wider">
                    Cerberus
                </h1>

                <h2 className="text-[10px] sm:text-[13px] md:text-[15px] text-white [text-shadow:0_0_12px_#6085ff9d] font-rajdhani font-bold tracking-[0.2em] text-center">
                    HOME CONTROL APPLICATION
                </h2>

                <div className="w-full flex flex-col items-center gap-4 sm:gap-5 md:gap-6 mt-3 sm:mt-4">
                    <DivisorL />

                    <div className="w-full flex flex-col items-center gap-3.5 sm:gap-4 px-1">
                        <div className="w-full bg-[#112046] px-3 sm:px-4 py-2 sm:py-2.5 border border-[#1748a3] rounded-xl flex items-center gap-2.5 sm:gap-3 focus-within:border-[#6085ff] focus-within:shadow-[0_0_16px_#6085ffaa] focus-within:bg-[#152756] transition-all duration-200">
                            <UserRound
                                className="text-[#2563eb] drop-shadow-[0_0_6px_#3b82f6] shrink-0"
                                strokeWidth={2.2}
                                size={24}
                            />
                            <div className="h-7 sm:h-9 w-[2px] bg-[#1748a3] shadow-[0_0_8px_#6361fa] rounded-full shrink-0" />
                            <div className="flex-1 min-w-0">
                                <h1 className="text-[10px] sm:text-[12px] font-ibm-plex font-bold text-[#7ba9ff] tracking-wide">
                                    Usuário:
                                </h1>
                                <input
                                    type="text"
                                    placeholder="Digite seu usuário"
                                    className="w-full bg-transparent placeholder:text-[#a7a9c063] placeholder:text-[12px] sm:placeholder:text-[15px] text-white font-normal text-[13px] sm:text-[16px] outline-none"
                                />
                            </div>
                        </div>

                        <div className="w-full bg-[#112046] px-3 sm:px-4 py-2 sm:py-2.5 border border-[#1748a3] rounded-xl flex items-center gap-2.5 sm:gap-3 focus-within:border-[#6085ff] focus-within:shadow-[0_0_16px_#6085ffaa] focus-within:bg-[#152756] transition-all duration-200">
                            <KeyRound
                                className="text-[#2563eb] drop-shadow-[0_0_6px_#3b82f6] shrink-0"
                                strokeWidth={2.2}
                                size={24}
                            />
                            <div className="h-7 sm:h-9 w-[2px] bg-[#1748a3] shadow-[0_0_8px_#6361fa] rounded-full shrink-0" />
                            <div className="flex-1 min-w-0">
                                <h1 className="text-[10px] sm:text-[12px] font-ibm-plex font-bold text-[#7ba9ff] tracking-wide">
                                    Senha:
                                </h1>
                                <input
                                    type="password"
                                    placeholder="Digite sua senha"
                                    className="w-full bg-transparent placeholder:text-[#a7a9c063] placeholder:text-[12px] sm:placeholder:text-[15px] text-white font-normal text-[13px] sm:text-[16px] outline-none"
                                />
                            </div>
                        </div>

                        <button
                            className="w-full h-10 sm:h-12 bg-gradient-to-r from-[#1748a3] via-[#1d5adb] to-[#02156d] hover:from-[#1d5adb] hover:to-[#2563eb] text-white font-rajdhani font-bold text-[20px] sm:text-[25px] rounded-xl outline-none border border-[#1748a3] hover:border-[#6085ff] hover:shadow-[0_0_22px_#6085ff] active:scale-98 transition-all duration-200 cursor-pointer mt-1 sm:mt-2 tracking-wider"
                            onClick={() => { navigate('/Dashboard') }}
                        >
                            Entrar
                        </button>
                    </div>

                    <DivisorL />

                    <h1 className="text-[11px] sm:text-[14px] text-[#2563eb] drop-shadow-[0px_0px_10px_#152028] font-bold font-rajdhani tracking-[0.18em] text-center">
                        SUA CASA, SEU CONTROLE
                    </h1>
                </div>
            </div>
        </div>
    );
}

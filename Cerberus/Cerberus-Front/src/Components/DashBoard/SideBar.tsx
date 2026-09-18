import IconAll from "../../assets/CerberusLogoTwo.png"
import { House, Video, Snowflake, Lightbulb, AlarmClockCheck, Diamond, ShieldCheck, Music, FileClock, Cctv } from "lucide-react"
import { useLocation, useNavigate } from "react-router-dom"

export default function SideBar() {
    const location = useLocation()
    const navigate = useNavigate()
    const sideBarItems = [
        { id: "Dashboard", label: "Dashboard", icon: House, rota: "/dashboard" },
        { id: "Câmeras", label: "Câmeras", icon: Cctv, rota: "/cameras" },
        { id: "Climatização", label: "Climatização", icon: Snowflake, rota: "/climatizacao" },
        { id: "Iluminação", label: "Iluminação", icon: Lightbulb, rota: "/iluminacao" },
        { id: "Alarmes", label: "Alarmes", icon: AlarmClockCheck, rota: "/desenvolvimento" },
        { id: "Músicas", label: "Músicas", icon: Music, rota: "/desenvolvimento" },
        { id: "Log", label: "Log", icon: FileClock, rota: "/desenvolvimento" },
    ];

    return (
        <div className="backdrop-blur-[100px] shadow-[10px_0_30px_rgba(15,124,250,0.15)] gap-6 sm: md:gap-10 w-full md:w-80 shrink-0 flex flex-col items-center md:h-screen border-b-2 md:border-b-0 md:border-r-2 border-[#2920d6] bg-linear-to-br from-[#0e0ed1] via-[#06023b] to-[#080536] pb-4 md:pb-0">
            <div className="group cursor-pointer hover:scale-110 flex flex-col items-center gap-10">
                <img
                    src={IconAll}
                    alt="Cerberus Logo"
                    className="group-hover:scale-105 group-hover:drop-shadow-[0_0_20px_#ff505079] group-hover:duration-200 mt-5 w-45 sm:w-45 md:w-45 lg:w-45 h-auto z-20 drop-shadow-[0_0_18px_#6085ff]  -mb-8 sm:-mb-10 md:-mb-12 relative"
                />
                <h1 className="group-hover:scale-86 group-hover:text-[#ffc7c779] group-hover:duration-200 text-3xl md:text-3xl lg:text-3xl font-zen-dots text-[#ffffff] [-w] [text-shadow:0_0_20px_#5e57e2]  font-bold text-center tracking-wider">
                    Cerberus
                </h1>

            </div>
            <div className="w-full flex items-center justify-center gap-2 px-4">
                <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent  via-[#143fff] to-[#6085ff]" />
                <Diamond className="text-[#6085ff] drop-shadow-[0_0_8px_#6085ff] shrink-0" size={14} fill="#143fff" />
                <div className="h-[1px] flex-1 bg-gradient-to-l from-transparent via-[#143fff] to-[#6085ff]" />
            </div>
            <div className="w-full flex-1 flex flex-col items-center gap-5 pb-4">
                {sideBarItems.map((item) => {
                    const IconComponent = item.icon;
                    const isActive = location.pathname === item.rota;

                    return (
                        <div
                            key={item.id}
                            onClick={() => navigate(item.rota)}
                            className={`group cursor-pointer w-full flex items-center gap-7 px-3 py-2.5 transition-all hover:border-l-4 hover:border-l-[#0051d3] hover:rounded-l-xl ${isActive
                                ? "rounded-lg bg-gradient-to-r from-[#55a1ff3b] via-[#002fff48] to-[#001152ab] text-white shadow-[0_0_12px_#1260f1d3] border-l-4 border-[#0051d3]"
                                : "hover:rounded-[5px] hover:bg-linear-to-r from-[#1260f193] via-[#2c26cf] to-[#05165e]"
                                }`}
                        >
                            <IconComponent
                                className={`ml-4 group-hover:scale-112 group-hover:duration-200 ${isActive ? "text-[#64c6ff] drop-shadow-[0_0_5px_#64c6ff]" : "text-[#308ec5]"
                                    }`}
                                strokeWidth={2}
                                size={35}
                            />
                            <button
                                className={`text-lg cursor-pointer font-semibold group-hover:scale-102 group-hover:duration-200 ${isActive ? "text-[#64c6ff] drop-shadow-[0_0_7px_#64c6ff]" : "text-[#308ec5]"
                                    }`}
                            >
                                {item.label}
                            </button>

                        </div>
                    );
                })}

                <div className="mt-auto w-full px-4 pt-4 border-t border-[#171d6b55]">
                    <div className="bg-[#111942]/80 border border-[#1748a355] rounded-xl p-3 flex items-center gap-3">
                        <ShieldCheck className="text-[#00b7ff] drop-shadow-[0_0_8px_#00f0ff]" size={24} />
                        <div className="flex flex-col">
                            <span className="text-[10px] font-ibm-plex text-[#a8e6ff] uppercase tracking-wider">Status do Sistema</span>
                            <div className="w-full flex flex-row gap-3">
                                <span className="text-[13px] font-rajdhani font-bold text-[#00b7ff] tracking-widest flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-[#00b7ff] animate-pulse" />
                                    ONLINE
                                </span>
                                <span className="text-[13px] font-rajdhani font-bold text-[#00b7ff] tracking-widest flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-[#00b7ff] animate-pulse" />
                                    SEGURO
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

import IconAll from "../../assets/CerberusLogoTwo.png"
import { House, Video, Snowflake, Lightbulb, AlarmClockCheck, Diamond, ShieldCheck, Music, FileClock, Cctv } from "lucide-react"
import { useLocation, useNavigate } from "react-router-dom"

export default function SideBar() {
    const location = useLocation()
    const navigate = useNavigate()
    const sideBarItems = [
        { id: "Iluminação", label: "Iluminação", icon: Lightbulb, rota: "/iluminacao" },
        { id: "Climatização", label: "Climatização", icon: Snowflake, rota: "/climatizacao" },
        { id: "Câmeras", label: "Câmeras", icon: Cctv, rota: "/cameras" },
        { id: "Dashboard", label: "Dashboard", icon: House, rota: "/dashboard" },
        { id: "Alarmes", label: "Alarmes", icon: AlarmClockCheck, rota: "/desenvolvimento" },
        { id: "Músicas", label: "Músicas", icon: Music, rota: "/desenvolvimento" },
        { id: "Log", label: "Log", icon: FileClock, rota: "/desenvolvimento" },
    ];
    return (
        <div className="z-50 fixed bottom-0 left-0 w-full bg-[#000b425e] border-t border-[#0066ff8c] p-1">
            <div className="flex justify-around">
                {sideBarItems.map((item) => {
                    const Icon = item.icon;
                    return (
                        <button
                            key={item.id}
                            onClick={() => navigate(item.rota)}
                            className={`flex flex-col items-center p-2 rounded-lg transition-all ${location.pathname === item.rota
                                ? "text-[#39a6ff] bg-[#0066ff2c] drop-shadow-[1px_1px_12px_#39a6ff]"
                                : "text-white hover:text-[#39a6ff] hover:bg-[#0066ff2c]"
                                }`}
                        >
                            <Icon className="w-6 h-6" strokeWidth={1.5} />
                            <span className="text-[10px] mt-1">{item.label}</span>
                        </button>
                    );
                })}
            </div>
        </div>
    )
}

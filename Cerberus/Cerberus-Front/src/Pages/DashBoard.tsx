import backgroundCerberus from "../assets/CerberusBackground.png";
import SideBar from "../Components/DashBoard/SideBar";
import SideBarMobile from "../Components/DashBoard/SideBarMobile";

export default function DashBoard() {
    return (
        <div
            className="relative min-h-screen w-full flex flex-col md:flex-row bg-cover bg-center overflow-x-hidden"
            style={{ backgroundImage: `url(${backgroundCerberus})` }}
        >
            <div className="hidden sm:block">
                <SideBar />
            </div>
            <div className="sm:hidden">
                <SideBarMobile />
            </div>
            <div className="flex-1 p-6 sm:p-8 flex flex-col justify-center items-center text-center text-white">
                <h1 className="text-3xl sm:text-5xl font-bold font-zen-dots drop-shadow-[0_0_15px_#6085ff]">
                    DashBoard
                </h1>
                <p className="font-rajdhani text-cyan-200/70 text-sm sm:text-base mt-2 tracking-wider uppercase">
                    Painel Principal • Cerberus Home Control
                </p>
            </div>
        </div>
    );
}
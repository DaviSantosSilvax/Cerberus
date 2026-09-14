import LoginAba from "./LoginInfo"
import IconAll from "../../assets/IconAll.png"

export default function ContainerLogin() {
    return (
        <div className="relative w-full max-w-[360px] sm:max-w-[440px] md:max-w-[480px] lg:max-w-[520px] flex flex-col items-center my-auto mr-[15%] mb-[15%]">
            <img
                src={IconAll}
                alt="Cerberus Logo"
                className="w-48 sm:w-56 md:w-64 lg:w-72 h-auto z-20 drop-shadow-[0_0_18px_#6085ff] pointer-events-none -mb-8 sm:-mb-10 md:-mb-12 relative"
            />

            <div className="w-full bg-[#090c24e6] backdrop-blur-md rounded-3xl border-2 border-[#171d6b9c] shadow-[0_0_40px_rgba(15,124,250,0.25),inset_0_0_20px_rgba(23,29,107,0.4)] p-2.5 sm:p-3 md:p-4 transition-all duration-300">
                <div className="w-full flex flex-col items-center justify-start pt-10 sm:pt-12 md:pt-14 pb-5 sm:pb-7 px-4 sm:px-6 md:px-8 rounded-2xl border-l border-b border-[#3337779c] shadow-xl shadow-[#2940c240]">
                    <LoginAba />
                </div>
            </div>
        </div>
    )
}



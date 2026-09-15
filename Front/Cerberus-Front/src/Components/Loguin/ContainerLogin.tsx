import LoginAba from "./LoginInfo";
import IconAll from "../../assets/IconAll.png";

export default function ContainerLogin() {
    return (
        <div className="relative w-full max-w-[340px] sm:max-w-[440px] md:max-w-[480px] flex flex-col items-center my-auto lg:-mt-4 lg:translate-x-27">
            <img
                src={IconAll}
                alt="Cerberus Logo"
                className="w-40 sm:w-56 md:w-64 h-auto z-20 drop-shadow-[0_0_18px_#6085ff] pointer-events-none -mb-6 sm:-mb-10 md:-mb-12 relative"
            />

            <div className="w-full bg-[#090c24e6] backdrop-blur-md rounded-3xl border-2 border-[#171d6b9c] shadow-[0_0_40px_rgba(15,124,250,0.25),inset_0_0_20px_rgba(23,29,107,0.4)] p-2.5 sm:p-4 transition-all duration-300">
                <div className="w-full flex flex-col items-center justify-start pt-8 sm:pt-12 pb-5 sm:pb-7 px-4 sm:px-6 rounded-2xl border-l border-b border-[#3337779c] shadow-xl shadow-[#2940c240]">
                    <LoginAba />
                </div>
            </div>
        </div>
    );
}

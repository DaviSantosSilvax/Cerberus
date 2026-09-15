import { Diamond } from "lucide-react";

export default function DivisorL() {
    return (
        <div className="w-full flex items-center justify-center gap-2 my-2 px-4">
            <div className="h-[2px] flex-1 bg-gradient-to-r from-transparent via-[#143fff] to-[#6085ff] shadow-[0_0_10px_#6085ff]" />
            <Diamond className="text-[#1a6af5] drop-shadow-[0_0_13px_#00f0ff] shrink-0" fill="#0045bb" color="#143fff" size={20} strokeWidth={2} />
            <div className="h-[2px] flex-1 bg-gradient-to-l from-transparent via-[#143fff] to-[#6085ff] shadow-[0_0_10px_#6085ff]" />
        </div>
    )
}
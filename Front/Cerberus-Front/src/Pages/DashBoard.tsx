import SideBar from "../Components/DashBoard/SideBar";

export default function DashBoard() {
    return (
        <div className="w-full flex h-screen bg-gradient-to-br from-[#232361] to-[#10104d] via-[hsla(246,73%,22%,1)]">
            <SideBar />
            <div className="flex flex-col justify-center items-center w-full h-screen bg-linear-to-br from-[#101057] to-[#140d66] via-[#151563]">
                <h1 className="text-white text-5xl font-bold">DashBoard</h1>
            </div>
        </div>
    )
}
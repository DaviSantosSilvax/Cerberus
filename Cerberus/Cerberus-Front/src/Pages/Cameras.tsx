import SideBar from '../Components/DashBoard/SideBar'
import SideBarMobile from '../Components/DashBoard/SideBarMobile'
import Background from '../assets/CerberusBackground.png'
import { Cctv, Video } from 'lucide-react'

export default function Cameras() {
    return (
        <div className="flex">
            <div className="hidden sm:block">
                <SideBar />
            </div>
            <div className="sm:hidden">
                <SideBarMobile />
            </div>
            <img src={Background} alt="Background" className="fixed inset-0 w-full h-full object-cover object-center -z-10" />
            <div className="flex-1">
                <div className="w-full max-w-3xl h-[50vh] backdrop-blur-[4px] bg-[#000b425e] border border-[#0066ff8c] shadow-[0_0_35px_rgba(0,183,255,0.2)] rounded-2xl sm:rounded-4xl p-4 sm:p-8 flex flex-col gap-6 sm:gap-8">
                    <div className="">

                    </div>


                    <div className="p-4 flex items-center gap-4">
                        <Video className="w-14 h-14 text-[#39a6ff] drop-shadow-[1px_1px_12px_#39a6ff]" strokeWidth={1.5} />
                        <h1 className="text-4xl sm:text-5xl font-semibold font-ibm-plex drop-shadow-[0_0_12px_#008cff] text-[#ffffff]">Cameras</h1>

                    </div>
                </div>
            </div>
        </div>
    )
}


import backGround from "../assets/CerberusLoginBackground.png"
import ContainerLogin from "../Components/Loguin/ContainerLogin"

export default function Login() {
    return (
        <div 
            className="h-screen w-screen overflow-hidden bg-cover bg-center flex items-center justify-center lg:justify-end p-4 md:p-8 lg:pr-[7%] xl:pr-[10%]" 
            style={{ backgroundImage: `url(${backGround})` }}
        >
            <ContainerLogin />
        </div>
    )
}
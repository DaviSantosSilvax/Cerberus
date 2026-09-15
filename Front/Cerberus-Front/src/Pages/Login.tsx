import backGround from "../assets/CerberusLoginBackground.png";
import ContainerLogin from "../Components/Loguin/ContainerLogin";

export default function Login() {
    return (
        <div 
            className="min-h-screen w-full bg-cover bg-center flex items-center justify-center p-4 py-8 overflow-y-auto" 
            style={{ backgroundImage: `url(${backGround})` }}
        >
            <ContainerLogin />
        </div>
    );
}
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Login from './Pages/Login'
import DashBoard from './Pages/DashBoard'
import Desenvolvimento from './Pages/Desenvolvimento'
import Iluminacao from './Pages/Iluminação'
import Climatizacao from './Pages/Climatização'
import Cameras from './Pages/Cameras'
import Cerberus from './Pages/Cerberus'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/dashboard" element={<DashBoard />} />
        <Route path="/desenvolvimento" element={<Desenvolvimento />} />
        <Route path="/iluminacao" element={<Iluminacao />} />
        <Route path="/climatizacao" element={<Climatizacao />} />
        <Route path="/cameras" element={<Cameras />} />
        <Route path="/cerberus" element={<Cerberus />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>)
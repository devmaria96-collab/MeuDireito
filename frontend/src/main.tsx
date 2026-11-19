import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { PortaoHomologacao } from "./components/PortaoHomologacao.tsx";
import App from "./App.tsx";
import "./index.css";

const raiz = document.getElementById("root");
if (!raiz) {
  throw new Error("Não foi possível iniciar a interface.");
}

createRoot(raiz).render(
  <StrictMode>
    <PortaoHomologacao>
      <App />
    </PortaoHomologacao>
  </StrictMode>,
);

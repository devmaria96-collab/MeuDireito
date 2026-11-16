import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

const raiz = document.getElementById("root");
if (!raiz) {
  throw new Error("Não foi possível iniciar a interface.");
}

createRoot(raiz).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

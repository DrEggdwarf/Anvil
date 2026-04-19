import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

type Mode = "ASM" | "RE" | "Pwn" | "Debug" | "Firmware" | "Protocols";

function App() {
  const [mode, setMode] = useState<Mode>("ASM");
  const [backendStatus, setBackendStatus] = useState<string>("checking...");

  async function checkBackend() {
    try {
      const ok = await invoke<boolean>("check_backend");
      setBackendStatus(ok ? "connected" : "unreachable");
    } catch {
      setBackendStatus("error");
    }
  }

  return (
    <main className="anvil-app">
      <header className="anvil-header">
        <h1 className="anvil-title">Anvil</h1>
        <nav className="anvil-modes" role="tablist" aria-label="Modes">
          {(["ASM", "RE", "Pwn", "Debug", "Firmware", "Protocols"] as Mode[]).map((m) => (
            <button
              key={m}
              role="tab"
              aria-selected={mode === m}
              className={`anvil-mode-btn ${mode === m ? "anvil-mode-btn--active" : ""}`}
              onClick={() => setMode(m)}
            >
              {m}
            </button>
          ))}
        </nav>
        <div className="anvil-status">
          <span className={`anvil-status-dot anvil-status-dot--${backendStatus === "connected" ? "ok" : "err"}`} />
          <button className="anvil-status-btn" onClick={checkBackend}>
            Backend: {backendStatus}
          </button>
        </div>
      </header>

      <section className="anvil-workspace">
        <p className="anvil-placeholder">Mode: {mode} — workspace vide</p>
      </section>
    </main>
  );
}

export default App;

use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;

struct BackendProcess(Mutex<Option<Child>>);

/// Check if the backend is reachable.
#[tauri::command]
async fn check_backend() -> Result<bool, String> {
    let resp = reqwest::get("http://localhost:8000/api/health").await;
    Ok(resp.is_ok())
}

/// Get dependency status from the backend.
#[tauri::command]
async fn check_dependencies() -> Result<serde_json::Value, String> {
    let resp = reqwest::get("http://localhost:8000/api/health/detailed")
        .await
        .map_err(|e| e.to_string())?;
    let body: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
    Ok(body)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            // Launch FastAPI backend as subprocess
            // Uses backend.app.main:app from project root so `backend.*` imports resolve
            let project_root = app.path()
                .resource_dir()
                .unwrap_or_default();
            let child = Command::new("uvicorn")
                .args(["backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"])
                .current_dir(&project_root)
                .env("PYTHONPATH", &project_root)
                .spawn();

            match child {
                Ok(process) => {
                    app.manage(BackendProcess(Mutex::new(Some(process))));
                }
                Err(e) => {
                    eprintln!("Failed to start backend: {e}");
                    app.manage(BackendProcess(Mutex::new(None)));
                }
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![check_backend, check_dependencies])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                // Kill backend subprocess on exit
                if let Some(state) = app.try_state::<BackendProcess>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(ref mut child) = *guard {
                            let _ = child.kill();
                        }
                    }
                }
            }
        });
}

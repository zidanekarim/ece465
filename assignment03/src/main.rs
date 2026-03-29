use axum::{
    extract::Multipart,
    routing::{get, post},
    response::IntoResponse,
    http::StatusCode,
    Router,
};
use serde::{Deserialize, Serialize};
use reqwest::Client;
#[tokio::main] 
async fn main() {
    let app = Router::new()
        .route("/", get(|| async { "Listening" }))
        .route("/api/upload", post(upload))
        .route("/api/status", get(status));
    let listener = tokio::net::TcpListener::bind("0.0.0.0:7676").await.unwrap() ;
    axum::serve(listener, app).await.unwrap();
}
async fn status() -> impl IntoResponse {
    let client = reqwest::Client::new();
    let url = "http://master-service:8000/nodes";

    match client.get(url).send().await {
        Ok(res) => {
            let status = res.status();
            let body = res.text().await.unwrap_or_default();
            (status, body).into_response()
        }
        Err(_) => (StatusCode::BAD_GATEWAY, "Master service unreachable").into_response(),
    }
}

async fn upload(mut multipart: Multipart) -> impl IntoResponse {
    let client = reqwest::Client::new();
    let url = "http://master-service:8000/upload";
    let mut form = reqwest::multipart::Form::new();

    while let Ok(Some(field)) = multipart.next_field().await {
        let name = field.name().unwrap_or("file").to_string();
        let file_name = field.file_name().unwrap_or("image.png").to_string();
        let data = field.bytes().await.unwrap_or_default();

        let part = reqwest::multipart::Part::bytes(data.to_vec()).file_name(file_name);
        form = form.part(name, part);
    }

    match client.post(url).multipart(form).send().await {
        Ok(res) => {
            let status = res.status();
            let body = res.text().await.unwrap_or_default();
            (status, body).into_response()
        }
        Err(_) => (StatusCode::BAD_GATEWAY, "Failed to forward to Master").into_response(),
    }
}
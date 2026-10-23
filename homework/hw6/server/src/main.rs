use std::env;

use tokio::net::TcpListener;

#[tokio::main]
async fn main() {
    let port: u16 = env::var("PORT").ok().and_then(|p| p.parse().ok()).unwrap_or(3000);
    let static_dir = env::var("STATIC_DIR")
        .unwrap_or_else(|_| concat!(env!("CARGO_MANIFEST_DIR"), "/../client").to_string());

    let listener = TcpListener::bind(("127.0.0.1", port)).await.unwrap();
    println!("Todo server listening on http://127.0.0.1:{port}");
    axum::serve(listener, todo_server::app(static_dir)).await.unwrap();
}

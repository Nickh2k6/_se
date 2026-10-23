//! HTTP 層：把 `todo::TodoStore` 包成 REST API，並提供 client/ 的靜態檔案。

pub mod todo;

use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::routing::{delete, get};
use axum::{Json, Router};
use serde::Deserialize;
use serde_json::json;
use tower_http::services::ServeDir;

use todo::{Filter, Stats, Todo, TodoError, TodoStore};

type SharedStore = Arc<Mutex<TodoStore>>;

impl IntoResponse for TodoError {
    fn into_response(self) -> Response {
        let status = match self {
            TodoError::EmptyTitle | TodoError::TitleTooLong => StatusCode::BAD_REQUEST,
            TodoError::NotFound => StatusCode::NOT_FOUND,
        };
        (status, Json(json!({ "error": self.message() }))).into_response()
    }
}

#[derive(Deserialize)]
struct ListQuery {
    #[serde(default)]
    filter: Filter,
}

#[derive(Deserialize)]
struct CreateTodo {
    title: String,
}

#[derive(Deserialize)]
struct UpdateTodo {
    title: Option<String>,
    completed: Option<bool>,
}

/// 建立整個應用程式的 Router。`static_dir` 是前端檔案所在的資料夾。
pub fn app(static_dir: impl Into<PathBuf>) -> Router {
    let store: SharedStore = Arc::new(Mutex::new(TodoStore::new()));
    Router::new()
        .route("/api/health", get(health))
        .route("/api/stats", get(stats))
        .route("/api/todos", get(list_todos).post(create_todo))
        .route("/api/todos/completed", delete(clear_completed))
        .route(
            "/api/todos/{id}",
            get(get_todo).patch(update_todo).delete(delete_todo),
        )
        .with_state(store)
        .fallback_service(ServeDir::new(static_dir.into()))
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok" }))
}

async fn stats(State(store): State<SharedStore>) -> Json<Stats> {
    Json(store.lock().unwrap().stats())
}

async fn list_todos(
    State(store): State<SharedStore>,
    Query(q): Query<ListQuery>,
) -> Json<Vec<Todo>> {
    Json(store.lock().unwrap().list(q.filter))
}

async fn create_todo(
    State(store): State<SharedStore>,
    Json(body): Json<CreateTodo>,
) -> Result<(StatusCode, Json<Todo>), TodoError> {
    let todo = store.lock().unwrap().add(&body.title)?;
    Ok((StatusCode::CREATED, Json(todo)))
}

async fn get_todo(
    State(store): State<SharedStore>,
    Path(id): Path<u64>,
) -> Result<Json<Todo>, TodoError> {
    let store = store.lock().unwrap();
    store.get(id).cloned().map(Json).ok_or(TodoError::NotFound)
}

async fn update_todo(
    State(store): State<SharedStore>,
    Path(id): Path<u64>,
    Json(body): Json<UpdateTodo>,
) -> Result<Json<Todo>, TodoError> {
    let todo = store
        .lock()
        .unwrap()
        .update(id, body.title.as_deref(), body.completed)?;
    Ok(Json(todo))
}

async fn delete_todo(
    State(store): State<SharedStore>,
    Path(id): Path<u64>,
) -> Result<StatusCode, TodoError> {
    store.lock().unwrap().remove(id)?;
    Ok(StatusCode::NO_CONTENT)
}

async fn clear_completed(State(store): State<SharedStore>) -> Json<serde_json::Value> {
    let removed = store.lock().unwrap().clear_completed();
    Json(json!({ "removed": removed }))
}

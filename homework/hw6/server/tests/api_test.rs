//! 系統測試（Web API 測試）
//!
//! 每個測試都在隨機 port 上啟動一個「真的」HTTP 伺服器，再用 reqwest
//! 像外部客戶端一樣送 HTTP 請求，檢查狀態碼、標頭與 JSON 內容。
//! 每個測試各自一台伺服器，所以資料互不干擾，可以平行跑。

use reqwest::{Client, StatusCode};
use serde_json::{json, Value};
use tokio::net::TcpListener;

struct TestServer {
    base: String,
    http: Client,
}

impl TestServer {
    async fn start() -> Self {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        let static_dir = concat!(env!("CARGO_MANIFEST_DIR"), "/../client");
        tokio::spawn(async move {
            axum::serve(listener, todo_server::app(static_dir)).await.unwrap();
        });
        Self { base: format!("http://{addr}"), http: Client::new() }
    }

    fn url(&self, path: &str) -> String {
        format!("{}{}", self.base, path)
    }

    async fn create(&self, title: &str) -> Value {
        let res = self
            .http
            .post(self.url("/api/todos"))
            .json(&json!({ "title": title }))
            .send()
            .await
            .unwrap();
        assert_eq!(res.status(), StatusCode::CREATED);
        res.json().await.unwrap()
    }

    async fn get_json(&self, path: &str) -> (StatusCode, Value) {
        let res = self.http.get(self.url(path)).send().await.unwrap();
        let status = res.status();
        (status, res.json().await.unwrap_or(Value::Null))
    }
}

#[tokio::test]
async fn health_check_returns_ok() {
    let s = TestServer::start().await;
    let (status, body) = s.get_json("/api/health").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn list_is_empty_on_fresh_server() {
    let s = TestServer::start().await;
    let (status, body) = s.get_json("/api/todos").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!([]));
}

#[tokio::test]
async fn create_returns_201_with_new_todo_and_json_content_type() {
    let s = TestServer::start().await;
    let res = s
        .http
        .post(s.url("/api/todos"))
        .json(&json!({ "title": "  買牛奶  " }))
        .send()
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::CREATED);
    assert_eq!(res.headers()["content-type"], "application/json");
    let body: Value = res.json().await.unwrap();
    assert_eq!(body, json!({ "id": 1, "title": "買牛奶", "completed": false }));
}

#[tokio::test]
async fn create_with_blank_title_returns_400_and_error_message() {
    let s = TestServer::start().await;
    let res = s
        .http
        .post(s.url("/api/todos"))
        .json(&json!({ "title": "   " }))
        .send()
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
    let body: Value = res.json().await.unwrap();
    assert_eq!(body["error"], "標題不可為空白");
}

#[tokio::test]
async fn create_with_too_long_title_returns_400() {
    let s = TestServer::start().await;
    let res = s
        .http
        .post(s.url("/api/todos"))
        .json(&json!({ "title": "a".repeat(101) }))
        .send()
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn create_with_malformed_body_is_rejected() {
    let s = TestServer::start().await;

    // 缺少 title 欄位 → axum 的 Json extractor 回 422
    let res = s
        .http
        .post(s.url("/api/todos"))
        .json(&json!({ "name": "x" }))
        .send()
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::UNPROCESSABLE_ENTITY);

    // 根本不是 JSON → 400
    let res = s
        .http
        .post(s.url("/api/todos"))
        .header("content-type", "application/json")
        .body("{not json")
        .send()
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);

    // 沒有 content-type → 415
    let res = s
        .http
        .post(s.url("/api/todos"))
        .body(r#"{"title":"x"}"#)
        .send()
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::UNSUPPORTED_MEDIA_TYPE);
}

#[tokio::test]
async fn get_single_todo_and_404_for_missing() {
    let s = TestServer::start().await;
    s.create("寫作業").await;

    let (status, body) = s.get_json("/api/todos/1").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["title"], "寫作業");

    let (status, body) = s.get_json("/api/todos/999").await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "找不到這個待辦事項");
}

#[tokio::test]
async fn non_numeric_id_returns_400() {
    let s = TestServer::start().await;
    let res = s.http.get(s.url("/api/todos/abc")).send().await.unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn patch_updates_fields_and_persists() {
    let s = TestServer::start().await;
    s.create("買牛奶").await;

    let res = s
        .http
        .patch(s.url("/api/todos/1"))
        .json(&json!({ "completed": true }))
        .send()
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let body: Value = res.json().await.unwrap();
    assert_eq!(body, json!({ "id": 1, "title": "買牛奶", "completed": true }));

    // 再 GET 一次，確認是真的存進去了
    let (_, body) = s.get_json("/api/todos/1").await;
    assert_eq!(body["completed"], true);

    let res = s
        .http
        .patch(s.url("/api/todos/1"))
        .json(&json!({ "title": "買豆漿" }))
        .send()
        .await
        .unwrap();
    let body: Value = res.json().await.unwrap();
    assert_eq!(body, json!({ "id": 1, "title": "買豆漿", "completed": true }));
}

#[tokio::test]
async fn patch_errors() {
    let s = TestServer::start().await;
    s.create("買牛奶").await;

    let res = s
        .http
        .patch(s.url("/api/todos/1"))
        .json(&json!({ "title": "" }))
        .send()
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);

    let res = s
        .http
        .patch(s.url("/api/todos/42"))
        .json(&json!({ "completed": true }))
        .send()
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn delete_returns_204_then_404() {
    let s = TestServer::start().await;
    s.create("運動").await;

    let res = s.http.delete(s.url("/api/todos/1")).send().await.unwrap();
    assert_eq!(res.status(), StatusCode::NO_CONTENT);
    assert_eq!(res.text().await.unwrap(), "");

    let res = s.http.delete(s.url("/api/todos/1")).send().await.unwrap();
    assert_eq!(res.status(), StatusCode::NOT_FOUND);

    let (_, body) = s.get_json("/api/todos").await;
    assert_eq!(body, json!([]));
}

#[tokio::test]
async fn filter_query_and_stats() {
    let s = TestServer::start().await;
    for title in ["A", "B", "C"] {
        s.create(title).await;
    }
    s.http
        .patch(s.url("/api/todos/2"))
        .json(&json!({ "completed": true }))
        .send()
        .await
        .unwrap();

    let (_, active) = s.get_json("/api/todos?filter=active").await;
    let titles: Vec<_> = active.as_array().unwrap().iter().map(|t| t["title"].clone()).collect();
    assert_eq!(titles, [json!("A"), json!("C")]);

    let (_, done) = s.get_json("/api/todos?filter=completed").await;
    assert_eq!(done.as_array().unwrap().len(), 1);

    let (_, stats) = s.get_json("/api/stats").await;
    assert_eq!(stats, json!({ "total": 3, "active": 2, "completed": 1 }));

    // 不認得的 filter 值 → 400
    let res = s.http.get(s.url("/api/todos?filter=done")).send().await.unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn clear_completed_endpoint() {
    let s = TestServer::start().await;
    for title in ["A", "B", "C"] {
        s.create(title).await;
    }
    for id in [1, 3] {
        s.http
            .patch(s.url(&format!("/api/todos/{id}")))
            .json(&json!({ "completed": true }))
            .send()
            .await
            .unwrap();
    }

    let res = s.http.delete(s.url("/api/todos/completed")).send().await.unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let body: Value = res.json().await.unwrap();
    assert_eq!(body, json!({ "removed": 2 }));

    let (_, list) = s.get_json("/api/todos").await;
    assert_eq!(list, json!([{ "id": 2, "title": "B", "completed": false }]));
}

#[tokio::test]
async fn wrong_method_returns_405() {
    let s = TestServer::start().await;
    let res = s.http.put(s.url("/api/todos")).send().await.unwrap();
    assert_eq!(res.status(), StatusCode::METHOD_NOT_ALLOWED);
}

#[tokio::test]
async fn serves_frontend_static_files() {
    let s = TestServer::start().await;
    let res = s.http.get(s.url("/")).send().await.unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    assert!(res.headers()["content-type"].to_str().unwrap().starts_with("text/html"));
    assert!(res.text().await.unwrap().contains("<title>Todo"));

    let res = s.http.get(s.url("/app.js")).send().await.unwrap();
    assert_eq!(res.status(), StatusCode::OK);

    let res = s.http.get(s.url("/no-such-file.txt")).send().await.unwrap();
    assert_eq!(res.status(), StatusCode::NOT_FOUND);
}

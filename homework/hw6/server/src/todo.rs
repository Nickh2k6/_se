//! 待辦事項的商業邏輯（純資料結構，不碰 HTTP），單元測試都寫在這個檔案最下面。

use serde::{Deserialize, Serialize};

/// 標題最多幾個字（以 Unicode 字元計算，中文一個字算一個）
pub const MAX_TITLE_LEN: usize = 100;

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Todo {
    pub id: u64,
    pub title: String,
    pub completed: bool,
}

#[derive(Debug, PartialEq)]
pub enum TodoError {
    EmptyTitle,
    TitleTooLong,
    NotFound,
}

impl TodoError {
    pub fn message(&self) -> String {
        match self {
            TodoError::EmptyTitle => "標題不可為空白".to_string(),
            TodoError::TitleTooLong => format!("標題不可超過 {MAX_TITLE_LEN} 個字"),
            TodoError::NotFound => "找不到這個待辦事項".to_string(),
        }
    }
}

/// 列表篩選條件，對應 `?filter=all|active|completed`
#[derive(Debug, Clone, Copy, Default, PartialEq, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Filter {
    #[default]
    All,
    Active,
    Completed,
}

impl Filter {
    fn matches(self, todo: &Todo) -> bool {
        match self {
            Filter::All => true,
            Filter::Active => !todo.completed,
            Filter::Completed => todo.completed,
        }
    }
}

#[derive(Debug, PartialEq, Serialize)]
pub struct Stats {
    pub total: usize,
    pub active: usize,
    pub completed: usize,
}

/// 去掉前後空白後檢查標題是否合法，回傳整理過的標題
pub fn validate_title(raw: &str) -> Result<String, TodoError> {
    let title = raw.trim();
    if title.is_empty() {
        return Err(TodoError::EmptyTitle);
    }
    if title.chars().count() > MAX_TITLE_LEN {
        return Err(TodoError::TitleTooLong);
    }
    Ok(title.to_string())
}

pub struct TodoStore {
    todos: Vec<Todo>,
    next_id: u64,
}

impl Default for TodoStore {
    fn default() -> Self {
        Self::new()
    }
}

impl TodoStore {
    pub fn new() -> Self {
        Self { todos: Vec::new(), next_id: 1 }
    }

    pub fn add(&mut self, title: &str) -> Result<Todo, TodoError> {
        let title = validate_title(title)?;
        let todo = Todo { id: self.next_id, title, completed: false };
        self.next_id += 1;
        self.todos.push(todo.clone());
        Ok(todo)
    }

    pub fn get(&self, id: u64) -> Option<&Todo> {
        self.todos.iter().find(|t| t.id == id)
    }

    pub fn list(&self, filter: Filter) -> Vec<Todo> {
        self.todos.iter().filter(|t| filter.matches(t)).cloned().collect()
    }

    /// 部分更新：沒給的欄位維持原值。標題不合法時整筆都不改。
    pub fn update(
        &mut self,
        id: u64,
        title: Option<&str>,
        completed: Option<bool>,
    ) -> Result<Todo, TodoError> {
        let title = title.map(validate_title).transpose()?;
        let todo = self
            .todos
            .iter_mut()
            .find(|t| t.id == id)
            .ok_or(TodoError::NotFound)?;
        if let Some(title) = title {
            todo.title = title;
        }
        if let Some(completed) = completed {
            todo.completed = completed;
        }
        Ok(todo.clone())
    }

    pub fn remove(&mut self, id: u64) -> Result<(), TodoError> {
        let index = self
            .todos
            .iter()
            .position(|t| t.id == id)
            .ok_or(TodoError::NotFound)?;
        self.todos.remove(index);
        Ok(())
    }

    /// 刪掉所有已完成的項目，回傳刪了幾筆
    pub fn clear_completed(&mut self) -> usize {
        let before = self.todos.len();
        self.todos.retain(|t| !t.completed);
        before - self.todos.len()
    }

    pub fn stats(&self) -> Stats {
        let completed = self.todos.iter().filter(|t| t.completed).count();
        Stats {
            total: self.todos.len(),
            active: self.todos.len() - completed,
            completed,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// 建一個有三筆資料、其中第 2 筆已完成的 store
    fn sample_store() -> TodoStore {
        let mut store = TodoStore::new();
        store.add("買牛奶").unwrap();
        store.add("寫作業").unwrap();
        store.add("運動").unwrap();
        store.update(2, None, Some(true)).unwrap();
        store
    }

    // ---------- validate_title ----------

    #[test]
    fn validate_title_trims_whitespace() {
        assert_eq!(validate_title("  買牛奶  "), Ok("買牛奶".to_string()));
    }

    #[test]
    fn validate_title_rejects_empty_and_blank() {
        assert_eq!(validate_title(""), Err(TodoError::EmptyTitle));
        assert_eq!(validate_title("   \t\n"), Err(TodoError::EmptyTitle));
    }

    #[test]
    fn validate_title_length_boundary_counts_chars_not_bytes() {
        // 100 個中文字 = 300 bytes，但只算 100 個字，應該合法
        let exactly_max = "字".repeat(MAX_TITLE_LEN);
        assert!(validate_title(&exactly_max).is_ok());

        let too_long = "字".repeat(MAX_TITLE_LEN + 1);
        assert_eq!(validate_title(&too_long), Err(TodoError::TitleTooLong));
    }

    // ---------- add / get ----------

    #[test]
    fn add_assigns_incrementing_ids_and_starts_incomplete() {
        let mut store = TodoStore::new();
        let a = store.add("A").unwrap();
        let b = store.add("B").unwrap();
        assert_eq!((a.id, b.id), (1, 2));
        assert!(!a.completed);
        assert_eq!(store.get(2), Some(&b));
    }

    #[test]
    fn add_invalid_title_does_not_consume_id() {
        let mut store = TodoStore::new();
        assert_eq!(store.add("  "), Err(TodoError::EmptyTitle));
        assert_eq!(store.add("ok").unwrap().id, 1);
        assert_eq!(store.stats().total, 1);
    }

    #[test]
    fn ids_are_not_reused_after_remove() {
        let mut store = TodoStore::new();
        store.add("A").unwrap();
        store.remove(1).unwrap();
        assert_eq!(store.add("B").unwrap().id, 2);
    }

    // ---------- list / filter ----------

    #[test]
    fn list_filters_by_status() {
        let store = sample_store();
        let titles = |f| store.list(f).into_iter().map(|t| t.title).collect::<Vec<_>>();
        assert_eq!(titles(Filter::All), ["買牛奶", "寫作業", "運動"]);
        assert_eq!(titles(Filter::Active), ["買牛奶", "運動"]);
        assert_eq!(titles(Filter::Completed), ["寫作業"]);
    }

    #[test]
    fn filter_deserializes_from_lowercase_string() {
        let f: Filter = serde_json::from_str("\"completed\"").unwrap();
        assert_eq!(f, Filter::Completed);
        assert!(serde_json::from_str::<Filter>("\"done\"").is_err());
    }

    // ---------- update ----------

    #[test]
    fn update_changes_only_given_fields() {
        let mut store = sample_store();
        let t = store.update(1, Some("買豆漿"), None).unwrap();
        assert_eq!(t, Todo { id: 1, title: "買豆漿".into(), completed: false });

        let t = store.update(1, None, Some(true)).unwrap();
        assert_eq!(t.title, "買豆漿");
        assert!(t.completed);
    }

    #[test]
    fn update_with_invalid_title_leaves_todo_unchanged() {
        let mut store = sample_store();
        assert_eq!(store.update(1, Some(" "), Some(true)), Err(TodoError::EmptyTitle));
        let t = store.get(1).unwrap();
        assert_eq!(t.title, "買牛奶");
        assert!(!t.completed, "completed 也不應該被改到");
    }

    #[test]
    fn update_missing_id_returns_not_found() {
        let mut store = sample_store();
        assert_eq!(store.update(99, None, Some(true)), Err(TodoError::NotFound));
    }

    // ---------- remove / clear_completed ----------

    #[test]
    fn remove_deletes_only_that_todo() {
        let mut store = sample_store();
        store.remove(2).unwrap();
        assert!(store.get(2).is_none());
        assert_eq!(store.stats().total, 2);
        assert_eq!(store.remove(2), Err(TodoError::NotFound));
    }

    #[test]
    fn clear_completed_removes_completed_and_returns_count() {
        let mut store = sample_store();
        store.update(3, None, Some(true)).unwrap();
        assert_eq!(store.clear_completed(), 2);
        assert_eq!(store.list(Filter::All).len(), 1);
        assert_eq!(store.clear_completed(), 0);
    }

    // ---------- stats ----------

    #[test]
    fn stats_counts_each_status() {
        assert_eq!(TodoStore::new().stats(), Stats { total: 0, active: 0, completed: 0 });
        assert_eq!(sample_store().stats(), Stats { total: 3, active: 2, completed: 1 });
    }

    #[test]
    fn error_messages_are_human_readable() {
        assert_eq!(TodoError::EmptyTitle.message(), "標題不可為空白");
        assert!(TodoError::TitleTooLong.message().contains("100"));
    }
}

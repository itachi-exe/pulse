use crate::aggregator;
use crate::cache::Cache;
use crate::fetchers::Fetchers;
use crate::types::{ApiError, FeedType, PulseFeed};
use axum::{
    extract::{Path, Query, State, WebSocketUpgrade},
    http::StatusCode,
    response::{IntoResponse, Json, Response},
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};
use std::{sync::Arc, time::Instant};
use tower_http::cors::{Any, CorsLayer};
use tracing::info;

pub struct AppState {
    pub fetchers: Fetchers,
    pub cache: Cache,
}

pub fn router(state: Arc<AppState>) -> Router {
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    Router::new()
        .route("/", get(health))
        .route("/health", get(health))
        .route("/feed/:feed_type", get(pull_feed))
        .route("/feed/:feed_type/ws", get(ws_feed))
        .route("/feeds", get(list_feeds))
        .layer(cors)
        .with_state(state)
}

// ── Health ────────────────────────────────────────────────────────────────────

async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "ok",
        "service": "pulse",
        "version": env!("CARGO_PKG_VERSION"),
    }))
}

// ── Query params ──────────────────────────────────────────────────────────────

#[derive(Debug, Deserialize)]
pub struct FeedParams {
    pub q: Option<String>,       // query string, e.g. "ETH gas price"
    pub fresh: Option<bool>,     // bypass cache
}

// ── Pull feed (HTTP GET) ──────────────────────────────────────────────────────

async fn pull_feed(
    Path(feed_type_str): Path<String>,
    Query(params): Query<FeedParams>,
    State(state): State<Arc<AppState>>,
) -> Response {
    let feed_type = parse_feed_type(&feed_type_str);
    let query = params.q.as_deref().unwrap_or(&feed_type_str).to_string();
    let fresh = params.fresh.unwrap_or(false);

    // Generate a stable feed_id from the feed_type + query
    let feed_id = format!("{}:{}", feed_type, query.to_lowercase().replace(' ', "_"));

    // Check cache first (unless fresh=true)
    if !fresh {
        if let Some(cached) = state.cache.get(&feed_id).await {
            info!("cache hit for {}", feed_id);
            return Json(cached).into_response();
        }
    }

    // Fetch fresh data
    let start = Instant::now();
    let points = state.fetchers.fetch_all(&query, &feed_type).await;
    let feed = aggregator::aggregate(&query, &feed_id, points, start);

    // Cache it
    let _ = state.cache.set(&feed_id, &feed).await;

    Json(feed).into_response()
}

// ── List feeds ────────────────────────────────────────────────────────────────

async fn list_feeds(State(state): State<Arc<AppState>>) -> Json<serde_json::Value> {
    let feeds = state.cache.list_feeds().await;
    Json(serde_json::json!({
        "cached_feeds": feeds,
        "count": feeds.len(),
    }))
}

// ── WebSocket push ────────────────────────────────────────────────────────────

async fn ws_feed(
    Path(feed_type_str): Path<String>,
    Query(params): Query<FeedParams>,
    ws: WebSocketUpgrade,
    State(state): State<Arc<AppState>>,
) -> Response {
    let feed_type = parse_feed_type(&feed_type_str);
    let query = params.q.as_deref().unwrap_or(&feed_type_str).to_string();

    ws.on_upgrade(move |socket| async move {
        use axum::extract::ws::{Message, WebSocket};
        use tokio::time::{sleep, Duration};

        let mut socket: WebSocket = socket;
        let feed_id = format!("{}:{}", feed_type, query.to_lowercase().replace(' ', "_"));

        loop {
            let start = Instant::now();
            let points = state.fetchers.fetch_all(&query, &feed_type).await;
            let feed = aggregator::aggregate(&query, &feed_id, points, start);
            let _ = state.cache.set(&feed_id, &feed).await;

            let msg = match serde_json::to_string(&feed) {
                Ok(s) => s,
                Err(_) => break,
            };

            if socket.send(Message::Text(msg)).await.is_err() {
                break; // client disconnected
            }

            sleep(Duration::from_secs(10)).await;
        }
    })
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn parse_feed_type(s: &str) -> FeedType {
    match s.to_lowercase().as_str() {
        "crypto_price" | "price" | "crypto" => FeedType::CryptoPrice,
        "gas_price" | "gas" => FeedType::GasPrice,
        "on_chain_event" | "on_chain" | "onchain" => FeedType::OnChainEvent,
        "news_signal" | "news" => FeedType::NewsSignal,
        "social_sentiment" | "social" | "sentiment" => FeedType::SocialSentiment,
        "regulatory" => FeedType::Regulatory,
        _ => FeedType::Generic,
    }
}

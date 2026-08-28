mod aggregator;
mod api;
mod cache;
mod fetchers;
mod types;

use api::AppState;
use cache::Cache;
use fetchers::Fetchers;
use std::sync::Arc;
use tracing::info;
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Tracing
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("pulse=info")),
        )
        .init();

    let redis_url = std::env::var("REDIS_URL").unwrap_or_else(|_| "redis://127.0.0.1:6379".into());
    let bind_addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:7070".into());

    info!("connecting to redis at {}", redis_url);
    let cache = Cache::new(&redis_url)?;

    let state = Arc::new(AppState {
        fetchers: Fetchers::new(),
        cache,
    });

    let app = api::router(state);

    info!("pulse listening on {}", bind_addr);
    let listener = tokio::net::TcpListener::bind(&bind_addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

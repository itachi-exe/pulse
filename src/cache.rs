use crate::types::PulseFeed;
use anyhow::Result;
use redis::AsyncCommands;
use serde_json;
use tracing::{debug, warn};

const CACHE_TTL_SECS: u64 = 10; // refresh every 10 seconds
const CACHE_PREFIX: &str = "pulse:feed:";

pub struct Cache {
    client: redis::Client,
}

impl Cache {
    pub fn new(redis_url: &str) -> Result<Self> {
        let client = redis::Client::open(redis_url)?;
        Ok(Self { client })
    }

    pub async fn get(&self, feed_id: &str) -> Option<PulseFeed> {
        let mut conn = match self.client.get_async_connection().await {
            Ok(c) => c,
            Err(e) => { warn!("redis connect err: {}", e); return None; }
        };
        let key = format!("{}{}", CACHE_PREFIX, feed_id);
        let raw: Option<String> = conn.get(&key).await.ok();
        raw.and_then(|s| {
            match serde_json::from_str(&s) {
                Ok(feed) => { debug!("cache hit: {}", feed_id); Some(feed) }
                Err(e) => { warn!("cache deserialize err: {}", e); None }
            }
        })
    }

    pub async fn set(&self, feed_id: &str, feed: &PulseFeed) -> Result<()> {
        let mut conn = self.client.get_async_connection().await?;
        let key = format!("{}{}", CACHE_PREFIX, feed_id);
        let serialized = serde_json::to_string(feed)?;
        let _: () = conn.set_ex(&key, serialized, CACHE_TTL_SECS).await?;
        debug!("cache set: {} (ttl={}s)", feed_id, CACHE_TTL_SECS);
        Ok(())
    }

    pub async fn invalidate(&self, feed_id: &str) -> Result<()> {
        let mut conn = self.client.get_async_connection().await?;
        let key = format!("{}{}", CACHE_PREFIX, feed_id);
        let _: () = conn.del(&key).await?;
        Ok(())
    }

    /// List all cached feed IDs.
    pub async fn list_feeds(&self) -> Vec<String> {
        let mut conn = match self.client.get_async_connection().await {
            Ok(c) => c,
            Err(_) => return vec![],
        };
        let pattern = format!("{}*", CACHE_PREFIX);
        let keys: Vec<String> = conn.keys(&pattern).await.unwrap_or_default();
        keys.into_iter()
            .map(|k| k.trim_start_matches(CACHE_PREFIX).to_string())
            .collect()
    }
}

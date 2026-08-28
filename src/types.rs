use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataPoint {
    pub source: String,
    pub value: serde_json::Value,
    pub fetched_at: DateTime<Utc>,
    pub latency_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PulseFeed {
    pub feed_id: String,
    pub query: String,
    pub value: serde_json::Value,
    pub confidence: f64,          // 0.0 - 1.0
    pub sources: Vec<DataPoint>,
    pub source_count: usize,
    pub agreement_score: f64,     // how much sources agreed (0-1)
    pub refreshed_at: DateTime<Utc>,
    pub latency_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FetchRequest {
    pub query: String,
    pub feed_type: FeedType,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum FeedType {
    CryptoPrice,
    GasPrice,
    OnChainEvent,
    NewsSignal,
    SocialSentiment,
    Regulatory,
    Generic,
}

impl std::fmt::Display for FeedType {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        let s = match self {
            FeedType::CryptoPrice => "crypto_price",
            FeedType::GasPrice => "gas_price",
            FeedType::OnChainEvent => "on_chain_event",
            FeedType::NewsSignal => "news_signal",
            FeedType::SocialSentiment => "social_sentiment",
            FeedType::Regulatory => "regulatory",
            FeedType::Generic => "generic",
        };
        write!(f, "{}", s)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiError {
    pub error: String,
    pub code: u16,
}

use crate::types::{DataPoint, FeedType};
use anyhow::Result;
use chrono::Utc;
use reqwest::Client;
use serde_json::Value;
use std::time::Instant;
use tracing::{debug, warn};

pub struct Fetchers {
    client: Client,
}

impl Fetchers {
    pub fn new() -> Self {
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(8))
            .user_agent("pulse-agent/0.1")
            .build()
            .expect("failed to build http client");
        Self { client }
    }

    /// Fetch all relevant sources for a given feed type and query.
    /// Returns a Vec of DataPoints, one per source that responded.
    pub async fn fetch_all(&self, query: &str, feed_type: &FeedType) -> Vec<DataPoint> {
        use std::pin::Pin;
        use std::future::Future;

        type BoxFut<'a> = Pin<Box<dyn Future<Output = Option<DataPoint>> + Send + 'a>>;

        let tasks: Vec<BoxFut> = match feed_type {
            FeedType::CryptoPrice => {
                let symbol = extract_symbol(query);
                let s1 = symbol.clone();
                let s2 = symbol.clone();
                let s3 = symbol.clone();
                vec![
                    Box::pin(async move { self.fetch_coingecko(&s1).await }),
                    Box::pin(async move { self.fetch_coinpaprika(&s2).await }),
                    Box::pin(async move { self.fetch_coincap(&s3).await }),
                ]
            }
            FeedType::GasPrice => {
                vec![
                    Box::pin(async move { self.fetch_etherscan_gas().await }),
                    Box::pin(async move { self.fetch_blocknative_gas().await }),
                    Box::pin(async move { self.fetch_owlracle_gas().await }),
                ]
            }
            FeedType::OnChainEvent => {
                let q1 = query.to_string();
                let q2 = query.to_string();
                vec![
                    Box::pin(async move { self.fetch_etherscan_events(&q1).await }),
                    Box::pin(async move { self.fetch_blockchair(&q2).await }),
                ]
            }
            FeedType::NewsSignal => {
                let q1 = query.to_string();
                let q2 = query.to_string();
                vec![
                    Box::pin(async move { self.fetch_cryptopanic(&q1).await }),
                    Box::pin(async move { self.fetch_newsdata(&q2).await }),
                ]
            }
            FeedType::SocialSentiment => {
                let q1 = query.to_string();
                let q2 = query.to_string();
                vec![
                    Box::pin(async move { self.fetch_lunarcrush(&q1).await }),
                    Box::pin(async move { self.fetch_santiment(&q2).await }),
                ]
            }
            _ => {
                let sym = extract_symbol(query);
                let q1 = query.to_string();
                vec![
                    Box::pin(async move { self.fetch_coingecko(&sym).await }),
                    Box::pin(async move { self.fetch_etherscan_gas().await }),
                    Box::pin(async move { self.fetch_cryptopanic(&q1).await }),
                ]
            }
        };

        let results = futures_util::future::join_all(tasks).await;
        results.into_iter().flatten().collect()
    }

    // ── CoinGecko ────────────────────────────────────────────────────────────
    async fn fetch_coingecko(&self, symbol: &str) -> Option<DataPoint> {
        let id = coingecko_id(symbol);
        let url = format!(
            "https://api.coingecko.com/api/v3/simple/price?ids={}&vs_currencies=usd&include_24hr_change=true",
            id
        );
        let t = Instant::now();
        match self.client.get(&url).send().await {
            Ok(resp) if resp.status().is_success() => {
                let latency = t.elapsed().as_millis() as u64;
                match resp.json::<Value>().await {
                    Ok(json) => {
                        let price = json[&id]["usd"].as_f64().unwrap_or(0.0);
                        let change = json[&id]["usd_24h_change"].as_f64().unwrap_or(0.0);
                        debug!("coingecko {} = ${}", symbol, price);
                        Some(DataPoint {
                            source: "coingecko".into(),
                            value: serde_json::json!({
                                "price_usd": price,
                                "change_24h_pct": change,
                                "symbol": symbol.to_uppercase(),
                            }),
                            fetched_at: Utc::now(),
                            latency_ms: latency,
                        })
                    }
                    Err(e) => { warn!("coingecko parse err: {}", e); None }
                }
            }
            Ok(resp) => { warn!("coingecko status {}", resp.status()); None }
            Err(e) => { warn!("coingecko fetch err: {}", e); None }
        }
    }

    // ── CoinPaprika ──────────────────────────────────────────────────────────
    async fn fetch_coinpaprika(&self, symbol: &str) -> Option<DataPoint> {
        let id = coinpaprika_id(symbol);
        let url = format!("https://api.coinpaprika.com/v1/tickers/{}", id);
        let t = Instant::now();
        match self.client.get(&url).send().await {
            Ok(resp) if resp.status().is_success() => {
                let latency = t.elapsed().as_millis() as u64;
                match resp.json::<Value>().await {
                    Ok(json) => {
                        let price = json["quotes"]["USD"]["price"].as_f64().unwrap_or(0.0);
                        let change = json["quotes"]["USD"]["percent_change_24h"].as_f64().unwrap_or(0.0);
                        Some(DataPoint {
                            source: "coinpaprika".into(),
                            value: serde_json::json!({
                                "price_usd": price,
                                "change_24h_pct": change,
                                "symbol": symbol.to_uppercase(),
                            }),
                            fetched_at: Utc::now(),
                            latency_ms: latency,
                        })
                    }
                    Err(e) => { warn!("coinpaprika parse: {}", e); None }
                }
            }
            Ok(r) => { warn!("coinpaprika {}", r.status()); None }
            Err(e) => { warn!("coinpaprika err: {}", e); None }
        }
    }

    // ── CoinCap ──────────────────────────────────────────────────────────────
    async fn fetch_coincap(&self, symbol: &str) -> Option<DataPoint> {
        let id = symbol.to_lowercase();
        let url = format!("https://api.coincap.io/v2/assets/{}", id);
        let t = Instant::now();
        match self.client.get(&url).send().await {
            Ok(resp) if resp.status().is_success() => {
                let latency = t.elapsed().as_millis() as u64;
                match resp.json::<Value>().await {
                    Ok(json) => {
                        let price: f64 = json["data"]["priceUsd"]
                            .as_str()
                            .and_then(|s| s.parse().ok())
                            .unwrap_or(0.0);
                        let change: f64 = json["data"]["changePercent24Hr"]
                            .as_str()
                            .and_then(|s| s.parse().ok())
                            .unwrap_or(0.0);
                        Some(DataPoint {
                            source: "coincap".into(),
                            value: serde_json::json!({
                                "price_usd": price,
                                "change_24h_pct": change,
                                "symbol": symbol.to_uppercase(),
                            }),
                            fetched_at: Utc::now(),
                            latency_ms: latency,
                        })
                    }
                    Err(e) => { warn!("coincap parse: {}", e); None }
                }
            }
            Ok(r) => { warn!("coincap {}", r.status()); None }
            Err(e) => { warn!("coincap err: {}", e); None }
        }
    }

    // ── Etherscan Gas ────────────────────────────────────────────────────────
    async fn fetch_etherscan_gas(&self) -> Option<DataPoint> {
        let url = "https://api.etherscan.io/api?module=gastracker&action=gasoracle";
        let t = Instant::now();
        match self.client.get(url).send().await {
            Ok(resp) if resp.status().is_success() => {
                let latency = t.elapsed().as_millis() as u64;
                match resp.json::<Value>().await {
                    Ok(json) => {
                        let safe = json["result"]["SafeGasPrice"].as_str()
                            .and_then(|s| s.parse::<f64>().ok()).unwrap_or(0.0);
                        let fast = json["result"]["FastGasPrice"].as_str()
                            .and_then(|s| s.parse::<f64>().ok()).unwrap_or(0.0);
                        let base = json["result"]["suggestBaseFee"].as_str()
                            .and_then(|s| s.parse::<f64>().ok()).unwrap_or(0.0);
                        Some(DataPoint {
                            source: "etherscan".into(),
                            value: serde_json::json!({
                                "safe_gwei": safe,
                                "fast_gwei": fast,
                                "base_fee_gwei": base,
                                "unit": "gwei",
                            }),
                            fetched_at: Utc::now(),
                            latency_ms: latency,
                        })
                    }
                    Err(e) => { warn!("etherscan parse: {}", e); None }
                }
            }
            Ok(r) => { warn!("etherscan {}", r.status()); None }
            Err(e) => { warn!("etherscan err: {}", e); None }
        }
    }

    // ── BlockNative Gas ──────────────────────────────────────────────────────
    async fn fetch_blocknative_gas(&self) -> Option<DataPoint> {
        let url = "https://api.blocknative.com/gasprices/blockprices";
        let t = Instant::now();
        match self.client.get(url).send().await {
            Ok(resp) if resp.status().is_success() => {
                let latency = t.elapsed().as_millis() as u64;
                match resp.json::<Value>().await {
                    Ok(json) => {
                        let base = json["blockPrices"][0]["baseFeePerGas"]
                            .as_f64().unwrap_or(0.0);
                        let est = json["blockPrices"][0]["estimatedPrices"][0]["maxPriorityFeePerGas"]
                            .as_f64().unwrap_or(0.0);
                        Some(DataPoint {
                            source: "blocknative".into(),
                            value: serde_json::json!({
                                "base_fee_gwei": base,
                                "priority_fee_gwei": est,
                                "unit": "gwei",
                            }),
                            fetched_at: Utc::now(),
                            latency_ms: latency,
                        })
                    }
                    Err(e) => { warn!("blocknative parse: {}", e); None }
                }
            }
            Ok(r) => { warn!("blocknative {}", r.status()); None }
            Err(e) => { warn!("blocknative err: {}", e); None }
        }
    }

    // ── Owlracle Gas ─────────────────────────────────────────────────────────
    async fn fetch_owlracle_gas(&self) -> Option<DataPoint> {
        let url = "https://api.owlracle.info/v4/eth/gas?feeinusd=false";
        let t = Instant::now();
        match self.client.get(url).send().await {
            Ok(resp) if resp.status().is_success() => {
                let latency = t.elapsed().as_millis() as u64;
                match resp.json::<Value>().await {
                    Ok(json) => {
                        let slow = json["speeds"][0]["gasPrice"].as_f64().unwrap_or(0.0);
                        let fast = json["speeds"][2]["gasPrice"].as_f64().unwrap_or(0.0);
                        Some(DataPoint {
                            source: "owlracle".into(),
                            value: serde_json::json!({
                                "slow_gwei": slow,
                                "fast_gwei": fast,
                                "unit": "gwei",
                            }),
                            fetched_at: Utc::now(),
                            latency_ms: latency,
                        })
                    }
                    Err(e) => { warn!("owlracle parse: {}", e); None }
                }
            }
            Ok(r) => { warn!("owlracle {}", r.status()); None }
            Err(e) => { warn!("owlracle err: {}", e); None }
        }
    }

    // ── Etherscan Events ─────────────────────────────────────────────────────
    async fn fetch_etherscan_events(&self, _query: &str) -> Option<DataPoint> {
        // Latest block stats as a proxy for on-chain activity
        let url = "https://api.etherscan.io/api?module=proxy&action=eth_blockNumber";
        let t = Instant::now();
        match self.client.get(url).send().await {
            Ok(resp) if resp.status().is_success() => {
                let latency = t.elapsed().as_millis() as u64;
                match resp.json::<Value>().await {
                    Ok(json) => {
                        let block_hex = json["result"].as_str().unwrap_or("0x0");
                        let block = u64::from_str_radix(block_hex.trim_start_matches("0x"), 16)
                            .unwrap_or(0);
                        Some(DataPoint {
                            source: "etherscan_events".into(),
                            value: serde_json::json!({
                                "latest_block": block,
                                "network": "ethereum",
                            }),
                            fetched_at: Utc::now(),
                            latency_ms: latency,
                        })
                    }
                    Err(e) => { warn!("etherscan events parse: {}", e); None }
                }
            }
            Ok(r) => { warn!("etherscan events {}", r.status()); None }
            Err(e) => { warn!("etherscan events err: {}", e); None }
        }
    }

    // ── Blockchair ───────────────────────────────────────────────────────────
    async fn fetch_blockchair(&self, _query: &str) -> Option<DataPoint> {
        let url = "https://api.blockchair.com/ethereum/stats";
        let t = Instant::now();
        match self.client.get(url).send().await {
            Ok(resp) if resp.status().is_success() => {
                let latency = t.elapsed().as_millis() as u64;
                match resp.json::<Value>().await {
                    Ok(json) => {
                        let blocks = json["data"]["blocks"].as_u64().unwrap_or(0);
                        let txs_24h = json["data"]["transactions_24h"].as_u64().unwrap_or(0);
                        let fee_avg = json["data"]["average_transaction_fee_24h"].as_f64().unwrap_or(0.0);
                        Some(DataPoint {
                            source: "blockchair".into(),
                            value: serde_json::json!({
                                "total_blocks": blocks,
                                "transactions_24h": txs_24h,
                                "avg_fee_eth": fee_avg / 1e18,
                                "network": "ethereum",
                            }),
                            fetched_at: Utc::now(),
                            latency_ms: latency,
                        })
                    }
                    Err(e) => { warn!("blockchair parse: {}", e); None }
                }
            }
            Ok(r) => { warn!("blockchair {}", r.status()); None }
            Err(e) => { warn!("blockchair err: {}", e); None }
        }
    }

    // ── CryptoPanic ──────────────────────────────────────────────────────────
    async fn fetch_cryptopanic(&self, query: &str) -> Option<DataPoint> {
        let symbol = extract_symbol(query).to_uppercase();
        let url = format!(
            "https://cryptopanic.com/api/free/v1/posts/?auth_token=free&currencies={}&kind=news&filter=hot",
            symbol
        );
        let t = Instant::now();
        match self.client.get(&url).send().await {
            Ok(resp) if resp.status().is_success() => {
                let latency = t.elapsed().as_millis() as u64;
                match resp.json::<Value>().await {
                    Ok(json) => {
                        let results = json["results"].as_array().cloned().unwrap_or_default();
                        let count = results.len();
                        let headlines: Vec<String> = results.iter().take(3)
                            .filter_map(|r| r["title"].as_str().map(|s| s.to_string()))
                            .collect();
                        let sentiment_score = calculate_news_sentiment(&results);
                        Some(DataPoint {
                            source: "cryptopanic".into(),
                            value: serde_json::json!({
                                "article_count": count,
                                "top_headlines": headlines,
                                "sentiment_score": sentiment_score, // -1 to 1
                                "query": query,
                            }),
                            fetched_at: Utc::now(),
                            latency_ms: latency,
                        })
                    }
                    Err(e) => { warn!("cryptopanic parse: {}", e); None }
                }
            }
            Ok(r) => { warn!("cryptopanic {}", r.status()); None }
            Err(e) => { warn!("cryptopanic err: {}", e); None }
        }
    }

    // ── NewsData.io ──────────────────────────────────────────────────────────
    async fn fetch_newsdata(&self, query: &str) -> Option<DataPoint> {
        // Public endpoint, limited but keyless
        let url = format!(
            "https://newsdata.io/api/1/news?q={}&language=en&category=business,technology",
            urlencoding_simple(query)
        );
        let t = Instant::now();
        match self.client.get(&url).send().await {
            Ok(resp) if resp.status().is_success() => {
                let latency = t.elapsed().as_millis() as u64;
                match resp.json::<Value>().await {
                    Ok(json) => {
                        let results = json["results"].as_array().cloned().unwrap_or_default();
                        let count = results.len();
                        let headlines: Vec<String> = results.iter().take(3)
                            .filter_map(|r| r["title"].as_str().map(String::from))
                            .collect();
                        Some(DataPoint {
                            source: "newsdata".into(),
                            value: serde_json::json!({
                                "article_count": count,
                                "top_headlines": headlines,
                                "query": query,
                            }),
                            fetched_at: Utc::now(),
                            latency_ms: latency,
                        })
                    }
                    Err(e) => { warn!("newsdata parse: {}", e); None }
                }
            }
            Ok(r) => { warn!("newsdata {}", r.status()); None }
            Err(e) => { warn!("newsdata err: {}", e); None }
        }
    }

    // ── LunarCrush (social) ──────────────────────────────────────────────────
    async fn fetch_lunarcrush(&self, query: &str) -> Option<DataPoint> {
        let symbol = extract_symbol(query).to_uppercase();
        let url = format!(
            "https://lunarcrush.com/api4/public/coins/{}/v1",
            symbol.to_lowercase()
        );
        let t = Instant::now();
        match self.client.get(&url).send().await {
            Ok(resp) if resp.status().is_success() => {
                let latency = t.elapsed().as_millis() as u64;
                match resp.json::<Value>().await {
                    Ok(json) => {
                        let galaxy_score = json["data"]["galaxy_score"].as_f64().unwrap_or(0.0);
                        let sentiment = json["data"]["sentiment"].as_f64().unwrap_or(0.0);
                        let social_volume = json["data"]["social_volume_24h"].as_u64().unwrap_or(0);
                        Some(DataPoint {
                            source: "lunarcrush".into(),
                            value: serde_json::json!({
                                "galaxy_score": galaxy_score,
                                "sentiment": sentiment,
                                "social_volume_24h": social_volume,
                                "symbol": symbol,
                            }),
                            fetched_at: Utc::now(),
                            latency_ms: latency,
                        })
                    }
                    Err(e) => { warn!("lunarcrush parse: {}", e); None }
                }
            }
            Ok(r) => { warn!("lunarcrush {}", r.status()); None }
            Err(e) => { warn!("lunarcrush err: {}", e); None }
        }
    }

    // ── Santiment (social/on-chain) ───────────────────────────────────────────
    async fn fetch_santiment(&self, query: &str) -> Option<DataPoint> {
        let slug = santiment_slug(&extract_symbol(query));
        // Public GraphQL endpoint (rate-limited but no auth for basic metrics)
        let gql = format!(
            r#"{{"query":"{{projectBySlug(slug:\"{}\"){{slug,ticker,priceUsd,volumeUsd24h,devActivity30d}}}}"}}"#,
            slug
        );
        let t = Instant::now();
        match self.client
            .post("https://api.santiment.net/graphql")
            .header("content-type", "application/json")
            .body(gql)
            .send()
            .await
        {
            Ok(resp) if resp.status().is_success() => {
                let latency = t.elapsed().as_millis() as u64;
                match resp.json::<Value>().await {
                    Ok(json) => {
                        let data = &json["data"]["projectBySlug"];
                        let price = data["priceUsd"].as_f64().unwrap_or(0.0);
                        let vol = data["volumeUsd24h"].as_f64().unwrap_or(0.0);
                        let dev = data["devActivity30d"].as_f64().unwrap_or(0.0);
                        Some(DataPoint {
                            source: "santiment".into(),
                            value: serde_json::json!({
                                "price_usd": price,
                                "volume_usd_24h": vol,
                                "dev_activity_30d": dev,
                                "slug": slug,
                            }),
                            fetched_at: Utc::now(),
                            latency_ms: latency,
                        })
                    }
                    Err(e) => { warn!("santiment parse: {}", e); None }
                }
            }
            Ok(r) => { warn!("santiment {}", r.status()); None }
            Err(e) => { warn!("santiment err: {}", e); None }
        }
    }
}

// ── Helpers ────────────────────────────────────────────────────────────────

fn extract_symbol(query: &str) -> String {
    // Try to extract a crypto ticker from the query
    let q = query.to_uppercase();
    for sym in &["BTC", "ETH", "SOL", "BNB", "MATIC", "ARB", "OP", "AVAX", "LINK", "UNI", "AAVE", "MKR"] {
        if q.contains(sym) {
            return sym.to_lowercase();
        }
    }
    // Default fallback
    q.split_whitespace()
        .next()
        .unwrap_or("ethereum")
        .to_lowercase()
}

fn coingecko_id(symbol: &str) -> String {
    match symbol.to_lowercase().as_str() {
        "btc" => "bitcoin",
        "eth" => "ethereum",
        "sol" => "solana",
        "bnb" => "binancecoin",
        "matic" | "pol" => "matic-network",
        "arb" => "arbitrum",
        "op" => "optimism",
        "avax" => "avalanche-2",
        "link" => "chainlink",
        "uni" => "uniswap",
        "aave" => "aave",
        "mkr" => "maker",
        other => other,
    }.to_string()
}

fn coinpaprika_id(symbol: &str) -> String {
    match symbol.to_lowercase().as_str() {
        "btc" => "btc-bitcoin".to_string(),
        "eth" => "eth-ethereum".to_string(),
        "sol" => "sol-solana".to_string(),
        "bnb" => "bnb-binance-coin".to_string(),
        "matic" => "matic-polygon".to_string(),
        "link" => "link-chainlink".to_string(),
        other => format!("{}-{}", other, other),
    }
}

fn santiment_slug(symbol: &str) -> String {
    match symbol.to_lowercase().as_str() {
        "btc" => "bitcoin",
        "eth" => "ethereum",
        "sol" => "solana",
        "link" => "chainlink",
        other => other,
    }.to_string()
}

fn calculate_news_sentiment(articles: &[Value]) -> f64 {
    if articles.is_empty() { return 0.0; }
    let mut score = 0.0f64;
    for a in articles {
        let votes = &a["votes"];
        let pos = votes["positive"].as_f64().unwrap_or(0.0);
        let neg = votes["negative"].as_f64().unwrap_or(0.0);
        let total = pos + neg;
        if total > 0.0 {
            score += (pos - neg) / total;
        }
    }
    (score / articles.len() as f64).clamp(-1.0, 1.0)
}

fn urlencoding_simple(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            ' ' => "%20".to_string(),
            '&' => "%26".to_string(),
            '?' => "%3F".to_string(),
            '#' => "%23".to_string(),
            c => c.to_string(),
        })
        .collect()
}

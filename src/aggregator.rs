use crate::types::{DataPoint, PulseFeed};
use anyhow::Result;
use chrono::Utc;
use std::time::Instant;
use serde_json::Value;

/// Aggregate multiple DataPoints into a single PulseFeed.
/// Handles numeric consensus (median), string voting, and confidence scoring.
pub fn aggregate(query: &str, feed_id: &str, points: Vec<DataPoint>, start: Instant) -> PulseFeed {
    let source_count = points.len();
    let latency_ms = start.elapsed().as_millis() as u64;

    if source_count == 0 {
        return PulseFeed {
            feed_id: feed_id.to_string(),
            query: query.to_string(),
            value: Value::Null,
            confidence: 0.0,
            sources: vec![],
            source_count: 0,
            agreement_score: 0.0,
            refreshed_at: Utc::now(),
            latency_ms,
        };
    }

    if source_count == 1 {
        return PulseFeed {
            feed_id: feed_id.to_string(),
            query: query.to_string(),
            value: points[0].value.clone(),
            confidence: 0.5, // single source = half confidence
            sources: points,
            source_count: 1,
            agreement_score: 1.0,
            refreshed_at: Utc::now(),
            latency_ms,
        };
    }

    // Try numeric aggregation on "price_usd" or "safe_gwei" / "base_fee_gwei"
    let aggregated = try_numeric_aggregate(&points)
        .unwrap_or_else(|| merge_objects(&points));

    let agreement = calculate_agreement(&points);
    // Confidence: base 0.6 for 2 sources, +0.1 per additional source, capped at 0.95
    // then scaled by agreement
    let base_conf = (0.6 + 0.1 * (source_count as f64 - 2.0)).min(0.95);
    let confidence = (base_conf * (0.5 + 0.5 * agreement)).clamp(0.0, 1.0);

    PulseFeed {
        feed_id: feed_id.to_string(),
        query: query.to_string(),
        value: aggregated,
        confidence,
        sources: points,
        source_count,
        agreement_score: agreement,
        refreshed_at: Utc::now(),
        latency_ms,
    }
}

/// Try to extract a primary numeric field and compute median + spread.
fn try_numeric_aggregate(points: &[DataPoint]) -> Option<Value> {
    // Priority fields to aggregate
    let candidate_fields = ["price_usd", "safe_gwei", "base_fee_gwei", "sentiment", "galaxy_score"];

    for field in &candidate_fields {
        let values: Vec<f64> = points.iter()
            .filter_map(|p| p.value.get(field).and_then(|v| v.as_f64()))
            .collect();

        if values.len() >= 2 {
            let median = median_f64(&values);
            let spread = spread_pct(&values);

            // Build a merged object with the consensus value + metadata
            let mut merged = merge_objects(points);
            if let Value::Object(ref mut m) = merged {
                m.insert(field.to_string(), Value::from(round2(median)));
                m.insert("_consensus_field".to_string(), Value::from(*field));
                m.insert("_spread_pct".to_string(), Value::from(round2(spread)));
                m.insert("_source_values".to_string(), Value::Array(
                    values.iter().map(|v| Value::from(round2(*v))).collect()
                ));
            }
            return Some(merged);
        }
    }
    None
}

/// Merge all source objects by key, preferring non-null values.
/// For numeric fields that appear in multiple sources, use the median.
fn merge_objects(points: &[DataPoint]) -> Value {
    let mut merged = serde_json::Map::new();

    // Collect all keys
    let mut all_keys: Vec<String> = points.iter()
        .filter_map(|p| p.value.as_object())
        .flat_map(|m| m.keys().cloned())
        .collect();
    all_keys.dedup();

    for key in all_keys {
        if key.starts_with('_') { continue; }
        let nums: Vec<f64> = points.iter()
            .filter_map(|p| p.value.get(&key).and_then(|v| v.as_f64()))
            .collect();
        if nums.len() >= 2 {
            merged.insert(key, Value::from(round2(median_f64(&nums))));
        } else {
            // Take first non-null value
            if let Some(val) = points.iter()
                .filter_map(|p| p.value.get(&key))
                .find(|v| !v.is_null()) {
                merged.insert(key, val.clone());
            }
        }
    }

    Value::Object(merged)
}

fn median_f64(values: &[f64]) -> f64 {
    let mut sorted = values.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = sorted.len();
    if n % 2 == 0 {
        (sorted[n / 2 - 1] + sorted[n / 2]) / 2.0
    } else {
        sorted[n / 2]
    }
}

/// Returns the coefficient of variation (std/mean) as a percentage.
/// 0 = perfect agreement, 100+ = high disagreement.
fn spread_pct(values: &[f64]) -> f64 {
    if values.is_empty() { return 0.0; }
    let mean = values.iter().sum::<f64>() / values.len() as f64;
    if mean.abs() < 1e-10 { return 0.0; }
    let variance = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / values.len() as f64;
    (variance.sqrt() / mean.abs() * 100.0).clamp(0.0, 100.0)
}

/// Agreement score based on spread. 0% spread = 1.0, 20%+ spread = 0.0.
fn calculate_agreement(points: &[DataPoint]) -> f64 {
    let candidate_fields = ["price_usd", "safe_gwei", "base_fee_gwei"];
    for field in &candidate_fields {
        let values: Vec<f64> = points.iter()
            .filter_map(|p| p.value.get(field).and_then(|v| v.as_f64()))
            .collect();
        if values.len() >= 2 {
            let spread = spread_pct(&values);
            // 0% spread -> 1.0 agreement, 20%+ spread -> 0.0
            return (1.0 - spread / 20.0).clamp(0.0, 1.0);
        }
    }
    // No numeric field found; base agreement on source count
    (points.len() as f64 / 3.0).min(1.0)
}

fn round2(v: f64) -> f64 {
    (v * 100.0).round() / 100.0
}

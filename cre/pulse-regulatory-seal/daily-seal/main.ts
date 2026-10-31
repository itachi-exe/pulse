/**
 * Pulse daily regulatory seal: a Chainlink CRE workflow.
 *
 * Runs on a cron schedule (daily at 23:30 UTC), fetches the Pulse regulatory
 * feed, extracts the day's SHA-256 seal digest, and returns a signed
 * attestation record verified by DON consensus.
 *
 * API shape: GET /data/feed/<feedKey>
 *   -> { data: { snapshot: { digest, fetched_at, items, verify }, ... }, ... }
 *
 * Pulse entry, BLI Legal Tech Hackathon 2.
 */

import {
	consensusIdenticalAggregation,
	cre,
	type HTTPSendRequester,
	json,
	Runner,
	type Runtime,
} from '@chainlink/cre-sdk'

type Config = {
	schedule: string
	pulseApiUrl: string
	feedKey: string
}

type PulseSnapshot = {
	fetched_at: string
	digest: string
	items: number
	verify: string
}

type PulseFeedData = {
	articles: unknown[]
	source_count: number
	snapshot: PulseSnapshot
	note?: string
}

type PulseFeedResponse = {
	category: string
	label: string
	data: PulseFeedData
	timestamp: string
}

type SealRecord = {
	day: string
	digest: string
	items: number
	feed: string
	verify_path: string
	fetched_at: string
}

const initWorkflow = (config: Config) => {
	const cron = new cre.capabilities.CronCapability()
	return [cre.handler(cron.trigger({ schedule: config.schedule }), onDailyCron)]
}

const fetchPulseSeal = (sendRequester: HTTPSendRequester, config: Config): string => {
	const url = `${config.pulseApiUrl}/data/feed/${config.feedKey}`

	const resp = sendRequester.sendRequest({
		url,
		method: 'GET' as const,
		headers: {
			'Accept': 'application/json',
			'User-Agent': 'pulse-cre-workflow/1.0',
		},
	}).result()

	const feed = json(resp) as PulseFeedResponse

	const snap = feed?.data?.snapshot
	if (!snap?.digest) {
		throw new Error(`No snapshot.digest in Pulse response for feed=${config.feedKey}`)
	}

	// Extract UTC date from fetched_at (e.g. "2026-10-30T13:23:04.121964+00:00")
	const day = snap.fetched_at.slice(0, 10)

	const record: SealRecord = {
		day,
		digest: snap.digest,
		items: snap.items,
		feed: config.feedKey,
		verify_path: snap.verify,
		fetched_at: snap.fetched_at,
	}

	return JSON.stringify(record)
}

const onDailyCron = (runtime: Runtime<Config>): string => {
	const triggeredAt = new Date().toISOString()

	runtime.log(`Pulse seal run | triggered_at=${triggeredAt}`)
	runtime.log(`Fetching | ${runtime.config.pulseApiUrl}/data/feed/${runtime.config.feedKey}`)

	const httpClient = new cre.capabilities.HTTPClient()

	// DON nodes fetch independently. Identical aggregation: consensus only when
	// the nodes return the same digest, so no single fetch can slip in an edit.
	const raw = httpClient
		.sendRequest(
			runtime,
			fetchPulseSeal,
			consensusIdenticalAggregation<string>(),
		)(runtime.config)
		.result()

	const record: SealRecord = JSON.parse(raw)

	runtime.log(
		`Seal confirmed | day=${record.day} digest=${record.digest.slice(0, 16)}... items=${record.items}`,
	)

	return JSON.stringify(
		{
			pulse_seal: record,
			workflow: 'pulse-daily-regulatory-seal',
			triggered_at: triggeredAt,
		},
		null,
		2,
	)
}

export async function main() {
	const runner = await Runner.newRunner<Config>()
	await runner.run(initWorkflow)
}

main()

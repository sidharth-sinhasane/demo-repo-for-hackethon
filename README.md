# CartCrash

CartCrash is a database-free checkout used to demonstrate a change-aware
production incident agent.

## Story

1. A pull request merges into the production branch.
2. Vercel automatically deploys it.
3. The API logs Vercel's deployment commit SHA to OpenObserve.
4. A coupon regression returns HTTP 500.
5. OpenObserve alerts the agent.
6. The agent correlates the SHA and stack frame with GitHub, then reports to Slack.

The UI remains available while checkout fails. This is a real partial outage,
not a fake error log.

## Local run

Node.js 20 or newer is required. There are no package dependencies.

```bash
npm run dev
```

Open http://127.0.0.1:3000. This loads the existing local `.env`.

## OpenObserve

The server reads `O2_INGESTION_URL` and `O2_AUTH_HEADER`. Every health check
and checkout awaits ingestion before completing, which suits Vercel's
request-based runtime.

Alert on:

```text
event_name = 'cart.checkout.failed'
incident_candidate = true
```

Useful evidence fields include `git_commit_sha`, `service_name`,
`http_status_code`, `error_type`, `stack_trace`, and
`failure_fingerprint`. Local filesystem paths are removed from stack traces.

## Vercel

Import this repository in the Vercel dashboard. Keep default framework and
build settings. Add `O2_INGESTION_URL` and `O2_AUTH_HEADER` in Project
Settings for Production and Preview. Enable Vercel system environment variables
so `VERCEL_GIT_COMMIT_SHA` is available at runtime.

## Regression PR

Healthy `lib/checkout.js` contains:

```js
const discountRate = COUPON_RATES[normalizedCoupon]?.rate ?? 0;
```

Create a PR titled **Optimize coupon lookup** and change it to:

```js
const discountRate = COUPON_RATES[normalizedCoupon].rate;
```

It remains valid JavaScript and known coupons still work, but `FLASH25` now
throws a real TypeError after Vercel deploys the merge.

## Test

```bash
npm test
```

# Checkout Release Lab

A deliberately small checkout service for demonstrating a change-aware incident
agent. The service starts healthy, can roll out a known regression, generates
repeatable traffic, and exports structured logs to OpenObserve.

The application is a test fixture, not the incident agent itself. Its purpose is
to provide known ground truth for reliability testing:

- the same request succeeds on the stable release;
- it fails on the regression release;
- every event identifies the deployed revision;
- the stack trace points to the file changed by the regression PR.

## Run locally

Python 3.11 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open <http://127.0.0.1:8000>. The dashboard provides buttons for the entire
demo sequence.

## Connect OpenObserve Cloud

Copy `.env.example` values into the secret/configuration mechanism you use to
start the application. Do not commit real credentials.

The ingestion URL is the full JSON ingestion endpoint:

```text
https://<openobserve-host>/api/<organization>/checkout_demo/_json
```

The authorization value must include the authentication scheme, for example
`Basic <encoded-credential>`. The application never includes it in status
responses or logs.

When configuration is absent, the application still works and writes the same
structured events to stdout. The dashboard's telemetry indicator shows whether
remote export is configured and whether its most recent batch succeeded.

Suggested OpenObserve stream: `checkout_demo`.

Useful incident fields:

```text
event_name = 'checkout.failed'
incident_candidate = true
http_status_code = 500
service_name = 'checkout-api'
git_commit_sha = '<deployed revision>'
```

After the first events arrive, create an OpenObserve real-time alert matching
`incident_candidate = true`, or a scheduled alert that counts these records in
a short lookback window. Set its webhook destination to the deployed incident
agent.

## Demonstrate the regression

1. Keep the stable release selected and click **Run baseline**. All requests
   succeed even though they use an unknown coupon.
2. Paste the merged regression PR's commit SHA into the revision field.
3. Click **Deploy regression**. This represents the explicit rollout that
   normally follows a merge.
4. Click **Trigger incident**. All requests fail with the same error signature.
5. OpenObserve receives the failure events and calls the incident agent.
6. The agent uses `git_commit_sha` to find the PR, verifies that its changed
   files overlap the stack trace, and reports the evidence to Slack.
7. Click **Recover stable** and run the baseline again to show recovery.

The deploy button is a local release simulator. It makes evaluation repeatable
without requiring CI/CD infrastructure, and it deliberately treats "merged"
and "deployed" as separate events.

## Create the demonstration PR

The default release is defined near the top of `app/checkout.py`:

```python
DEFAULT_RELEASE = "stable"
```

For the regression PR, change it to:

```python
DEFAULT_RELEASE = "regression"
```

A suitable PR title is **Enable optimized coupon lookup**. The regression path
uses `COUPON_RATES.get(code)` without a fallback, causing an unknown coupon to
produce `Decimal * None`.

After that PR is merged, a local process does not update automatically. Either:

- update the local checkout through your normal IDE/GitHub workflow and restart
  the server, which is the most realistic deployment; or
- use the dashboard's **Deploy regression** button and paste the merged SHA,
  which is the deterministic hackathon demonstration.

Do not present the merge itself as the production failure. The rollout of the
merged revision is what changes runtime behavior.

## Test

The core behavior tests use only Python's standard library:

```bash
python3 -m unittest discover -s tests -v
```

They establish the ground truth expected from the incident agent: stable accepts
the unknown coupon, while regression raises the known failure.

## Main endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /` | Demonstration dashboard |
| `GET /healthz` | Process health |
| `GET /api/status` | Current release and telemetry state |
| `POST /api/checkout` | Checkout request |
| `POST /demo/traffic` | Generate a controlled batch of requests |
| `POST /demo/deploy` | Roll out stable or regression behavior locally |

## Safety

This application processes no real payments or customer information. Generated
request IDs and order IDs are synthetic. The deploy and traffic endpoints are
intended only for a local demonstration environment.

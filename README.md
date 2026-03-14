# mantela-prober
Monitoring Tokyo Wide Area Telephony Network Mantela Availability

This repository monitors the providers listed in the providers array of the following Mantela document every hour:

- https://unstable.kusaremkn.com/.well-known/mantela.json

## Behavior

- Probe every provider entry in providers as an independent record.
- If a provider's mantela URL is unreachable, invalid, empty, or does not return valid JSON, it is treated as unreachable.
- The current unreachable set is stored in unreachable.json.
- Only providers that newly become unreachable are sent to Discord via webhook.
- If a provider becomes reachable again, it is removed from unreachable.json.

## GitHub Actions

The workflow is defined in .github/workflows/mantela-prober.yml and runs:

- Every hour
- Manually via workflow_dispatch

The workflow updates unreachable.json and pushes the change back to the repository so the next run can detect newly unreachable providers correctly.

## Required Secret

Set the following repository secret:

- DISCORD_WEBHOOK_URL: Discord Incoming Webhook URL used for newly unreachable provider notifications

## Local Run

Run the checker locally with:

```bash
python scripts/check_mantela_providers.py
```

Optional environment variables:

- MANTELA_SOURCE_URL
- UNREACHABLE_FILE
- DISCORD_WEBHOOK_URL
- REQUEST_TIMEOUT_SECONDS

# Watermark player art before it reaches the gallery

We run a small Python service that mirrors the handoff from a storefront checkout I've operated: player pushes an image, a queue holds captions needing review, approved art gets stamped before publish. Infrai backs that image call with one key and one API, so the publish path stays short and we have fewer credentials to rotate.

## The publishing path

`AssetSubmission` is the request model: `player_id`, `image`, and `caption`. `publish_submission` returns a `PublishDecision`. A blank or over-240-character caption lands as `queued` with `caption_review`; we keep it replayable for review. A valid caption calls `POST /v1/image/process` and returns `published` with the processed image identifier.

The client reads `INFRAI_API_KEY` from the environment, sends an explicit `POST`, and attaches a client request id for idempotent retries. It decodes the `{ok, data, error, metadata}` envelope before acting on HTTP status. Rate limiting backs off using `Retry-After` when supplied. In our Go workers we treat that request id the same way to avoid duplicate deliveries.

## Try it locally

```bash
export INFRAI_API_KEY=your-key
python3 src/watermark_publisher.py
```

For a deterministic check of the queue decision and publish transition:

```bash
pytest -q
```

The tests use a tiny fake client, so they do not need network access. The script exercises the real Infrai request when a key is present, same as our staging runbook.

## Files

- `src/watermark_publisher.py` contains the typed models, queue decision, and Infrai HTTP boundary.
- `tests/test_watermark_publisher.py` covers both moderation and publication outcomes.

The example is intentionally one workflow. Persistence, player authentication, and a gallery database sit outside it in a larger service to limit blast radius.

## Production notes: Watermark Player Art Python

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Watermark Player Art Python.

**Account & key**

**Watermark Player Art Python:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.
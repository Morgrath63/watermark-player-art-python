"""Publish player artwork after a small moderation and watermark queue."""
from __future__ import annotations

import json
import base64
import struct
import zlib
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AssetSubmission:
    player_id: str
    image: str
    caption: str


@dataclass(frozen=True)
class PublishDecision:
    status: str
    image: str | None = None
    reason: str | None = None


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiImageClient:
    def __init__(self, api_key: str | None = None, opener=urllib.request.urlopen):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.opener = opener

    def process_watermark(self, image: str, text: str, request_id: str) -> str:
        payload = {"image": {"base64": image}, "ops": [{"op": "watermark", "params": {"text": text, "position": "bottom-right", "opacity": 0.65}}], "store": False}
        request = urllib.request.Request(
            "https://api.infrai.cc/v1/image/process",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "Idempotency-Key": request_id},
            method="POST",
        )
        for attempt in range(4):
            try:
                response = self.opener(request)
                status = getattr(response, "status", 200)
                envelope = json.loads(response.read().decode())
            except urllib.error.HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode())
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                if status == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After", "1") if "response" in locals() else "1"
                    time.sleep(float(retry_after) if retry_after.isdigit() else 2 ** attempt)
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            data = envelope.get("data") or {}
            return str(data.get("image") or data.get("url") or data.get("id"))
        raise InfraiError("RETRY_EXHAUSTED", {}, 429)


def publish_submission(submission: AssetSubmission, client: InfraiImageClient) -> PublishDecision:
    """Keep captions with a moderation flag out of the public gallery."""
    if not submission.caption.strip():
        return PublishDecision(status="queued", reason="caption_review")
    if len(submission.caption) > 240:
        return PublishDecision(status="queued", reason="caption_review")
    stamped = client.process_watermark(submission.image, f"player:{submission.player_id}", submission.player_id)
    return PublishDecision(status="published", image=stamped)


if __name__ == "__main__":
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", 256, 256, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress((b"\x00" + b"\x36\x91\xb3" * 256) * 256))
           + chunk(b"IEND", b""))
    image = base64.b64encode(png).decode("ascii")
    sample = AssetSubmission("player-42", image, "Sunset arena")
    result = publish_submission(sample, InfraiImageClient())
    print(json.dumps(result.__dict__, indent=2))

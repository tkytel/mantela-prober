#!/usr/bin/env python3

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SOURCE_URL = os.environ.get(
    "MANTELA_SOURCE_URL",
    "https://unstable.kusaremkn.com/.well-known/mantela.json",
)
STATE_FILE = Path(os.environ.get("UNREACHABLE_FILE", "unreachable.json"))
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "20"))
USER_AGENT = "mantela-prober/1.0"


@dataclass(frozen=True)
class ProviderState:
    identifier: str
    name: str
    prefix: str
    mantela: str
    unavailable: bool = False

    @property
    def key(self) -> str:
        return "::".join([self.identifier, self.prefix, self.name, self.mantela])

    def to_json(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "name": self.name,
            "prefix": self.prefix,
            "mantela": self.mantela,
            "unavailable": self.unavailable,
        }


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        charset = response.headers.get_content_charset("utf-8")
        return json.loads(response.read().decode(charset))


def load_providers() -> list[ProviderState]:
    document = fetch_json(SOURCE_URL)
    providers = document.get("providers")
    if not isinstance(providers, list):
        raise ValueError("source mantela.json does not contain a providers array")

    result: list[ProviderState] = []
    for entry in providers:
        if not isinstance(entry, dict):
            continue

        result.append(
            ProviderState(
                identifier=str(entry.get("identifier", "")),
                name=str(entry.get("name", "")),
                prefix=str(entry.get("prefix", "")),
                mantela=str(entry.get("mantela", "")).strip(),
                unavailable=bool(entry.get("unavailable", False)),
            )
        )

    return result


def load_state() -> dict[str, ProviderState]:
    if not STATE_FILE.exists():
        return {}

    with STATE_FILE.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    items = raw.get("providers", []) if isinstance(raw, dict) else []
    state: dict[str, ProviderState] = {}
    for entry in items:
        if not isinstance(entry, dict):
            continue
        provider = ProviderState(
            identifier=str(entry.get("identifier", "")),
            name=str(entry.get("name", "")),
            prefix=str(entry.get("prefix", "")),
            mantela=str(entry.get("mantela", "")).strip(),
            unavailable=bool(entry.get("unavailable", False)),
        )
        state[provider.key] = provider

    return state


def save_state(state: dict[str, ProviderState]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    providers = [state[key].to_json() for key in sorted(state)]
    payload = {
        "providers": providers,
    }
    with STATE_FILE.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def validate_url(url: str) -> str | None:
    if not url:
        return "Mantela URL が空です"

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "Mantela URL が不正です"

    return None


def probe_provider(provider: ProviderState) -> str | None:
    if not provider.mantela:
        return None

    validation_error = validate_url(provider.mantela)
    if validation_error:
        return validation_error

    try:
        fetch_json(provider.mantela)
    except urllib.error.HTTPError as error:
        return f"HTTP {error.code}"
    except urllib.error.URLError as error:
        reason = getattr(error, "reason", error)
        return f"URL error: {reason}"
    except TimeoutError:
        return "request timed out"
    except json.JSONDecodeError:
        return "response was not valid JSON"
    except Exception as error:
        return f"unexpected error: {error}"

    return None


def build_notification(newly_unreachable: list[tuple[ProviderState, str]]) -> dict[str, Any]:
    lines = []
    for provider, reason in newly_unreachable:
        lines.append(
            "\n".join(
                [
                    f"- 局: {provider.name or '(unknown)'}",
                    f"  prefix: {provider.prefix or '(none)'}",
                    f"  識別子: {provider.identifier or '(none)'}",
                    f"  Mantela: {provider.mantela or '(empty)'}",
                    f"  理由: {reason}",
                ]
            )
        )

    return {
        "content": "Mantela provider unreachable detected.",
        "embeds": [
            {
                "title": f"新たに Mantela に疎通できない局が見つかりました: {len(newly_unreachable)}",
                "description": "\n\n".join(lines)[:4000],
                "color": 15158332,
            }
        ],
    }


def send_discord_notification(newly_unreachable: list[tuple[ProviderState, str]]) -> None:
    if not newly_unreachable or not DISCORD_WEBHOOK_URL:
        return

    payload = json.dumps(build_notification(newly_unreachable)).encode("utf-8")
    request = urllib.request.Request(
        DISCORD_WEBHOOK_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS):
        pass


def main() -> int:
    providers = load_providers()
    previous_state = load_state()
    next_state: dict[str, ProviderState] = {}
    newly_unreachable: list[tuple[ProviderState, str]] = []
    recovered: list[ProviderState] = []
    skipped = 0

    for provider in providers:
        if not provider.mantela:
            skipped += 1
            continue

        error = probe_provider(provider)
        if error is None:
            if provider.key in previous_state:
                recovered.append(provider)
            continue

        next_state[provider.key] = provider
        if provider.key not in previous_state:
            newly_unreachable.append((provider, error))

    save_state(next_state)
    send_discord_notification(newly_unreachable)

    print(f"Checked providers: {len(providers)}")
    print(f"Skipped providers without mantela URL: {skipped}")
    print(f"Currently unreachable: {len(next_state)}")
    print(f"Newly unreachable: {len(newly_unreachable)}")
    print(f"Recovered: {len(recovered)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise

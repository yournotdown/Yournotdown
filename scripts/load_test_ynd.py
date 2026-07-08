#!/usr/bin/env python3
"""Lightweight safe load-test harness for YourNotDown public API paths."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import sys
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


DEFAULT_LOCAL_TARGET = "http://localhost:8000"
PRODUCTION_DOMAIN_HINT = "yournotdown.com"
DEFAULT_TIMEOUT = 10.0
SAFE_VIBES = ("just-vibing", "down", "very-down", "send-it")


@dataclass
class RequestResult:
    endpoint: str
    ok: bool
    status: str
    latency_ms: float


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total_requests = 0
        self.success_count = 0
        self.failure_count = 0
        self.latencies_ms: list[float] = []
        self.errors = Counter()

    def record(self, result: RequestResult) -> None:
        with self._lock:
            self.total_requests += 1
            self.latencies_ms.append(result.latency_ms)
            if result.ok:
                self.success_count += 1
            else:
                self.failure_count += 1
                self.errors[(result.endpoint, result.status)] += 1

    def snapshot(self) -> dict[str, Any]:
        latencies = sorted(self.latencies_ms)
        average = statistics.fmean(latencies) if latencies else 0.0
        return {
            "total_requests": self.total_requests,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "average_latency_ms": average,
            "p95_latency_ms": percentile(latencies, 95),
            "p99_latency_ms": percentile(latencies, 99),
            "errors": [
                {"endpoint": endpoint, "status": status, "count": count}
                for (endpoint, status), count in sorted(self.errors.items())
            ],
        }


def percentile(values: list[float], pct: int) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    rank = (pct / 100) * (len(values) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return values[low]
    lower_value = values[low]
    upper_value = values[high]
    return lower_value + (upper_value - lower_value) * (rank - low)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safe public API load-test harness for YourNotDown.",
    )
    parser.add_argument(
        "--target",
        default=os.environ.get("YND_LOAD_TEST_TARGET", DEFAULT_LOCAL_TARGET),
        help="Backend base URL, e.g. http://localhost:8000 or https://api.yournotdown.com",
    )
    parser.add_argument("--allow-production", action="store_true", help="Required for any yournotdown.com target.")
    parser.add_argument("--users", type=int, default=10, help="Logical users to simulate.")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent worker threads.")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds.")
    parser.add_argument("--ramp-up", type=int, default=10, help="Ramp-up time in seconds.")
    parser.add_argument("--city", default="nashville", help="City slug to test.")
    parser.add_argument("--vibe", default="down", choices=SAFE_VIBES, help="Vibe slug to test.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Per-request timeout in seconds.")
    parser.add_argument(
        "--enable-save",
        action="store_true",
        help="Include POST /api/itinerary/save. Disabled by default because it writes more data and may send email.",
    )
    parser.add_argument(
        "--save-email",
        default="",
        help="Required when --enable-save is used. Use a dedicated test inbox only.",
    )
    return parser.parse_args()


def normalize_target(target: str) -> tuple[str, str, str]:
    raw_target = (target or "").strip()
    if not raw_target:
        raise SystemExit("Missing --target")
    if "://" not in raw_target:
        raw_target = f"http://{raw_target}"
    parsed = parse.urlparse(raw_target)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit(f"Invalid target URL: {target}")
    root_path = parsed.path.rstrip("/")
    if root_path.endswith("/api"):
        api_path = root_path
        root_path = root_path[:-4]
    else:
        api_path = f"{root_path}/api" if root_path else "/api"
    root_base = parse.urlunparse((parsed.scheme, parsed.netloc, root_path, "", "", ""))
    api_base = parse.urlunparse((parsed.scheme, parsed.netloc, api_path, "", "", ""))
    return raw_target, root_base.rstrip("/"), api_base.rstrip("/")


def assert_safe_target(raw_target: str, allow_production: bool) -> None:
    parsed = parse.urlparse(raw_target)
    host = (parsed.netloc or "").lower()
    if PRODUCTION_DOMAIN_HINT in host and not allow_production:
        raise SystemExit(
            "Refusing production-like target without --allow-production. "
            "Use local/staging first, or pass --allow-production for a tiny smoke test only."
        )


def build_request(url: str, payload: dict[str, Any] | None = None) -> request.Request:
    headers = {
        "Accept": "application/json",
        "User-Agent": "ynd-load-test/1.0",
    }
    if payload is None:
        return request.Request(url, headers=headers, method="GET")
    body = json.dumps(payload).encode("utf-8")
    headers["Content-Type"] = "application/json"
    return request.Request(url, data=body, headers=headers, method="POST")


def send_json(req: request.Request, timeout: float) -> tuple[int, Any]:
    with request.urlopen(req, timeout=timeout) as response:
        status = getattr(response, "status", 200)
        body = response.read()
    if not body:
        return status, None
    try:
        return status, json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return status, body.decode("utf-8", errors="replace")


def record_call(metrics: Metrics, endpoint: str, timeout: float, req: request.Request) -> tuple[bool, Any]:
    start = time.perf_counter()
    try:
        status_code, payload = send_json(req, timeout)
        latency_ms = (time.perf_counter() - start) * 1000
        ok = 200 <= status_code < 300
        metrics.record(
            RequestResult(
                endpoint=endpoint,
                ok=ok,
                status=str(status_code),
                latency_ms=latency_ms,
            )
        )
        return ok, payload
    except error.HTTPError as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        metrics.record(
            RequestResult(
                endpoint=endpoint,
                ok=False,
                status=f"http_{exc.code}",
                latency_ms=latency_ms,
            )
        )
        try:
            payload = exc.read().decode("utf-8", errors="replace")
        except Exception:
            payload = ""
        return False, payload
    except Exception as exc:  # pragma: no cover - defensive
        latency_ms = (time.perf_counter() - start) * 1000
        metrics.record(
            RequestResult(
                endpoint=endpoint,
                ok=False,
                status=type(exc).__name__,
                latency_ms=latency_ms,
            )
        )
        return False, str(exc)


def maybe_save_itinerary(
    api_base: str,
    timeout: float,
    metrics: Metrics,
    city: str,
    vibe: str,
    itinerary: dict[str, Any],
    visitor_id: str,
    save_email: str,
) -> None:
    payload = {
        "email": save_email,
        "visitor_id": visitor_id,
        "city_slug": city,
        "vibe": vibe,
        "source_itinerary_id": itinerary.get("id"),
        "steps": itinerary.get("steps") or [],
        "locked_slots": [],
        "marketing_opt_in": False,
    }
    req = build_request(f"{api_base}/itinerary/save", payload)
    record_call(metrics, "POST /api/itinerary/save", timeout, req)


def simulate_user_journey(
    api_base: str,
    timeout: float,
    metrics: Metrics,
    city: str,
    vibe: str,
    enable_save: bool,
    save_email: str,
    visitor_id: str,
) -> None:
    ok, _ = record_call(metrics, "GET /api/health", timeout, build_request(f"{api_base}/health"))
    if not ok:
        return

    businesses_url = f"{api_base}/businesses?{parse.urlencode({'city': city})}"
    ok, _ = record_call(metrics, "GET /api/businesses", timeout, build_request(businesses_url))
    if not ok:
        return

    homepage_event = {
        "event_type": "homepage_visit",
        "visitor_id": visitor_id,
        "city_slug": city,
    }
    ok, _ = record_call(
        metrics,
        "POST /api/analytics/track",
        timeout,
        build_request(f"{api_base}/analytics/track", homepage_event),
    )
    if not ok:
        return

    vibe_event = {
        "event_type": "vibe_click",
        "visitor_id": visitor_id,
        "city_slug": city,
        "vibe": vibe,
    }
    ok, _ = record_call(
        metrics,
        "POST /api/analytics/track",
        timeout,
        build_request(f"{api_base}/analytics/track", vibe_event),
    )
    if not ok:
        return

    generate_payload = {
        "vibe": vibe,
        "city": city,
        "exclude_ids": [],
        "exclude_ids_by_slot": {},
        "exclude_event_ids": [],
        "live_music_event_mode": "normal",
        "locked_steps": {},
    }
    ok, itinerary = record_call(
        metrics,
        "POST /api/itinerary/generate",
        timeout,
        build_request(f"{api_base}/itinerary/generate", generate_payload),
    )
    if not ok or not isinstance(itinerary, dict):
        return

    if enable_save:
        maybe_save_itinerary(api_base, timeout, metrics, city, vibe, itinerary, visitor_id, save_email)


def run_worker(
    worker_index: int,
    start_delay: float,
    end_time: float,
    api_base: str,
    timeout: float,
    metrics: Metrics,
    city: str,
    vibe: str,
    enable_save: bool,
    save_email: str,
    user_count: int,
) -> None:
    if start_delay > 0:
        time.sleep(start_delay)
    logical_user_id = worker_index % max(1, user_count)
    random.seed(f"ynd-load-test-{worker_index}-{logical_user_id}")
    while time.time() < end_time:
        visitor_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"ynd-load-test-{logical_user_id}"))
        simulate_user_journey(
            api_base=api_base,
            timeout=timeout,
            metrics=metrics,
            city=city,
            vibe=vibe,
            enable_save=enable_save,
            save_email=save_email,
            visitor_id=visitor_id,
        )


def validate_args(args: argparse.Namespace) -> None:
    if args.users < 1 or args.concurrency < 1:
        raise SystemExit("--users and --concurrency must both be >= 1")
    if args.duration < 1:
        raise SystemExit("--duration must be >= 1")
    if args.ramp_up < 0:
        raise SystemExit("--ramp-up must be >= 0")
    if args.timeout <= 0:
        raise SystemExit("--timeout must be > 0")
    if args.concurrency > args.users:
        raise SystemExit("--concurrency cannot exceed --users for this harness")
    if args.enable_save and not args.save_email:
        raise SystemExit("--enable-save requires --save-email. Use a dedicated test inbox only.")


def print_header(args: argparse.Namespace, root_base: str, api_base: str) -> None:
    print("YourNotDown load test harness")
    print(f"Target root: {root_base}")
    print(f"Target API : {api_base}")
    print(f"Users      : {args.users}")
    print(f"Concurrency: {args.concurrency}")
    print(f"Duration   : {args.duration}s")
    print(f"Ramp-up    : {args.ramp_up}s")
    print(f"City       : {args.city}")
    print(f"Vibe       : {args.vibe}")
    print(f"Save step  : {'enabled' if args.enable_save else 'disabled'}")
    if args.enable_save:
        print("WARNING: /api/itinerary/save is enabled and may send email.")


def print_summary(summary: dict[str, Any]) -> None:
    print("")
    print("Results")
    print(f"Total requests : {summary['total_requests']}")
    print(f"Success count  : {summary['success_count']}")
    print(f"Failure count  : {summary['failure_count']}")
    print(f"Average latency: {summary['average_latency_ms']:.2f} ms")
    print(f"P95 latency    : {summary['p95_latency_ms']:.2f} ms")
    print(f"P99 latency    : {summary['p99_latency_ms']:.2f} ms")
    print("Errors by endpoint/status:")
    if not summary["errors"]:
        print("  none")
        return
    for item in summary["errors"]:
        print(f"  {item['endpoint']} [{item['status']}]: {item['count']}")


def main() -> int:
    args = parse_args()
    validate_args(args)
    raw_target, root_base, api_base = normalize_target(args.target)
    assert_safe_target(raw_target, args.allow_production)
    print_header(args, root_base, api_base)

    metrics = Metrics()
    end_time = time.time() + args.duration

    try:
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = []
            for worker_index in range(args.concurrency):
                start_delay = 0.0
                if args.ramp_up:
                    start_delay = (args.ramp_up / max(1, args.concurrency)) * worker_index
                futures.append(
                    executor.submit(
                        run_worker,
                        worker_index,
                        start_delay,
                        end_time,
                        api_base,
                        args.timeout,
                        metrics,
                        args.city,
                        args.vibe,
                        args.enable_save,
                        args.save_email,
                        args.users,
                    )
                )
            for future in futures:
                future.result()
    except KeyboardInterrupt:
        print("\nInterrupted. Printing partial results.")

    print_summary(metrics.snapshot())
    return 0


if __name__ == "__main__":
    sys.exit(main())

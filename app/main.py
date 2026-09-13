"""FastAPI entry point for the checkout release lab."""

from __future__ import annotations

import logging
import os
import traceback
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path
from time import perf_counter
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

from app.checkout import DEFAULT_RELEASE, calculate_checkout
from app.release_state import Release, ReleaseState
from app.telemetry import EventLogger


SERVICE_NAME = "checkout-api"
DEPLOYMENT_ENVIRONMENT = "production-demo"
DEMO_COUPON = "FLASH25"

event_logger = EventLogger()
release_state = ReleaseState(os.getenv("DEMO_DEFAULT_RELEASE", DEFAULT_RELEASE))
dashboard_path = Path(__file__).parent / "static" / "index.html"

app = FastAPI(
    title="Checkout Release Lab",
    version="1.0.0",
    description="Deterministic incident fixture for a multi-app production support agent.",
)


class CheckoutRequest(BaseModel):
    order_id: str = Field(default="order-demo-001", min_length=1, max_length=80)
    subtotal: str = Field(default="125.00")
    coupon_code: str = Field(default=DEMO_COUPON, max_length=40)

    @field_validator("subtotal")
    @classmethod
    def valid_subtotal(cls, value: str) -> str:
        try:
            parsed = Decimal(value)
        except InvalidOperation as error:
            raise ValueError("subtotal must be a decimal number") from error
        if parsed <= 0 or parsed > Decimal("1000000"):
            raise ValueError("subtotal must be between 0 and 1000000")
        return value


class DeployRequest(BaseModel):
    release: Literal["stable", "regression"]
    git_commit_sha: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{7,64}$")
    pull_request_number: int | None = Field(default=None, ge=1)


class TrafficRequest(BaseModel):
    count: int = Field(default=8, ge=1, le=50)
    coupon_code: str = Field(default=DEMO_COUPON, max_length=40)


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    return HTMLResponse(dashboard_path.read_text(encoding="utf-8"))


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/api/status")
async def status() -> dict[str, object]:
    return {
        "service": SERVICE_NAME,
        "environment": DEPLOYMENT_ENVIRONMENT,
        "release": release_state.current().as_dict(),
        "telemetry": event_logger.sink.status(),
    }


@app.post("/api/checkout")
async def checkout(request: CheckoutRequest) -> dict[str, object]:
    return _perform_checkout(request)


@app.post("/demo/deploy")
async def deploy(request: DeployRequest) -> dict[str, object]:
    previous = release_state.current()
    current = release_state.deploy(
        name=request.release,
        git_commit_sha=request.git_commit_sha,
        pull_request_number=request.pull_request_number,
    )
    event_logger.emit(
        logging.WARNING,
        "deployment.completed",
        message=f"deployed {current.version}",
        **_release_fields(current),
        previous_service_version=previous.version,
        previous_git_commit_sha=previous.git_commit_sha,
        incident_candidate=False,
    )
    return {"deployed": True, "release": current.as_dict()}


@app.post("/demo/traffic")
async def generate_traffic(request: TrafficRequest) -> dict[str, object]:
    successes = 0
    failures = 0
    failure_ids: list[str] = []

    for index in range(request.count):
        checkout_request = CheckoutRequest(
            order_id=f"order-demo-{index + 1:03d}",
            subtotal="125.00",
            coupon_code=request.coupon_code,
        )
        try:
            _perform_checkout(checkout_request)
            successes += 1
        except HTTPException as error:
            failures += 1
            if isinstance(error.detail, dict):
                failure_ids.append(str(error.detail.get("request_id", "unknown")))

    release = release_state.current()
    return {
        "requested": request.count,
        "successes": successes,
        "failures": failures,
        "failure_request_ids": failure_ids,
        "release": release.as_dict(),
        "expected_incident": release.name == "regression" and failures > 0,
    }


@app.on_event("shutdown")
async def shutdown_exporter() -> None:
    event_logger.sink.close()


def _perform_checkout(request: CheckoutRequest) -> dict[str, object]:
    release = release_state.current()
    request_id = str(uuid.uuid4())
    started = perf_counter()

    try:
        totals = calculate_checkout(
            subtotal=Decimal(request.subtotal),
            coupon_code=request.coupon_code,
            release=release.name,
        )
        duration_ms = round((perf_counter() - started) * 1000, 3)
        event_logger.emit(
            logging.INFO,
            "checkout.completed",
            message="checkout completed successfully",
            **_release_fields(release),
            request_id=request_id,
            order_id=request.order_id,
            route="/api/checkout",
            http_method="POST",
            http_status_code=200,
            duration_ms=duration_ms,
            coupon_code=request.coupon_code,
            incident_candidate=False,
        )
        return {
            "ok": True,
            "request_id": request_id,
            "order_id": request.order_id,
            "totals": totals.as_dict(),
            "release": release.as_dict(),
        }
    except Exception as error:
        duration_ms = round((perf_counter() - started) * 1000, 3)
        event_logger.emit(
            logging.ERROR,
            "checkout.failed",
            message="checkout calculation failed after coupon lookup",
            **_release_fields(release),
            request_id=request_id,
            order_id=request.order_id,
            route="/api/checkout",
            http_method="POST",
            http_status_code=500,
            duration_ms=duration_ms,
            coupon_code=request.coupon_code,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace="".join(traceback.format_exception(error)),
            failure_fingerprint="checkout.calculate_discount.none_rate",
            incident_candidate=True,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": "checkout failed",
                "request_id": request_id,
                "release": release.version,
                "git_commit_sha": release.git_commit_sha,
            },
        ) from error


def _release_fields(release: Release) -> dict[str, object]:
    return {
        "service_name": SERVICE_NAME,
        "service_version": release.version,
        "git_commit_sha": release.git_commit_sha,
        "pull_request_number": release.pull_request_number,
        "deployment_environment": DEPLOYMENT_ENVIRONMENT,
        "deployed_at": release.deployed_at,
    }

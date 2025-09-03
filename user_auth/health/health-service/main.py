import os
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
import httpx
from kubernetes import config, client
from kubernetes.client import ApiException
import smtplib
from email.message import EmailMessage
import logging

# ---- Logging ----
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("health-service")

# ---- Config ----
NAMESPACE = os.getenv("K8S_NAMESPACE", "user-health")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "20"))
RESTART_THRESHOLD = int(os.getenv("RESTART_THRESHOLD", "3"))

ALERT_SLACK_WEBHOOK = os.getenv("ALERT_SLACK_WEBHOOK", "http://datama-db-service.user-health.svc.cluster.local:8001/webhook/")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))

# ---- K8s Client ----
try:
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        config.load_incluster_config()
    else:
        config.load_kube_config()
    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
except Exception as e:
    log.warning("K8s client init failed: %s", e)
    core_v1 = None
    apps_v1 = None

# ---- FastAPI ----
app = FastAPI(title="User Pod Health Service", version="1.0.0")

# In-memory event store (可换DB)
EVENTS: Dict[str, Any] = {}   # key: pod_name -> last event

class SidecarReport(BaseModel):
    user: str
    pod: str
    timestamp: str
    problem: Dict[str, Any]

async def send_slack(text: str):
    if not ALERT_SLACK_WEBHOOK:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as cli:
            await cli.post(ALERT_SLACK_WEBHOOK, json={"text": text})
    except Exception as e:
        log.warning("Slack alert failed: %s", e)

def send_email(subject: str, body: str):
    if not (SMTP_HOST and ALERT_EMAIL_TO and ALERT_EMAIL_FROM):
        return
    try:
        msg = EmailMessage()
        msg["From"] = ALERT_EMAIL_FROM
        msg["To"] = ALERT_EMAIL_TO
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5) as s:
            s.send_message(msg)
    except Exception as e:
        log.warning("Email alert failed: %s", e)

async def raise_alert(title: str, body: str):
    await asyncio.gather(
        send_slack(f"*{title}*\n{body}"),
        asyncio.to_thread(send_email, title, body)
    )

@app.get("/health")
async def health():
    return {"status":"ok","time": datetime.now(timezone.utc).isoformat(),"namespace":NAMESPACE}

@app.get("/events")
async def events():
    # 简单返回最近事件（只用于验证）
    return EVENTS

@app.post("/report")
async def report(r: SidecarReport):
    EVENTS[r.pod] = r.model_dump()
    title = f"[Sidecar] 业务异常 user={r.user} pod={r.pod}"
    body = json.dumps(r.problem, ensure_ascii=False)
    log.warning("%s | %s", title, body)
    asyncio.create_task(raise_alert(title, f"time={r.timestamp}\nproblem={body}"))
    return {"status":"accepted"}

async def check_pods_loop():
    if not core_v1:
        log.warning("No K8s client, skip periodic checks.")
        return
    while True:
        try:
            pods = core_v1.list_namespaced_pod(
                namespace=NAMESPACE,
                label_selector="app=nginx-user"
            )
            for p in pods.items:
                pod_name = p.metadata.name
                user = (p.metadata.labels or {}).get("user","<unknown>")
                phase = p.status.phase
                statuses = p.status.container_statuses or []
                ready = all((s.ready for s in statuses)) if statuses else False
                # 重启阈值报警
                for cs in statuses:
                    rc = cs.restart_count or 0
                    if rc >= RESTART_THRESHOLD:
                        t = f"[HealthCheck] Pod 重启过多 user={user} pod={pod_name}"
                        b = f"container={cs.name} restartCount={rc} lastState={cs.last_state}"
                        log.error("%s | %s", t, b)
                        asyncio.create_task(raise_alert(t,b))
                # 非运行/未就绪报警
                if phase != "Running" or not ready:
                    t = f"[HealthCheck] Pod 非运行/未就绪 user={user} pod={pod_name}"
                    b = f"phase={phase} ready={ready}"
                    log.error("%s | %s", t, b)
                    asyncio.create_task(raise_alert(t,b))
                # 主动探测 sidecar /health
                ip = p.status.pod_ip
                if ip:
                    try:
                        async with httpx.AsyncClient(timeout=2) as cli:
                            resp = await cli.get(f"http://{ip}:9000/health")
                            if resp.status_code != 200:
                                raise RuntimeError(f"status={resp.status_code}")
                    except Exception as e:
                        t = f"[HealthCheck] Sidecar 健康检查失败 user={user} pod={pod_name}"
                        b = f"sidecar {ip}:9000/health error={e}"
                        log.error("%s | %s", t, b)
                        asyncio.create_task(raise_alert(t,b))
        except ApiException as e:
            log.warning("K8s API error: %s", e)
        except Exception as e:
            log.warning("check_pods_loop error: %s", e)
        await asyncio.sleep(CHECK_INTERVAL)

@app.on_event("startup")
async def startup():
    asyncio.create_task(check_pods_loop())

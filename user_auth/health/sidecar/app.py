import os
import time
import json
import socket
import logging
import threading
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone

import httpx

# -------- Config --------
HEALTH_SERVICE_URL = os.getenv("HEALTH_SERVICE_URL", "http://health-svc.user-health.svc.cluster.local:80/report")
USER = os.getenv("USER_ID", "unknown")
POD = os.getenv("POD_NAME", socket.gethostname())
DETECT_INTERVAL = int(os.getenv("DETECT_INTERVAL", "10"))
DETECTOR_PORT = int(os.getenv("DETECTOR_PORT", "9000"))
NGINX_ERROR_LOG = os.getenv("NGINX_ERROR_LOG", "/var/log/nginx/error.log")

# -------- Logging --------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("sidecar-detector")

# 状态信息用于 /health
STATE = {
    "last_report_time": None,
    "last_problem": None,
    "heartbeat": 0,
    "log_tail_position": 0
}

# -------- 指数退避上报 --------
async def post_with_backoff(url: str, payload: dict, base_delay=1, max_delay=64, max_attempts=8):
    delay = base_delay
    attempt = 0
    while True:
        attempt += 1
        try:
            async with httpx.AsyncClient(timeout=3) as cli:
                resp = await cli.post(url, json=payload)
                if resp.status_code < 300:
                    return True
                raise RuntimeError(f"status={resp.status_code}")
        except Exception as e:
            log.warning("report failed (attempt %s): %s", attempt, e)
            if attempt >= max_attempts:
                return False
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)

# -------- 业务检测（示例：检查 nginx /status + 监控 error.log 触发）--------
def detect_business_issue() -> dict | None:
    # 1) HTTP 探测本地 nginx /status
    try:
        with httpx.Client(timeout=2) as cli:
            r = cli.get("http://127.0.0.1/")
            if r.status_code != 200:
                return {"type": "status_non_200", "detail": f"status={r.status_code}"}
    except Exception as e:
        return {"type": "status_unreachable", "detail": str(e)}

    # 2) error.log 最近是否出现 ERROR/crit
    try:
        if os.path.exists(NGINX_ERROR_LOG):
            with open(NGINX_ERROR_LOG, "rb") as f:
                f.seek(STATE["log_tail_position"])
                chunk = f.read(8192)
                if chunk:
                    STATE["log_tail_position"] = f.tell()
                    text = chunk.decode(errors="ignore")
                    for line in text.splitlines():
                        if "crit" in line.lower() or "error" in line.lower():
                            return {"type": "nginx_error_log", "detail": line[-500:]}
    except Exception as e:
        log.debug("log read error: %s", e)

    return None

async def detector_loop():
    while True:
        STATE["heartbeat"] += 1
        problem = detect_business_issue()
        if problem:
            payload = {
                "user": USER,
                "pod": POD,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "problem": problem
            }
            ok = await post_with_backoff(HEALTH_SERVICE_URL, payload)
            STATE["last_report_time"] = datetime.now(timezone.utc).isoformat()
            STATE["last_problem"] = problem
            if ok:
                log.warning("reported: %s", json.dumps(problem, ensure_ascii=False))
            else:
                log.error("report failed permanently: %s", json.dumps(problem, ensure_ascii=False))
        await asyncio.sleep(DETECT_INTERVAL)

# -------- /health Endpoint --------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({
                "status": "ok",
                "user": USER,
                "pod": POD,
                "heartbeat": STATE["heartbeat"],
                "last_report_time": STATE["last_report_time"],
                "last_problem": STATE["last_problem"],
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

def run_http_server():
    srv = HTTPServer(("0.0.0.0", DETECTOR_PORT), Handler)
    log.info("sidecar /health listening on :%s", DETECTOR_PORT)
    srv.serve_forever()

if __name__ == "__main__":
    # 后台线程跑 HTTP server，主线程跑检测协程
    t = threading.Thread(target=run_http_server, daemon=True)
    t.start()
    asyncio.run(detector_loop())

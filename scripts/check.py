#!/usr/bin/env python3
"""Проверка уровня 8: python3 scripts/check.py [-n N]"""

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTTP_TIMEOUT = 5
WAIT_TIMEOUT = 120
CMD_TIMEOUT = 300


class CheckFailed(Exception):
    pass


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Checker:
    def __init__(self, requests):
        self.n = requests
        self.project = f"hw3check-{secrets.token_hex(3)}"
        self.port = free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.env = {
            **os.environ,
            "APP_PORT": str(self.port),
            "GREETING": "Hello from check.py",
        }
        self.stage = "подготовка"


    def compose(self, *args, show=True):
        cmd = ["docker", "compose", "-p", self.project, *args]
        if show:
            print("$ docker compose " + " ".join(args), flush=True)
        try:
            res = subprocess.run(
                cmd, cwd=ROOT, env=self.env, capture_output=True,
                text=True, timeout=CMD_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            raise CheckFailed(f"команда не уложилась в {CMD_TIMEOUT} с: {' '.join(cmd)}")
        out = (res.stdout + res.stderr).strip()
        if show and out:
            print(out, flush=True)
        if res.returncode != 0:
            raise CheckFailed(f"команда завершилась с кодом {res.returncode}: {' '.join(cmd)}")
        return res.stdout.strip()

    def http(self, method, path, show=True):
        req = urllib.request.Request(self.base + path, method=method)
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                status, body = resp.status, resp.read().decode()
        except urllib.error.HTTPError as e:
            status, body = e.code, e.read().decode()
        except (urllib.error.URLError, OSError) as e:
            status, body = None, f"<нет ответа: {e}>"
        if show:
            print(f"$ curl -X {method} {self.base}{path}\n  -> HTTP {status} {body}", flush=True)
        try:
            data = json.loads(body)
        except ValueError:
            data = None
        return status, data

    def expect_status(self, method, path, expected):
        status, data = self.http(method, path)
        if status != expected:
            raise CheckFailed(f"{method} {path}: ожидался HTTP {expected}, получен {status}")
        return data

    def expect_count(self, method, path, expected):
        data = self.expect_status(method, path, 200)
        if data.get("count") != expected:
            raise CheckFailed(f"{method} {path}: ожидался count={expected}, получен {data.get('count')}")
        return data

    def wait_ready(self):
        deadline = time.monotonic() + WAIT_TIMEOUT
        while time.monotonic() < deadline:
            status, _ = self.http("GET", "/readyz", show=False)
            if status == 200:
                print(f"  /readyz -> 200 через {WAIT_TIMEOUT - (deadline - time.monotonic()):.1f} с")
                return
            time.sleep(1)
        raise CheckFailed(f"/readyz не вернул 200 за {WAIT_TIMEOUT} с")

    def section(self, title):
        self.stage = title
        print(f"\n=== {title} ===", flush=True)


    def run(self):
        n = self.n
        print(f"Проект: {self.project}, порт приложения: {self.port}, N = {n}")

        self.section("1. Запуск с пустым хранилищем")
        self.compose("up", "-d", "--build", "--quiet-build", "--quiet-pull",
                     "--wait", "--wait-timeout", str(WAIT_TIMEOUT))
        self.compose("ps", "--format", "table {{.Service}}\t{{.Status}}\t{{.Ports}}")
        if not self.compose("port", "app", "8000", show=False).endswith(f":{self.port}"):
            raise CheckFailed("порт приложения не опубликован")
        redis_port = subprocess.run(
            ["docker", "compose", "-p", self.project, "port", "redis", "6379"],
            cwd=ROOT, env=self.env, capture_output=True, text=True, timeout=CMD_TIMEOUT,
        )
        published = redis_port.stdout.strip()
        # для неопубликованного порта compose печатает ":0"
        if redis_port.returncode == 0 and published and not published.endswith(":0"):
            raise CheckFailed(f"порт Redis опубликован: {published}")
        print("  порт Redis на компьютер не опубликован — ок")
        self.expect_count("GET", "/", 0)

        self.section(f"2. {n} запросов POST /increment")
        for i in range(1, n + 1):
            self.expect_count("POST", "/increment", i)
        self.expect_count("GET", "/", n)

        self.section("3. down + up -d: данные в volume сохраняются")
        self.compose("down")
        self.compose("up", "-d", "--wait", "--wait-timeout", str(WAIT_TIMEOUT))
        self.expect_count("GET", "/", n)

        self.section("4. Остановка Redis")
        app_id = self.compose("ps", "-q", "app", show=False)
        self.compose("stop", "redis")
        self.expect_status("GET", "/healthz", 200)
        self.expect_status("GET", "/readyz", 503)
        self.expect_status("POST", "/increment", 503)
        self.expect_status("GET", "/", 503)

        self.section("5. Запуск Redis без перезапуска приложения")
        self.compose("start", "redis")
        self.wait_ready()
        if self.compose("ps", "-q", "app", show=False) != app_id:
            raise CheckFailed("контейнер app был пересоздан")
        print(f"  контейнер app тот же: {app_id[:12]}")
        self.expect_count("GET", "/", n)
        self.expect_count("POST", "/increment", n + 1)

        self.section("6. Состояние сервисов и данные Redis")
        self.compose("ps", "--format", "table {{.Service}}\t{{.Status}}")
        self.compose("exec", "-T", "redis", "redis-cli", "CONFIG", "GET", "appendonly")
        self.compose("exec", "-T", "redis", "ls", "-la", "/data", "/data/appendonlydir")

    def cleanup(self):
        print(f"\n=== Очистка: удаляю проект {self.project} вместе с volume ===", flush=True)
        try:
            self.compose("down", "-v", "--remove-orphans")
        except CheckFailed as e:
            print(f"ВНИМАНИЕ: очистка не удалась: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--requests", "-n", type=int, default=5, help="сколько раз вызвать POST /increment")
    args = parser.parse_args()

    checker = Checker(args.requests)
    try:
        checker.run()
    except CheckFailed as e:
        print(f"\nОШИБКА на этапе «{checker.stage}»: {e}", file=sys.stderr, flush=True)
        return 1
    except KeyboardInterrupt:
        print(f"\nПрервано на этапе «{checker.stage}»", file=sys.stderr)
        return 130
    finally:
        checker.cleanup()
    print("\nВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Отчёт о проверках

Окружение: macOS (Apple Silicon), Docker через Colima.

```
Docker Engine 29.5.2
Docker Compose version 5.8.0
```

Все выводы ниже — реальные, скопированы из терминала.

## Уровень 4 — один контейнер

Образ собран, порт опубликован (`8080 -> 8000`), приветствие передано через `-e GREETING`.
Счётчик растёт только на `POST`, `GET` его не меняет. Процесс работает от UID 10001,
`HEALTHCHECK` переводит контейнер в `healthy`. Благодаря `STOPSIGNAL SIGINT` контейнер
останавливается мгновенно, без 10-секундного ожидания SIGKILL.

```
$ docker build -q -t counter-app .
sha256:25b631467b02eb07467a86dd8e898e1e2495fc804e22417c72073abb6b89e0ef

$ docker run -d --name counter -p 8080:8000 -e GREETING="Привет из Docker!" counter-app
9f33c65540bee17946190242ce071fca632410aae95adf6a45a66888d5f9f427

$ curl -sS http://127.0.0.1:8080/
{"greeting": "Привет из Docker!", "count": 0, "hostname": "9f33c65540be", "storage": "sqlite"}

$ curl -sS -X POST http://127.0.0.1:8080/increment
{"greeting": "Привет из Docker!", "count": 1, "hostname": "9f33c65540be", "storage": "sqlite"}

$ curl -sS -X POST http://127.0.0.1:8080/increment
{"greeting": "Привет из Docker!", "count": 2, "hostname": "9f33c65540be", "storage": "sqlite"}

$ curl -sS -X POST http://127.0.0.1:8080/increment
{"greeting": "Привет из Docker!", "count": 3, "hostname": "9f33c65540be", "storage": "sqlite"}

$ curl -sS http://127.0.0.1:8080/
{"greeting": "Привет из Docker!", "count": 3, "hostname": "9f33c65540be", "storage": "sqlite"}

$ curl -sS http://127.0.0.1:8080/readyz
{"status": "ready", "storage": "sqlite"}

$ docker exec counter id
uid=10001(app) gid=10001(app) groups=10001(app)

$ docker ps --filter name=counter --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
NAMES     PORTS                                         STATUS
counter   0.0.0.0:8080->8000/tcp, [::]:8080->8000/tcp   Up 9 seconds (healthy)

$ docker logs counter
2026-11-22 16:15:48,539 listening port=8000 storage=sqlite
2026-11-22 16:15:50,464 http 172.17.0.1 "GET / HTTP/1.1" 200 -
2026-11-22 16:15:50,480 http 172.17.0.1 "POST /increment HTTP/1.1" 200 -
2026-11-22 16:15:50,493 http 172.17.0.1 "POST /increment HTTP/1.1" 200 -
2026-11-22 16:15:50,505 http 172.17.0.1 "POST /increment HTTP/1.1" 200 -
2026-11-22 16:15:50,515 http 172.17.0.1 "GET / HTTP/1.1" 200 -
2026-11-22 16:15:50,525 http 172.17.0.1 "GET /readyz HTTP/1.1" 200 -
2026-11-22 16:15:53,564 http 127.0.0.1 "GET /healthz HTTP/1.1" 200 -

$ docker stop counter
counter

# остановка заняла 0.1 с

$ docker rm counter
counter
```

## Уровень 6 — Compose и SQLite в volume

Приветствие и порт на компьютере берутся из `.env` (создан из `.env.example` с
`APP_PORT=9090`). После `down` контейнер удалён, после `up -d` создан новый
(другой `hostname`), а счётчик остался **5**: файл SQLite лежит в именованном volume
`hw3-sqlite_counter-data`. `down -v` в конце удаляет volume.

```
$ cat .env
GREETING=Привет из Compose!
APP_PORT=9090

$ docker compose -f compose.sqlite.yaml up -d --build --quiet-build
 Image counter-app:latest Building 
 Image counter-app:latest Built 
 Network hw3-sqlite_default Creating 
 Volume hw3-sqlite_counter-data Creating 
 Volume hw3-sqlite_counter-data Created 
 Network hw3-sqlite_default Created 
 Container hw3-sqlite-app-1 Creating 
 Container hw3-sqlite-app-1 Created 
 Container hw3-sqlite-app-1 Starting 
 Container hw3-sqlite-app-1 Started 

$ docker compose -f compose.sqlite.yaml ps
NAME               IMAGE                COMMAND           SERVICE   CREATED         STATUS                            PORTS
hw3-sqlite-app-1   counter-app:latest   "python app.py"   app       3 seconds ago   Up 3 seconds (health: starting)   0.0.0.0:9090->8000/tcp, [::]:9090->8000/tcp

$ curl -sS http://127.0.0.1:9090/
{"greeting": "Привет из Compose!", "count": 0, "hostname": "54b8eccdc6b0", "storage": "sqlite"}
$ curl -sS -X POST http://127.0.0.1:9090/increment
{"greeting": "Привет из Compose!", "count": 1, "hostname": "54b8eccdc6b0", "storage": "sqlite"}
$ curl -sS -X POST http://127.0.0.1:9090/increment
{"greeting": "Привет из Compose!", "count": 2, "hostname": "54b8eccdc6b0", "storage": "sqlite"}
$ curl -sS -X POST http://127.0.0.1:9090/increment
{"greeting": "Привет из Compose!", "count": 3, "hostname": "54b8eccdc6b0", "storage": "sqlite"}
$ curl -sS -X POST http://127.0.0.1:9090/increment
{"greeting": "Привет из Compose!", "count": 4, "hostname": "54b8eccdc6b0", "storage": "sqlite"}
$ curl -sS -X POST http://127.0.0.1:9090/increment
{"greeting": "Привет из Compose!", "count": 5, "hostname": "54b8eccdc6b0", "storage": "sqlite"}
$ docker volume ls --filter name=hw3-sqlite
DRIVER    VOLUME NAME
local     hw3-sqlite_counter-data

$ docker compose -f compose.sqlite.yaml down
 Container hw3-sqlite-app-1 Stopping 
 Container hw3-sqlite-app-1 Stopped 
 Container hw3-sqlite-app-1 Removing 
 Container hw3-sqlite-app-1 Removed 
 Network hw3-sqlite_default Removing 
 Network hw3-sqlite_default Removed 

$ docker compose -f compose.sqlite.yaml ps -a
NAME      IMAGE     COMMAND   SERVICE   CREATED   STATUS    PORTS

$ docker compose -f compose.sqlite.yaml up -d
 Network hw3-sqlite_default Creating 
 Network hw3-sqlite_default Created 
 Container hw3-sqlite-app-1 Creating 
 Container hw3-sqlite-app-1 Created 
 Container hw3-sqlite-app-1 Starting 
 Container hw3-sqlite-app-1 Started 

$ curl -sS http://127.0.0.1:9090/
{"greeting": "Привет из Compose!", "count": 5, "hostname": "62b48115a78e", "storage": "sqlite"}
$ docker compose -f compose.sqlite.yaml down -v
 Container hw3-sqlite-app-1 Stopping 
 Container hw3-sqlite-app-1 Stopped 
 Container hw3-sqlite-app-1 Removing 
 Container hw3-sqlite-app-1 Removed 
 Volume hw3-sqlite_counter-data Removing 
 Network hw3-sqlite_default Removing 
 Volume hw3-sqlite_counter-data Removed 
 Network hw3-sqlite_default Removed
```

## Уровень 8 — отдельное хранилище Redis

Проверка автоматизирована скриптом [scripts/check.py](scripts/check.py) (Python 3,
только стандартная библиотека). Он запускает **отдельный** Compose-проект со случайным
именем `hw3check-xxxxxx` и свободным портом на основе того же `compose.yaml`, печатает
каждую команду и ответ, а в конце удаляет только свои ресурсы через `down -v`.
У HTTP-запросов (5 с) и ожидания готовности (120 с) есть тайм-ауты; при ошибке
скрипт пишет этап и возвращает код 1.

```sh
python3 scripts/check.py -n 7
```

Что подтверждает прогон:

| Требование | Результат |
| --- | --- |
| `STORAGE=redis`, `REDIS_URL=redis://redis:6379/0` | `"storage": "redis"` в ответах |
| Наружу опубликован только порт приложения | у `redis` в `ps` только `6379/tcp`, без `0.0.0.0` |
| Healthcheck обоих сервисов | оба `(healthy)`; `--wait` дожидается этого статуса |
| Volume на `/data`, запись на диск | после `down` + `up -d` `GET /` вернул тот же **N = 7**; `appendonly yes`, в `/data/appendonlydir` лежит AOF |
| `stop redis` | `/healthz` — **200**, `/readyz`, `POST /increment`, `GET /` — **503** |
| `start redis` без перезапуска приложения | ID контейнера `app` не изменился, `GET /` — **7**, следующий `POST` — **8** |

### Прогон 1 (`-n 7`)

```
Проект: hw3check-0662d4, порт приложения: 49310, N = 7

=== 1. Запуск с пустым хранилищем ===
$ docker compose up -d --build --quiet-build --quiet-pull --wait --wait-timeout 120
Image counter-app:latest Building 
 Image counter-app:latest Built 
 Volume hw3check-0662d4_redis-data Creating 
 Network hw3check-0662d4_default Creating 
 Volume hw3check-0662d4_redis-data Created 
 Network hw3check-0662d4_default Created 
 Container hw3check-0662d4-redis-1 Creating 
 Container hw3check-0662d4-redis-1 Created 
 Container hw3check-0662d4-app-1 Creating 
 Container hw3check-0662d4-app-1 Created 
 Container hw3check-0662d4-redis-1 Starting 
 Container hw3check-0662d4-redis-1 Started 
 Container hw3check-0662d4-redis-1 Waiting 
 Container hw3check-0662d4-redis-1 Healthy 
 Container hw3check-0662d4-app-1 Starting 
 Container hw3check-0662d4-app-1 Started 
 Container hw3check-0662d4-app-1 Waiting 
 Container hw3check-0662d4-redis-1 Waiting 
 Container hw3check-0662d4-redis-1 Healthy 
 Container hw3check-0662d4-app-1 Healthy
$ docker compose ps --format table {{.Service}}	{{.Status}}	{{.Ports}}
SERVICE   STATUS                    PORTS
app       Up 5 seconds (healthy)    0.0.0.0:49310->8000/tcp, [::]:49310->8000/tcp
redis     Up 11 seconds (healthy)   6379/tcp
  порт Redis на компьютер не опубликован — ок
$ curl -X GET http://127.0.0.1:49310/
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 0, "hostname": "64aeafbd5586", "storage": "redis"}

=== 2. 7 запросов POST /increment ===
$ curl -X POST http://127.0.0.1:49310/increment
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 1, "hostname": "64aeafbd5586", "storage": "redis"}
$ curl -X POST http://127.0.0.1:49310/increment
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 2, "hostname": "64aeafbd5586", "storage": "redis"}
$ curl -X POST http://127.0.0.1:49310/increment
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 3, "hostname": "64aeafbd5586", "storage": "redis"}
$ curl -X POST http://127.0.0.1:49310/increment
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 4, "hostname": "64aeafbd5586", "storage": "redis"}
$ curl -X POST http://127.0.0.1:49310/increment
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 5, "hostname": "64aeafbd5586", "storage": "redis"}
$ curl -X POST http://127.0.0.1:49310/increment
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 6, "hostname": "64aeafbd5586", "storage": "redis"}
$ curl -X POST http://127.0.0.1:49310/increment
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 7, "hostname": "64aeafbd5586", "storage": "redis"}
$ curl -X GET http://127.0.0.1:49310/
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 7, "hostname": "64aeafbd5586", "storage": "redis"}

=== 3. down + up -d: данные в volume сохраняются ===
$ docker compose down
Container hw3check-0662d4-app-1 Stopping 
 Container hw3check-0662d4-app-1 Stopped 
 Container hw3check-0662d4-app-1 Removing 
 Container hw3check-0662d4-app-1 Removed 
 Container hw3check-0662d4-redis-1 Stopping 
 Container hw3check-0662d4-redis-1 Stopped 
 Container hw3check-0662d4-redis-1 Removing 
 Container hw3check-0662d4-redis-1 Removed 
 Network hw3check-0662d4_default Removing 
 Network hw3check-0662d4_default Removed
$ docker compose up -d --wait --wait-timeout 120
Network hw3check-0662d4_default Creating 
 Network hw3check-0662d4_default Created 
 Container hw3check-0662d4-redis-1 Creating 
 Container hw3check-0662d4-redis-1 Created 
 Container hw3check-0662d4-app-1 Creating 
 Container hw3check-0662d4-app-1 Created 
 Container hw3check-0662d4-redis-1 Starting 
 Container hw3check-0662d4-redis-1 Started 
 Container hw3check-0662d4-redis-1 Waiting 
 Container hw3check-0662d4-redis-1 Healthy 
 Container hw3check-0662d4-app-1 Starting 
 Container hw3check-0662d4-app-1 Started 
 Container hw3check-0662d4-app-1 Waiting 
 Container hw3check-0662d4-redis-1 Waiting 
 Container hw3check-0662d4-redis-1 Healthy 
 Container hw3check-0662d4-app-1 Healthy
$ curl -X GET http://127.0.0.1:49310/
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 7, "hostname": "851550e90614", "storage": "redis"}

=== 4. Остановка Redis ===
$ docker compose stop redis
Container hw3check-0662d4-redis-1 Stopping 
 Container hw3check-0662d4-redis-1 Stopped
$ curl -X GET http://127.0.0.1:49310/healthz
  -> HTTP 200 {"status": "alive"}
$ curl -X GET http://127.0.0.1:49310/readyz
  -> HTTP 503 {"error": "storage_unavailable"}
$ curl -X POST http://127.0.0.1:49310/increment
  -> HTTP 503 {"error": "storage_unavailable"}
$ curl -X GET http://127.0.0.1:49310/
  -> HTTP 503 {"error": "storage_unavailable"}

=== 5. Запуск Redis без перезапуска приложения ===
$ docker compose start redis
Container hw3check-0662d4-redis-1 Starting 
 Container hw3check-0662d4-redis-1 Started
  /readyz -> 200 через 0.0 с
  контейнер app тот же: 851550e90614
$ curl -X GET http://127.0.0.1:49310/
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 7, "hostname": "851550e90614", "storage": "redis"}
$ curl -X POST http://127.0.0.1:49310/increment
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 8, "hostname": "851550e90614", "storage": "redis"}

=== 6. Состояние сервисов и данные Redis ===
$ docker compose ps --format table {{.Service}}	{{.Status}}
SERVICE   STATUS
app       Up 6 seconds (healthy)
redis     Up Less than a second (health: starting)
$ docker compose exec -T redis redis-cli CONFIG GET appendonly
appendonly
yes
$ docker compose exec -T redis ls -la /data /data/appendonlydir
/data:
total 16
drwxr-xr-x    3 redis    redis         4096 Nov 22 16:15 .
drwxr-xr-x    1 root     root          4096 Nov 22 16:14 ..
drwx------    2 redis    redis         4096 Nov 22 16:14 appendonlydir
-rw-------    1 redis    redis          115 Nov 22 16:15 dump.rdb

/data/appendonlydir:
total 20
drwx------    2 redis    redis         4096 Nov 22 16:14 .
drwxr-xr-x    3 redis    redis         4096 Nov 22 16:15 ..
-rw-------    1 redis    redis           89 Nov 22 16:14 appendonly.aof.1.base.rdb
-rw-------    1 redis    redis          422 Nov 22 16:15 appendonly.aof.1.incr.aof
-rw-------    1 redis    redis           88 Nov 22 16:14 appendonly.aof.manifest

=== Очистка: удаляю проект hw3check-0662d4 вместе с volume ===
$ docker compose down -v --remove-orphans
Container hw3check-0662d4-app-1 Stopping 
 Container hw3check-0662d4-app-1 Stopped 
 Container hw3check-0662d4-app-1 Removing 
 Container hw3check-0662d4-app-1 Removed 
 Container hw3check-0662d4-redis-1 Stopping 
 Container hw3check-0662d4-redis-1 Stopped 
 Container hw3check-0662d4-redis-1 Removing 
 Container hw3check-0662d4-redis-1 Removed 
 Volume hw3check-0662d4_redis-data Removing 
 Network hw3check-0662d4_default Removing 
 Volume hw3check-0662d4_redis-data Removed 
 Network hw3check-0662d4_default Removed

ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ
```

### Прогон 2 (`-n 5`)

Второй прогон подряд, сокращённый вывод — итог:

```
Проект: hw3check-049404, порт приложения: 49348, N = 5
=== 1. Запуск с пустым хранилищем ===
  порт Redis на компьютер не опубликован — ок
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 0, "hostname": "afc326920e48", "storage": "redis"}
=== 2. 5 запросов POST /increment ===
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 1, "hostname": "afc326920e48", "storage": "redis"}
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 2, "hostname": "afc326920e48", "storage": "redis"}
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 3, "hostname": "afc326920e48", "storage": "redis"}
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 4, "hostname": "afc326920e48", "storage": "redis"}
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 5, "hostname": "afc326920e48", "storage": "redis"}
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 5, "hostname": "afc326920e48", "storage": "redis"}
=== 3. down + up -d: данные в volume сохраняются ===
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 5, "hostname": "cfe3ba75d5c7", "storage": "redis"}
=== 4. Остановка Redis ===
  -> HTTP 200 {"status": "alive"}
  -> HTTP 503 {"error": "storage_unavailable"}
  -> HTTP 503 {"error": "storage_unavailable"}
  -> HTTP 503 {"error": "storage_unavailable"}
=== 5. Запуск Redis без перезапуска приложения ===
  /readyz -> 200 через 0.0 с
  контейнер app тот же: cfe3ba75d5c7
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 5, "hostname": "cfe3ba75d5c7", "storage": "redis"}
  -> HTTP 200 {"greeting": "Hello from check.py", "count": 6, "hostname": "cfe3ba75d5c7", "storage": "redis"}
=== 6. Состояние сервисов и данные Redis ===
=== Очистка: удаляю проект hw3check-049404 вместе с volume ===
ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ
```

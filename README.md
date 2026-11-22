# ДЗ 3 — счётчик в Docker

Сделано на 8 баллов. Код приложения в папке `app/` не менял.
Условие задания — в [TASK.md](TASK.md), вывод всех проверок — в [REPORT.md](REPORT.md).

## Что где лежит

- `Dockerfile` — как собирается образ приложения
- `.dockerignore` — чтобы в образ не попадало лишнее
- `compose.yaml` — приложение + Redis (это уровень 8)
- `compose.sqlite.yaml` — только приложение с SQLite (это уровень 6)
- `.env.example` — пример настроек
- `scripts/check.py` — скрипт, который сам проверяет уровень 8

Нужен Docker с Compose и curl.

## Уровень 4: один контейнер

```sh
docker build -t counter-app .
docker run -d --name counter -p 8080:8000 -e GREETING="Привет!" counter-app
curl http://127.0.0.1:8080/
curl -X POST http://127.0.0.1:8080/increment
docker logs counter
docker rm -f counter
```

## Настройки

Копируем пример:

```sh
cp .env.example .env
```

В `.env` две настройки:

- `GREETING` — приветствие в ответе
- `APP_PORT` — порт на компе, по которому открывается приложение (по умолчанию 8080)

Если `.env` нет, берутся значения по умолчанию.

## Уровень 6: Compose и SQLite

```sh
docker compose -f compose.sqlite.yaml up -d --build
curl -X POST http://127.0.0.1:8080/increment
docker compose -f compose.sqlite.yaml down
docker compose -f compose.sqlite.yaml up -d
curl http://127.0.0.1:8080/
```

Счётчик после `down` и `up` остаётся тем же, потому что база лежит в volume,
а `down` volume не удаляет. Удалить всё вместе с данными: `down -v`.

## Уровень 8: приложение + Redis

```sh
docker compose up -d --build --wait
curl http://127.0.0.1:8080/
curl -X POST http://127.0.0.1:8080/increment
```

Как это устроено:

- Приложение ходит в Redis по адресу `redis://redis:6379/0`. `redis` — это имя сервиса,
  Compose сам знает, какой у него IP.
- Порт Redis наружу не открыт, открыт только порт приложения.
- Данные Redis лежат в volume `redis-data` (папка `/data`). Включён `appendonly`,
  поэтому Redis пишет каждое изменение на диск и после перезапуска ничего не теряет.
- У обоих сервисов есть healthcheck. Redis проверяется через `redis-cli ping`,
  приложение — через `/readyz`. Приложение стартует только когда Redis уже готов.

Если остановить Redis (`docker compose stop redis`), приложение не падает:
`/healthz` отвечает 200, а `/readyz` и `POST /increment` — 503.
После `docker compose start redis` всё снова работает само, перезапускать приложение не надо.

Остановить и сохранить данные: `docker compose down`.
Остановить и удалить данные: `docker compose down -v`.

## Автопроверка

```sh
python3 scripts/check.py
```

Скрипт поднимает отдельную тестовую копию (не трогает основную), прогоняет все проверки
уровня 8 и потом удаляет за собой всё, что создал. Если что-то не так — пишет, на каком шаге,
и завершается с ошибкой. Количество POST-запросов можно поменять: `python3 scripts/check.py -n 10`.

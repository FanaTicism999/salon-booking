import os
import json
import base64
import aiohttp

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # например, "FanaTicism999/salon-booking"
SITE_JSON_PATH = "landing/site.json"

API_URL = "https://api.github.com"


def _headers() -> dict:
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "salon-booking-bot",
    }


async def get_site_json() -> tuple[dict, str]:
    """
    Читает landing/site.json из GitHub.
    Возвращает (данные, sha) — sha нужен для последующего обновления.
    """
    url = f"{API_URL}/repos/{GITHUB_REPO}/contents/{SITE_JSON_PATH}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=_headers()) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"GitHub API error {resp.status}: {text}")

            data = await resp.json()
            content_b64 = data["content"]
            content_bytes = base64.b64decode(content_b64)
            content_str = content_bytes.decode("utf-8")
            site_data = json.loads(content_str)
            sha = data["sha"]

            return site_data, sha


async def update_site_json(new_data: dict) -> None:
    """
    Обновляет landing/site.json в GitHub.
    Автоматически получает актуальный sha перед коммитом.
    """
    # Сначала получаем актуальный sha
    _, sha = await get_site_json()

    url = f"{API_URL}/repos/{GITHUB_REPO}/contents/{SITE_JSON_PATH}"

    # Кодируем JSON обратно в base64
    new_content = json.dumps(new_data, ensure_ascii=False, indent=2)
    new_content_b64 = base64.b64encode(new_content.encode("utf-8")).decode("ascii")

    payload = {
        "message": "Обновление site.json через Telegram-бота",
        "content": new_content_b64,
        "sha": sha,
    }

    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=_headers(), json=payload) as resp:
            if resp.status not in (200, 201):
                text = await resp.text()
                raise Exception(f"GitHub API error {resp.status}: {text}")


async def update_field(field_name: str, new_value: str) -> dict:
    """
    Обновляет одно поле в site.json.
    Возвращает обновлённые данные.
    """
    data, _ = await get_site_json()
    data[field_name] = new_value
    await update_site_json(data)
    return data

async def upload_file(file_path: str, content_bytes: bytes, commit_message: str) -> str:
    """
    Загружает файл в GitHub репозиторий.
    file_path — путь внутри репозитория (например, 'landing/images/hero.jpg')
    content_bytes — содержимое файла в байтах
    commit_message — сообщение коммита

    Возвращает URL созданного файла (raw).
    """
    url = f"{API_URL}/repos/{GITHUB_REPO}/contents/{file_path}"

    # Проверяем, существует ли уже файл (нужно для sha при обновлении)
    sha = None
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=_headers()) as resp:
            if resp.status == 200:
                data = await resp.json()
                sha = data.get("sha")

    # Кодируем содержимое в base64
    content_b64 = base64.b64encode(content_bytes).decode("ascii")

    payload = {
        "message": commit_message,
        "content": content_b64,
    }
    if sha:
        payload["sha"] = sha  # обязательно при обновлении существующего файла

    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=_headers(), json=payload) as resp:
            if resp.status not in (200, 201):
                text = await resp.text()
                raise Exception(f"GitHub API error {resp.status}: {text}")

    # Возвращаем raw URL для этого файла
    return f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{file_path}"
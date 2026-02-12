#!/usr/bin/env python3
"""
Тест NotebookLM Podcast API.
Требует: pip install google-auth google-auth-oauthlib google-auth-httplib2 requests
Или: gcloud auth application-default login
"""
import json
import sys
from pathlib import Path

# Добавляем корень проекта
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROJECT_ID = ""  # <-- Вставь свой Project ID сюда


def get_access_token():
    """Получить токен: ADC или gcloud auth print-access-token."""
    # 1. Пробуем gcloud (если пользователь залогинен)
    try:
        import subprocess
        out = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True, text=True, timeout=10
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    # 2. Application Default Credentials
    try:
        import google.auth
        from google.auth.transport.requests import Request
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(Request())
        return credentials.token
    except Exception as e:
        print(f"Ошибка авторизации: {e}")
        print("Запусти в терминале: gcloud auth application-default login")
        print("(Откроется браузер для входа в Google)")
        return None


def test_podcast_api(project_id: str) -> bool:
    """Отправить тестовый запрос к Podcast API."""
    token = get_access_token()
    if not token:
        return False

    url = f"https://discoveryengine.googleapis.com/v1/projects/{project_id}/locations/global/podcasts"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "podcastConfig": {
            "focus": "Краткий обзор главной темы.",
            "length": "SHORT",
            "languageCode": "ru",
        },
        "contexts": [
            {
                "text": "Искусственный интеллект меняет способы создания контента. "
                "Подкасты теперь можно генерировать из текста автоматически. "
                "Это открывает новые возможности для радио и медиа.",
            }
        ],
        "title": "Тест NAVO RADIO",
        "description": "Пробный подкаст для проверки API.",
    }

    print("Отправляю запрос...")
    try:
        import requests
    except ImportError:
        print("Установи: pip install requests google-auth")
        return False
    r = requests.post(url, headers=headers, json=payload, timeout=30)

    print(f"Статус: {r.status_code}")
    if r.text:
        try:
            data = r.json()
            print("Ответ:", json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            print("Текст:", r.text[:500])

    if r.status_code == 200:
        data = r.json()
        name = data.get("name", "")
        op_name = name.split("/")[-1] if "/" in name else name
        dl_url = f"https://discoveryengine.googleapis.com/v1/projects/{project_id}/locations/global/operations/{op_name}:download?alt=media"
        print(f"\n[OK] Подкаст создаётся. Operation: {name}")
        print("Генерация занимает несколько минут. Для скачивания:")
        print(f'  curl -H "Authorization: Bearer $(gcloud auth print-access-token)" "{dl_url}" -L -o podcast.mp3')
        return True
    elif r.status_code == 403:
        print("\n[!] 403 — доступ к Podcast API не включён или нет роли.")
        print("Обратись к Google Cloud Sales для доступа.")
        return False
    elif r.status_code == 404:
        print("\n[!] 404 — API не найден. Проверь Project ID и Discovery Engine API.")
        return False
    else:
        return False


if __name__ == "__main__":
    pid = PROJECT_ID or (len(sys.argv) > 1 and sys.argv[1])
    if not pid:
        print("Укажи Project ID:")
        print("  python scripts/test_podcast_api.py YOUR_PROJECT_ID")
        print("Или вставь в переменную PROJECT_ID в скрипте.")
        sys.exit(1)
    ok = test_podcast_api(pid)
    sys.exit(0 if ok else 1)

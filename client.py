import requests

SERVER_URL = "https://occupancy-dismay-gleaming.ngrok-free.dev/api/check-in"


def check_in(user_id: str, username: str, action: str, latitude: float = 0.0, longitude: float = 0.0, photo_path: str | None = None):
    """Отправляет запрос на сервер трекера рабочего времени."""
    data = {
        "user_id": user_id,
        "username": username,
        "action": action,
        "latitude": latitude,
        "longitude": longitude,
    }

    files = None
    if photo_path:
        files = {"photo": open(photo_path, "rb")}

    try:
        response = requests.post(SERVER_URL, data=data, files=files)
        response.raise_for_status()
        return response.json()
    finally:
        if files:
            files["photo"].close()


if __name__ == "__main__":
    result = check_in(
        user_id="123456",
        username="Test User",
        action="📥 Приход",
        latitude=41.328337,
        longitude=69.334100,
        photo_path=None,
    )
    print(result)

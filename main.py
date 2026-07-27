from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
import os
import math
from datetime import datetime

app = FastAPI()
# app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/static", StaticFiles(directory="static"), name="static")

DB_NAME = "database.db"

# === ТВОИ КООРДИНАТЫ ОФИСА ===
OFFICE_LAT = 41.328337
OFFICE_LON = 69.334100
MAX_DISTANCE_METERS = 100  # Допустимый радиус в метрах

def calculate_distance(lat1, lon1, lat2, lon2):
    """Считает расстояние между двумя точками на Земле в метрах"""
    R = 6371000  # Радиус земли в метрах
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        username TEXT,
        action TEXT,
        timestamp TEXT,
        photo_path TEXT,
        latitude REAL,
        longitude REAL,
        break_duration TEXT DEFAULT '-',
        lunch_duration TEXT DEFAULT '-'
    )
    """)
    conn.commit()
    conn.close()

init_db()

@app.post("/api/check-in")
async def check_in(
    user_id: str = Form(...),
    username: str = Form(...),
    action: str = Form(...),
    latitude: float = Form(0.0),
    longitude: float = Form(0.0),
    photo: UploadFile = File(None)
):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_path = "-"

    # Проверка геозоны для Прихода и Ухода
    if action in ["📥 Приход", "📤 Уход"]:
        if latitude != 0.0 and longitude != 0.0:
            distance = calculate_distance(latitude, longitude, OFFICE_LAT, OFFICE_LON)
            if distance > MAX_DISTANCE_METERS:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": f"Вы находитесь слишком далеко от офиса! Расстояние: {int(distance)} м. (допустимо до {MAX_DISTANCE_METERS} м.)"
                    }
                )
        else:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Геолокация не передана!"}
            )

    # === ПРОВЕРКА ЛОГИКИ СТАТУСОВ ===
    conn_check = sqlite3.connect(DB_NAME)
    cursor_check = conn_check.cursor()
    cursor_check.execute("""
        SELECT action FROM records 
        WHERE user_id = ? 
        ORDER BY id DESC LIMIT 1
    """, (user_id,))
    last_record = cursor_check.fetchone()
    conn_check.close()

    last_action = last_record[0] if last_record else None

    if action == "📥 Приход" and last_action in ["📥 Приход", "☕ Перерыв", "🍽 Обед"]:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Вы уже отметили приход! Сначала нужно сделать уход."})
    
    if action == "📤 Уход" and (not last_action or last_action == "📤 Уход"):
        return JSONResponse(status_code=400, content={"status": "error", "message": "Вы еще не отметили приход в офис!"})

    if photo:
        os.makedirs("static", exist_ok=True)
        file_path = os.path.join("static", f"{user_id}_{int(datetime.now().timestamp())}.jpg")
        with open(file_path, "wb") as buffer:
            buffer.write(await photo.read())

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    break_dur = "-"
    lunch_dur = "-"
    duration_message = ""

    # Расчет времени перерыва или обеда при возвращении
    if action in ["☕ Вернуться с перерыва", "🍽 Вернуться с обеда"]:
        target_start = "☕ Перерыв" if "перерыв" in action else "🍽 Обед"
        cursor.execute("""
            SELECT timestamp FROM records 
            WHERE user_id = ? AND action = ? 
            ORDER BY id DESC LIMIT 1
        """, (user_id, target_start))
        last_start = cursor.fetchone()

        if last_start:
            start_time = datetime.strptime(last_start[0], "%Y-%m-%d %H:%M:%S")
            current_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            diff_minutes = int((current_time - start_time).total_seconds() / 60)

            duration_str = f"{diff_minutes} мин."
            if "перерыв" in action:
                break_dur = duration_str
                duration_message = f"⏱ Вы были на перерыве: {duration_str}"
            else:
                lunch_dur = duration_str
                duration_message = f"🍽 Вы были на обеде: {duration_str}"

    cursor.execute("""
        INSERT INTO records (user_id, username, action, timestamp, photo_path, latitude, longitude, break_duration, lunch_duration)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, username, action, timestamp, file_path, latitude, longitude, break_dur, lunch_dur))

    conn.commit()
    conn.close()

    new_status = action
    if action in ["☕ Вернуться с перерыва", "🍽 Вернуться с обеда"]:
        new_status = "📥 Приход"

    return JSONResponse(content={
        "status": "success",
        "message": "Запись сохранена",
        "duration_message": duration_message,
        "current_status": new_status
    })

@app.get("/manager/dashboard", response_class=HTMLResponse)
async def manager_dashboard():
    if not os.path.exists("index.html"):
        return "<h1>Файл index.html не найден в корне проекта!</h1>"

    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    table_rows = ""
    for row in rows:
        photo_link = f"<a href='/{row['photo_path']}' target='_blank'>Фото</a>" if row['photo_path'] != "-" else "-"
        lat = row['latitude']
        lon = row['longitude']
        coords = f"{lat}, {lon}" if lat != 0.0 else "-"
        
        table_rows += f"""
        <tr>
            <td>{row['id']}</td>
            <td>{row['username']} ({row['user_id']})</td>
            <td>{row['action']}</td>
            <td>{row['timestamp']}</td>
            <td>{row['break_duration']}</td>
            <td>{row['lunch_duration']}</td>
            <td>{photo_link}</td>
            <td>{coords}</td>
        </tr>
        """

    html_content = html_content.replace("<!-- TABLE ROWS PLACEHOLDER -->", table_rows)
    return html_content

if __name__ == "__main__":
    import uvicorn
    import threading
    import os

    def run_bot():
        try:
            import bot
            print("Telegram бот запущен параллельно с сервером!")
        except Exception as e:
            print(f"Ошибка запуска бота: {e}")

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
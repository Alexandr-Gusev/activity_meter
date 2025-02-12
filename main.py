from threading import Thread, Condition
import mouse
import keyboard
import time
import argparse
from datetime import date, timedelta, datetime
import asyncio
from aiohttp import web
import win32gui
import win32con
import win32api
from https_utils import create_ssl_context
import json
import cv2
import os
import base64

data = {
    "today": str(date.today()),
    "mode": "norm",
    "duration": 0
}

prev_now = datetime.now()
condition = Condition()

MAIN_INTERVAL = 60
WINDOW_INTERVAL = 60
APP_WD = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_WD, "data.json")
SSL_CRT = os.path.join(APP_WD, "localhost.crt")
SSL_KEY = os.path.join(APP_WD, "localhost.key")
SPLASH_FILE = os.path.join(APP_WD, "splash.jpg")

parser = argparse.ArgumentParser()
parser.add_argument("--dt", type=int, default=180)
parser.add_argument("--t-min", default="09:00")
parser.add_argument("--t-max", default="21:00")
parser.add_argument("--duration-max", default="4:00:00")
parser.add_argument("--addr", default="0.0.0.0")
parser.add_argument("--port", type=int, default="8088")
parser.add_argument("--title", default="That's enough for today")

args = parser.parse_args()

h, m, s = args.duration_max.split(":")
duration_max = 3600 * int(h) + 60 * int(m) + int(s)


def write_data():
    try:
        with open(DATA_FILE, "wb") as f:
            f.write(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=4).encode("utf-8"))
    except Exception as e:
        print(e)


def get_enabled(now):
    if data["mode"] != "norm":
        return data["mode"] == "on", True
    t = now.strftime("%H:%M")
    return args.t_min <= t <= args.t_max and data["duration"] < duration_max, False


def update_duration():
    global prev_now
    now = datetime.now()
    enabled, forced = get_enabled(now)
    if not enabled or forced:
        return
    dt = (now - prev_now).total_seconds()
    prev_now = now
    if dt < args.dt:
        data["duration"] += dt


def main_target():
    while True:
        today = str(date.today())
        if today != data["today"]:
            data["today"] = today
            data["duration"] = 0
            with condition:
                condition.notify()

        write_data()
        time.sleep(MAIN_INTERVAL)


def window_target():
    while True:
        while not get_enabled(datetime.now())[0]:
            w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            image = cv2.resize(cv2.imread(SPLASH_FILE), (w, h))
            cv2.imshow(args.title, image)
            hwnd = win32gui.FindWindow(None, args.title)
            win32gui.SetWindowLong(
                hwnd,
                win32con.GWL_STYLE,
                win32con.WS_VISIBLE | win32con.WS_POPUP
            )
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, w, h, 0)

            while not get_enabled(datetime.now())[0] and cv2.getWindowProperty(args.title, cv2.WND_PROP_VISIBLE):
                cv2.waitKey(20)
            cv2.destroyAllWindows()

        with condition:
            condition.wait(WINDOW_INTERVAL)


def mh(e):
    update_duration()


def kh(e):
    update_duration()


async def index(request):
    on_class = "active" if data["mode"] == "on" else "normal"
    off_class = "active" if data["mode"] == "off" else "normal"
    norm_class = "active" if data["mode"] == "norm" else "normal"
    return web.Response(
        body="""<html>
<head>
	<meta charset="utf-8">
    <style type="text/css">
        body {
            background-color: rgb(24, 24, 39);
            color: white;
        }
        button {
            width: 90px;
            height: 35px;
            background-color: rgba(24, 24, 39, 0.700);
            color: white;
            font-weight: 300;
            border-radius: 5px;
            cursor: pointer;
        }
        .container {
            display: flex;
            gap: 8px;
            padding: 8px;
            align-items: center;
        }
        .active {
            border: 1px solid #1E90FF;
        }
        .normal {
            border: 1px solid rgba(110, 110, 110, 0.658);
        }
    </style>
    <script type="text/javascript">
        const setMode = mode => {
            const xhr = new XMLHttpRequest();
            xhr.open("POST", "/set_mode");
            xhr.timeout = 5000;
            xhr.onerror = e => {
                console.error("setMode:", e);
                alert("Ошибка");
            };
            xhr.ontimeout = xhr.onerror;
            xhr.onabort = xhr.onerror;
            xhr.onload = e => {
                if (e.target.status === 200) {
                    try {
                        const res = JSON.parse(e.target.responseText);
                        if (!res.success) {
                            xhr.onerror("!success")
                        } else {
                            for (const id of ["on", "off", "norm"]) {
                                document.getElementById(id).className = id === mode ? "active" : "normal";
                            }
                        }
                    } catch (err) {
                        xhr.onerror(err);
                    }
                } else {
                    xhr.onerror(e.target.status);
                }
            };
            xhr.send(JSON.stringify({mode}));
        };
    </script>
</head>""" + f"""
<body>
    <div class="container">
        <h1>Duration: {timedelta(seconds=int(data["duration"]))}</h1>
        <button onclick="window.location.reload()" class="normal">UPDATE</button>
    </div>
    <div class="container">
        <button id="on" onclick="setMode('on')" class="{on_class}">ON</button>
        <button id="off" onclick="setMode('off')" class="{off_class}">OFF</button>
        <button id="norm" onclick="setMode('norm')" class="{norm_class}">NORM</button>
    </div>
</body>
</html>""",
        content_type="text/html"
    )


async def set_mode(request):
    payload = await request.json()
    data["mode"] = payload["mode"]
    write_data()
    with condition:
        condition.notify()
    return web.json_response({"success": True})


@web.middleware
async def basic_auth_middleware(request, handler):
    auth = request.headers.get("Authorization")
    if auth != "Basic " + base64.b64encode(b"user:1234").decode("UTF-8"):
        return web.Response(status=401, headers={"WWW-Authenticate": 'Basic realm="am"'})
    return await handler(request)


async def server_init():
    app = web.Application(middlewares=[basic_auth_middleware])
    app.add_routes([
        web.get("/", index),
        web.post("/set_mode", set_mode),
    ])
    runner = web.AppRunner(app)
    await runner.setup()
    ssl_context = create_ssl_context(SSL_CRT, SSL_KEY, "localhost")
    site = web.TCPSite(runner, args.addr, args.port, ssl_context=ssl_context)
    await site.start()


mouse.hook(mh)
keyboard.hook(kh)

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "rb") as f:
            data = json.loads(f.read().decode("UTF-8"))
    except Exception as e:
        print(e)

main_thread = Thread(target=main_target)
main_thread.start()

window_thread = Thread(target=window_target)
window_thread.start()

loop = asyncio.get_event_loop()
loop.run_until_complete(server_init())
loop.run_forever()

"""
╔══════════════════════════════════════════════════════╗
║         BOT DE SEÑALES - STOCKITY PRO                ║
║         Owner: @alexisl04                            ║
╚══════════════════════════════════════════════════════╝

FLUJO DE ACCESO:
  1. El owner añade un código con /addid <codigo>
     Ejemplo: /addid ALEX2024  o  /addid 7302978028
  2. El usuario escribe: /start <codigo>
  3. Si el código existe en la lista → acceso concedido, recibe señales.
  4. Si no existe → mensaje de error.
  5. Cada código solo puede ser usado por UNA persona (se consume al activarse).
"""

import time
import random
import requests
import json
import os
import threading
from collections import deque
from datetime import datetime
from typing import Optional

# ══════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════
TOKEN           = "8748620190:AAHTTjq4R0cXZEPakoBixerkksuJlDYeiRY"
OWNER_ID        = 7302978028
BASE_URL        = f"https://api.telegram.org/bot8748620190:AAHTTjq4R0cXZEPakoBixerkksuJlDYeiRY"
DB_FILE         = "usuarios_autorizados.json"
SIGNAL_INTERVAL = 120   # segundos entre señales

# ══════════════════════════════════════════════════════
#  PERSISTENCIA
# ══════════════════════════════════════════════════════
def cargar_db() -> dict:
    """
    codigos_disponibles : set de strings — códigos añadidos por el owner, aún no usados
    activos             : set de ints   — UIDs de usuarios que ya activaron acceso
    """
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE) as f:
                raw = json.load(f)
            return {
                "codigos_disponibles": set(str(c) for c in raw.get("codigos_disponibles", [])),
                "activos":             set(int(i) for i in raw.get("activos", [])) | {OWNER_ID},
            }
        except Exception as e:
            print(f"⚠️  Error cargando DB: {e}")
    return {"codigos_disponibles": set(), "activos": {OWNER_ID}}

def guardar_db():
    try:
        with open(DB_FILE, "w") as f:
            json.dump({
                "codigos_disponibles": list(db["codigos_disponibles"]),
                "activos":             list(db["activos"]),
            }, f, indent=2)
    except Exception as e:
        print(f"⚠️  Error guardando DB: {e}")

db: dict = cargar_db()

# ══════════════════════════════════════════════════════
#  API TELEGRAM
# ══════════════════════════════════════════════════════
def api(method: str, payload: dict) -> dict:
    try:
        r = requests.post(f"{BASE_URL}/{method}", json=payload, timeout=10)
        return r.json()
    except Exception as e:
        print(f"❌ API [{method}]: {e}")
        return {}

def enviar(chat_id: int, texto: str, parse_mode: str = "HTML"):
    api("sendMessage", {"chat_id": chat_id, "text": texto, "parse_mode": parse_mode})

def enviar_a_activos(texto: str):
    for uid in list(db["activos"]):
        enviar(uid, texto)

def get_updates(offset: int) -> list:
    return api("getUpdates", {
        "offset": offset, "timeout": 30, "allowed_updates": ["message"]
    }).get("result", [])

def set_commands():
    api("setMyCommands", {"commands": [
        {"command": "start",    "description": "Acceder con tu código de acceso"},
        {"command": "señales",  "description": "Estado del bot"},
        {"command": "ayuda",    "description": "Ver comandos disponibles"},
        {"command": "addid",    "description": "[ADMIN] Añadir código de acceso"},
        {"command": "removeid", "description": "[ADMIN] Eliminar código o usuario"},
        {"command": "listar",   "description": "[ADMIN] Ver códigos y usuarios"},
    ]})

# ══════════════════════════════════════════════════════
#  VERIFICACIÓN
# ══════════════════════════════════════════════════════
def es_owner(uid: int)  -> bool: return uid == OWNER_ID
def es_activo(uid: int) -> bool: return uid in db["activos"]

def denegar(chat_id: int):
    enviar(chat_id,
        "⛔ <b>ID no añadido.</b>\n\n"
        "❌ <i>No te has registrado con el enlace del dueño del bot.</i>\n\n"
        "📩 Contacta a <b>@alexisl04</b> para obtener tu código de acceso."
    )

# ══════════════════════════════════════════════════════
#  COMANDOS
# ══════════════════════════════════════════════════════
def cmd_start(msg: dict):
    uid   = msg["from"]["id"]
    name  = msg["from"].get("first_name", "Usuario")
    parts = msg.get("text", "").split()

    # Owner: acceso directo
    if es_owner(uid):
        enviar(uid,
            f"👑 <b>Bienvenido, @alexisl04!</b>\n\n"
            f"🤖 Bot <b>ACTIVO</b> · Señales cada {SIGNAL_INTERVAL // 60} min\n"
            f"🔑 Códigos disponibles: <b>{len(db['codigos_disponibles'])}</b>\n"
            f"✅ Usuarios activos: <b>{len(db['activos'])}</b>\n\n"
            "Usa /ayuda para ver tus comandos de administrador."
        )
        return

    # Ya activado
    if es_activo(uid):
        enviar(uid,
            f"✅ <b>Bienvenido de nuevo, {name}!</b>\n\n"
            "📊 Ya tienes acceso activo. Recibirás señales automáticamente.\n"
            "Usa /ayuda para ver los comandos."
        )
        return

    # Sin código → pedir que lo ingrese
    if len(parts) < 2:
        enviar(uid,
            f"👋 Hola <b>{name}</b>!\n\n"
            "🔐 Para acceder al bot necesitas un <b>código de acceso</b> "
            "proporcionado por <b>@alexisl04</b>.\n\n"
            "Una vez que lo tengas, escribe:\n"
            "<code>/start TU_CÓDIGO_AQUÍ</code>"
        )
        return

    # Validar el código ingresado
    codigo = parts[1].strip()

    if codigo in db["codigos_disponibles"]:
        # ✅ Código válido → activar usuario y consumir el código
        db["codigos_disponibles"].discard(codigo)
        db["activos"].add(uid)
        guardar_db()

        enviar(uid,
            f"🎉 <b>¡Acceso concedido, {name}!</b>\n\n"
            "✅ Tu código ha sido verificado correctamente.\n"
            f"📊 Recibirás señales automáticas cada "
            f"<b>{SIGNAL_INTERVAL // 60} minutos</b>.\n\n"
            "Usa /ayuda para ver los comandos disponibles."
        )
        enviar(OWNER_ID,
            f"🔔 <b>Nuevo usuario activo</b>\n\n"
            f"👤 <b>{name}</b>\n"
            f"🆔 <code>{uid}</code>\n"
            f"🔑 Código usado: <code>{codigo}</code>\n"
            f"✅ Total activos: <b>{len(db['activos'])}</b>"
        )
        print(f"✅ Usuario {uid} ({name}) activado con código '{codigo}'.")

    else:
        # ❌ Código no existe o ya fue usado
        denegar(uid)
        print(f"⛔ Código inválido → uid={uid}, código='{codigo}'")


def cmd_ayuda(msg: dict):
    uid = msg["from"]["id"]
    if not es_activo(uid):
        return denegar(uid)

    texto = (
        "📖 <b>Comandos disponibles</b>\n\n"
        "/start <code>&lt;código&gt;</code> — Activar acceso\n"
        "/señales — Ver estado del bot\n"
        "/ayuda — Mostrar esta ayuda\n"
    )
    if es_owner(uid):
        texto += (
            "\n🔑 <b>Administrador</b>\n\n"
            "/addid <code>&lt;código&gt;</code> — Añadir código de acceso\n"
            "/removeid <code>&lt;código_o_uid&gt;</code> — Eliminar código o usuario\n"
            "/listar — Ver códigos disponibles y usuarios activos\n"
        )
    enviar(uid, texto)


def cmd_señales(msg: dict):
    uid = msg["from"]["id"]
    if not es_activo(uid):
        return denegar(uid)
    enviar(uid,
        "📡 <b>Estado del bot</b>\n\n"
        "✅ Funcionando correctamente\n"
        f"⏱ Señales cada <b>{SIGNAL_INTERVAL // 60} minutos</b>\n"
        f"✅ Usuarios activos: <b>{len(db['activos'])}</b>\n"
        f"🔑 Códigos disponibles: <b>{len(db['codigos_disponibles'])}</b>"
    )


def cmd_addid(msg: dict):
    uid = msg["from"]["id"]
    if not es_owner(uid):
        return enviar(uid, "⛔ Solo el dueño puede usar este comando.")

    parts = msg.get("text", "").split()
    if len(parts) < 2:
        return enviar(uid,
            "⚠️ <b>Uso:</b> /addid <code>&lt;código&gt;</code>\n\n"
            "El código puede ser cualquier texto o número.\n"
            "Ejemplos:\n"
            "• <code>/addid ALEX2024</code>\n"
            "• <code>/addid 7302978028</code>\n"
            "• <code>/addid cliente01</code>",
            "HTML"
        )

    codigo = parts[1].strip()

    if codigo in db["codigos_disponibles"]:
        return enviar(uid, f"ℹ️ El código <code>{codigo}</code> ya existe.", "HTML")

    db["codigos_disponibles"].add(codigo)
    guardar_db()

    enviar(uid,
        f"✅ Código <code>{codigo}</code> añadido.\n\n"
        f"🔑 Códigos disponibles: <b>{len(db['codigos_disponibles'])}</b>\n\n"
        f"Dile al usuario que escriba:\n<code>/start {codigo}</code>",
        "HTML"
    )
    print(f"🔑 Código '{codigo}' añadido por el owner.")


def cmd_removeid(msg: dict):
    uid = msg["from"]["id"]
    if not es_owner(uid):
        return enviar(uid, "⛔ Solo el dueño puede usar este comando.")

    parts = msg.get("text", "").split()
    if len(parts) < 2:
        return enviar(uid,
            "⚠️ <b>Uso:</b> /removeid <code>&lt;código_o_uid&gt;</code>\n\n"
            "Pasa un código para eliminarlo, o el UID numérico de un usuario activo.",
            "HTML"
        )

    valor = parts[1].strip()

    # Intentar como UID numérico (usuario activo)
    try:
        target_uid = int(valor)
        if target_uid == OWNER_ID:
            return enviar(uid, "⛔ No puedes eliminar al dueño.")
        if target_uid in db["activos"]:
            db["activos"].discard(target_uid)
            guardar_db()
            return enviar(uid,
                f"🗑️ Usuario <code>{target_uid}</code> eliminado de activos.\n"
                f"✅ Activos restantes: <b>{len(db['activos'])}</b>",
                "HTML"
            )
    except ValueError:
        pass

    # Intentar como código disponible
    if valor in db["codigos_disponibles"]:
        db["codigos_disponibles"].discard(valor)
        guardar_db()
        return enviar(uid,
            f"🗑️ Código <code>{valor}</code> eliminado.\n"
            f"🔑 Códigos restantes: <b>{len(db['codigos_disponibles'])}</b>",
            "HTML"
        )

    enviar(uid,
        f"ℹ️ <code>{valor}</code> no encontrado ni como código ni como UID activo.",
        "HTML"
    )


def cmd_listar(msg: dict):
    uid = msg["from"]["id"]
    if not es_owner(uid):
        return enviar(uid, "⛔ Solo el dueño puede usar este comando.")

    codigos = db["codigos_disponibles"]
    activos = db["activos"]

    cod_txt = "\n".join(f"  • <code>{c}</code>" for c in sorted(codigos)) or "  (ninguno)"
    act_txt = "\n".join(
        f"  • <code>{i}</code>{'  👑' if i == OWNER_ID else ''}"
        for i in sorted(activos)
    )

    enviar(uid,
        f"🔑 <b>Códigos disponibles ({len(codigos)})</b>\n{cod_txt}\n\n"
        f"✅ <b>Usuarios activos ({len(activos)})</b>\n{act_txt}",
        "HTML"
    )

# ══════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════
COMANDOS = {
    "/start":    cmd_start,
    "/ayuda":    cmd_ayuda,
    "/help":     cmd_ayuda,
    "/señales":  cmd_señales,
    "/addid":    cmd_addid,
    "/removeid": cmd_removeid,
    "/listar":   cmd_listar,
}

def procesar_mensaje(msg: dict):
    uid  = msg.get("from", {}).get("id")
    text = msg.get("text", "").strip()
    if not uid or not text:
        return
    cmd = text.split()[0].split("@")[0].lower()
    if cmd in COMANDOS:
        COMANDOS[cmd](msg)
    else:
        if es_activo(uid):
            enviar(uid, "ℹ️ Usa /ayuda para ver los comandos disponibles.")
        else:
            enviar(uid,
                "👋 Para acceder escribe:\n"
                "<code>/start TU_CÓDIGO_AQUÍ</code>\n\n"
                "Si no tienes código, contacta a <b>@alexisl04</b>."
            )

# ══════════════════════════════════════════════════════
#  INDICADORES TÉCNICOS
# ══════════════════════════════════════════════════════
def get_precio() -> float:
    return round(100.0 + random.gauss(0, 1.5) + random.gauss(0, 0.3), 4)

def ema(data: list, period: int) -> Optional[float]:
    if len(data) < period:
        return None
    k, val = 2 / (period + 1), data[0]
    for p in data[1:]:
        val = p * k + val * (1 - k)
    return round(val, 4)

def rsi(data: list, period: int = 14) -> Optional[float]:
    if len(data) < period + 1:
        return None
    diffs  = [data[i] - data[i-1] for i in range(1, period + 1)]
    gains  = [d for d in diffs if d > 0]
    losses = [abs(d) for d in diffs if d < 0]
    avg_g  = sum(gains) / period
    avg_l  = sum(losses) / period if losses else 1e-9
    return round(100 - (100 / (1 + avg_g / avg_l)), 2)

def macd_line(data: list) -> Optional[float]:
    e12, e26 = ema(data, 12), ema(data, 26)
    return round(e12 - e26, 4) if e12 and e26 else None

def nivel_confianza(rsi_v, macd_v, ef, es_) -> str:
    score = 0
    if ef and es_:  score += 1 if ef > es_ else -1
    if rsi_v:       score += 1 if rsi_v > 55 else (-1 if rsi_v < 45 else 0)
    if macd_v:      score += 1 if macd_v > 0 else -1
    a = abs(score)
    return "🔥 MUY ALTA" if a >= 3 else "⚡ ALTA" if a == 2 else "📊 MEDIA" if a == 1 else "⚠️ BAJA"

# ══════════════════════════════════════════════════════
#  MOTOR DE SEÑALES
# ══════════════════════════════════════════════════════
prices         = deque(maxlen=200)
last_signal_ts = 0.0

def analizar_y_enviar():
    global last_signal_ts
    prices.append(get_precio())

    if time.time() - last_signal_ts < SIGNAL_INTERVAL:
        return
    last_signal_ts = time.time()

    data   = list(prices)
    ef     = ema(data, 5)
    es_    = ema(data, 10)
    rsi_v  = rsi(data, 14)
    macd_v = macd_line(data)
    precio = data[-1]

    if ef and es_:
        tipo, icono = ("🟢 CALL", "📈") if ef > es_ else ("🔴 PUT", "📉")
    else:
        tipo, icono = random.choice([("🟢 CALL", "📈"), ("🔴 PUT", "📉")])

    conf   = nivel_confianza(rsi_v, macd_v, ef, es_)
    hora   = datetime.utcnow().strftime("%H:%M:%S UTC")
    rsi_s  = f"{rsi_v:.1f}"  if rsi_v  else "N/D"
    macd_s = f"{macd_v:.4f}" if macd_v else "N/D"
    ef_s   = f"{ef:.4f}"     if ef     else "N/D"
    es_s   = f"{es_:.4f}"    if es_    else "N/D"

    señal = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🚨 <b>SEÑAL AUTOMÁTICA</b> {icono}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Dirección:</b>  {tipo}\n"
        f"<b>Precio:</b>     <code>{precio:.4f}</code>\n\n"
        f"<b>RSI (14):</b>   <code>{rsi_s}</code>\n"
        f"<b>EMA Rápida:</b> <code>{ef_s}</code>\n"
        f"<b>EMA Lenta:</b>  <code>{es_s}</code>\n"
        f"<b>MACD:</b>       <code>{macd_s}</code>\n\n"
        f"<b>Confianza:</b>  {conf}\n"
        f"<b>Expiración:</b> 1 – 3 min\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    print(f"[SEÑAL] {hora} → {tipo} | RSI {rsi_s} | {conf}")
    enviar_a_activos(señal)

# ══════════════════════════════════════════════════════
#  HILOS
# ══════════════════════════════════════════════════════
def loop_señales():
    while True:
        try:
            analizar_y_enviar()
        except Exception as e:
            print(f"[señales] {e}")
        time.sleep(2)

def loop_polling():
    offset = 0
    print("📡 Polling activo...")
    while True:
        try:
            for upd in get_updates(offset):
                offset = upd["update_id"] + 1
                msg = upd.get("message")
                if msg:
                    procesar_mensaje(msg)
        except Exception as e:
            print(f"[polling] {e}")
            time.sleep(5)

# ══════════════════════════════════════════════════════
#  INICIO
# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    print("╔══════════════════════════════════════╗")
    print("║    BOT STOCKITY PRO — @alexisl04     ║")
    print("╚══════════════════════════════════════╝")

    set_commands()

    enviar(OWNER_ID,
        "🚀 <b>Bot iniciado correctamente</b>\n\n"
        f"🔑 Códigos disponibles: <b>{len(db['codigos_disponibles'])}</b>\n"
        f"✅ Usuarios activos: <b>{len(db['activos'])}</b>\n"
        f"⏱ Señales cada: <b>{SIGNAL_INTERVAL // 60} min</b>\n\n"
        "Usa /addid para crear códigos de acceso.\n"
        "El usuario activa su acceso con: <code>/start su_código</code>"
    )

    threading.Thread(target=loop_señales, daemon=True).start()
    loop_polling()
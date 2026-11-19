"""
Muestra de Yayita: acceso a la app desde el celular (extracto simplificado de core/acceso.py).

- PIN de 6 dígitos generado con `secrets` (no con `random`).
- Comparaciones con `hmac.compare_digest`, para no filtrar información por el tiempo de respuesta.
- La cookie lleva su fecha de vencimiento y una firma HMAC-SHA256: no se puede inventar ni alargar.
  Si se cambia el PIN, todas las cookies anteriores dejan de valer.
- Máximo 5 PIN equivocados cada 5 minutos por IP, y aviso al celular por Telegram.
"""
import hashlib
import hmac
import secrets
import threading
import time

DURACION_COOKIE = 7 * 24 * 3600      # 7 días
MAX_INTENTOS = 5
VENTANA_INTENTOS = 5 * 60             # 5 minutos

_lock = threading.Lock()
_intentos_fallidos = {}               # ip -> [momentos de los intentos fallidos]

PIN = f"{secrets.randbelow(10**6):06d}"
SECRETO = secrets.token_hex(32)       # en Yayita se guarda en un archivo fuera de git (permisos 600)
TOKEN = hmac.new(SECRETO.encode(), PIN.encode(), hashlib.sha256).hexdigest()


def _firma(vence):
    return hmac.new(TOKEN.encode(), str(vence).encode(), hashlib.sha256).hexdigest()


def cookie_nueva(ahora=None):
    """"<vence>.<firma>": vale hasta esa fecha (epoch)."""
    vence = int((ahora or time.time()) + DURACION_COOKIE)
    return f"{vence}.{_firma(vence)}"


def cookie_valida(cookie, ahora=None):
    vence, _, firma = (cookie or "").partition(".")
    if not TOKEN or not vence.isdigit() or int(vence) < (ahora or time.time()):
        return False
    return hmac.compare_digest(firma.encode(), _firma(int(vence)).encode())


def demasiados_intentos(ip):
    ahora = time.time()
    with _lock:
        recientes = [t for t in _intentos_fallidos.get(ip, []) if ahora - t < VENTANA_INTENTOS]
        _intentos_fallidos[ip] = recientes
    return len(recientes) >= MAX_INTENTOS


def probar_pin(ip, pin):
    """¿Es el PIN correcto? Si no, cuenta el intento fallido de esa IP."""
    if PIN and hmac.compare_digest(pin.encode(), PIN.encode()):
        return True
    with _lock:
        _intentos_fallidos.setdefault(ip, []).append(time.time())
        cuantos = len(_intentos_fallidos[ip])
    print(f"[SEGURIDAD] PIN incorrecto desde {ip}")
    if cuantos in (1, MAX_INTENTOS):  # el primero y el que lo bloquea, para no llenar el celular de avisos
        al_avisar(f"⚠️ Alguien puso mal el PIN de la app desde {ip}"
                  + (f" ({cuantos} veces: lo bloqueé unos minutos)." if cuantos == MAX_INTENTOS else "."))
    return False


# Gancho: cómo avisar al celular (en Yayita, por Telegram).
al_avisar = print


if __name__ == "__main__":
    c = cookie_nueva()
    print(cookie_valida(c))                          # True
    print(cookie_valida(c[:-1] + "0"))               # False: firma alterada
    print(cookie_valida(cookie_nueva(ahora=0)))      # False: vencida
    for _ in range(5):
        probar_pin("100.64.0.9", "000000")
    print(demasiados_intentos("100.64.0.9"))         # True: bloqueada

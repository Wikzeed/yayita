"""
Muestra de Yayita: la LISTA BLANCA de acciones (extracto simplificado de yayita/dispositivos.py).

La idea central de la seguridad: la IA nunca ejecuta nada. Solo puede *pedir* una acción escribiendo una
etiqueta como [ACCION:LUZ:off] en su respuesta. El código revisa cada etiqueta:

1. ¿El nombre está en la lista blanca?
2. ¿El parámetro es válido para esa acción? (un número entre 0 y 100, un color conocido, etc.)
3. ¿Tiene que ver con lo que pidió el usuario? (si preguntaste por el clima, no puede pausar la música)
4. Máximo 2 acciones por respuesta, y encender el PC siempre pide confirmación.

Todo lo que no pasa se ignora y queda anotado como [SEGURIDAD].
"""
import re
import unicodedata

COLORES = {"rojo", "verde", "azul", "blanco", "amarillo", "morado", "rosado", "naranjo"}

ACCIONES = {
    "MUSICA_PLAY":   {"param": None,         "confirmar": False},
    "MUSICA_PAUSA":  {"param": None,         "confirmar": False},
    "MUSICA_BUSCAR": {"param": "texto",      "confirmar": False},
    "VOLUMEN":       {"param": "volumen",    "confirmar": False},
    "LUZ":           {"param": "on_off",     "confirmar": False},
    "LUZ_BRILLO":    {"param": "porcentaje", "confirmar": False},
    "LUZ_COLOR":     {"param": "color",      "confirmar": False},
    "PC":            {"param": "pc",         "confirmar": True},
}
MAX_ACCIONES_POR_RESPUESTA = 2
ETIQUETA_RE = re.compile(r"\[ACCION:([A-Z_]+)(?::([^\]]{0,80}))?\]")


def _sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _texto_seguro(texto, largo=60):
    """Solo letras, números y algo de puntuación: el texto termina dentro de AppleScript o de una búsqueda."""
    return re.sub(r"[^\w\s.,'&-]", "", texto)[:largo].strip()


def _validar_param(tipo, valor):
    """Devuelve el parámetro limpio, o None si no es válido."""
    original = (valor or "").strip()
    if tipo == "texto":
        return _texto_seguro(original) or None
    valor = _sin_tildes(original.lower())
    if tipo is None:
        return "" if not valor else None
    if tipo == "volumen":
        if valor in ("subir", "bajar", "silencio"):
            return valor
        return valor if valor.isdigit() and 0 <= int(valor) <= 100 else None
    if tipo == "on_off":
        return {"on": "on", "off": "off", "encender": "on", "apagar": "off"}.get(valor)
    if tipo == "porcentaje":
        return valor if valor.isdigit() and 1 <= int(valor) <= 100 else None
    if tipo == "color":
        return valor if valor in COLORES else None
    if tipo == "pc":
        return {"": "encender", "encender": "encender", "apagar": "apagar", "suspender": "suspender"}.get(valor)
    return None


def validar(nombre, param=""):
    regla = ACCIONES.get(nombre)
    if not regla:
        return None
    limpio = _validar_param(regla["param"], param)
    return None if limpio is None else (nombre, limpio)


def extraer_acciones(texto):
    """Saca las etiquetas [ACCION:...] válidas de una respuesta de la IA (máx. 2); las inválidas se ignoran."""
    acciones = []
    for nombre, param in ETIQUETA_RE.findall(texto):
        accion = validar(nombre, param)
        if accion:
            acciones.append(accion)
        else:
            print(f"[SEGURIDAD] Acción ignorada (no está en la lista blanca o parámetro inválido): {nombre}:{param}")
    return acciones[:MAX_ACCIONES_POR_RESPUESTA]


# Segunda revisión: la acción tiene que tener que ver con lo que dijo el usuario.
# (Caso real: a "¿cómo está el clima?" un modelo agregó [ACCION:MUSICA_PAUSA]: válida, pero nadie la pidió.)
PISTAS = {
    "MUSICA": r"music|cancion|playlist|pon|reproduc|escuch|pausa|para|siguiente|artista|banda|album|radio",
    "VOLUMEN": r"volumen|fuerte|bajo|silencio|sube|baja|ruido|^\s*\d{1,3}\s*(%|por ciento)?\s*$",
    "LUZ": r"luz|luces|lampara|oscur|color|brillo|apaga|enciende|prende|^\s*\d{1,3}\s*(%|por ciento)?\s*$",
    "PC": r"\bpc\b|computador|compu",
}


def tiene_que_ver(texto_usuario, nombre):
    familia = next(f for f in PISTAS if nombre.startswith(f))
    if re.search(PISTAS[familia], _sin_tildes(texto_usuario.lower())):
        return True
    print(f"[SEGURIDAD] Acción {nombre} ignorada: no tiene que ver con lo que se pidió.")
    return False


if __name__ == "__main__":
    respuesta = ("Listo, apago la luz. [ACCION:LUZ:off] [ACCION:BORRAR_TODO:si] "
                 "[ACCION:VOLUMEN:999] [ACCION:LUZ_COLOR:azul] [ACCION:MUSICA_PAUSA]")
    print(extraer_acciones(respuesta))   # [('LUZ', 'off'), ('LUZ_COLOR', 'azul')]
    print(tiene_que_ver("¿cómo está el clima?", "MUSICA_PAUSA"))   # False

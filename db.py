import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

APP_DIR = Path.home() / ".me-paga"
DB_PATH = APP_DIR / "me-paga.db"

METODOS = ["Efectivo", "Transferencia", "Deposito", "Otro"]

DEFAULTS = {
    "titular": "Tia",
    "deuda_inicial": "0",
    "moneda": "MXN",
}


def get_connection():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with closing(get_connection()) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS abonos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                monto REAL NOT NULL,
                metodo TEXT,
                nota TEXT,
                creado_en TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS config (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_abonos_fecha ON abonos (fecha)")
        for clave, valor in DEFAULTS.items():
            conn.execute(
                "INSERT OR IGNORE INTO config (clave, valor) VALUES (?, ?)",
                (clave, valor),
            )


def parse_fecha(texto):
    if isinstance(texto, date):
        return texto
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("La fecha no puede estar vacia")
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ValueError(f"Fecha no valida: {texto}. Usa dd/mm/aaaa")


def parse_monto(texto):
    if isinstance(texto, (int, float)):
        valor = float(texto)
    else:
        limpio = (texto or "").strip().replace("$", "").replace(",", "").replace(" ", "")
        if not limpio:
            raise ValueError("El monto no puede estar vacio")
        try:
            valor = float(limpio)
        except ValueError:
            raise ValueError(f"Monto no valido: {texto}")
    if valor <= 0:
        raise ValueError("El monto debe ser mayor que cero")
    return round(valor, 2)


def add_abono(fecha, monto, metodo="", nota=""):
    fecha_obj = parse_fecha(fecha)
    monto_val = parse_monto(monto)
    with closing(get_connection()) as conn, conn:
        cur = conn.execute(
            """
            INSERT INTO abonos (fecha, monto, metodo, nota, creado_en)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                fecha_obj.isoformat(),
                monto_val,
                (metodo or "").strip(),
                (nota or "").strip(),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return cur.lastrowid


def update_abono(abono_id, fecha, monto, metodo="", nota=""):
    fecha_obj = parse_fecha(fecha)
    monto_val = parse_monto(monto)
    with closing(get_connection()) as conn, conn:
        cur = conn.execute(
            """
            UPDATE abonos SET fecha = ?, monto = ?, metodo = ?, nota = ?
            WHERE id = ?
            """,
            (
                fecha_obj.isoformat(),
                monto_val,
                (metodo or "").strip(),
                (nota or "").strip(),
                abono_id,
            ),
        )
        return cur.rowcount


def delete_abono(abono_id):
    with closing(get_connection()) as conn, conn:
        cur = conn.execute("DELETE FROM abonos WHERE id = ?", (abono_id,))
        return cur.rowcount


def list_abonos():
    with closing(get_connection()) as conn:
        filas = conn.execute(
            "SELECT * FROM abonos ORDER BY fecha ASC, id ASC"
        ).fetchall()
    return [dict(f) for f in filas]


def total_abonado():
    with closing(get_connection()) as conn:
        fila = conn.execute("SELECT COALESCE(SUM(monto), 0) AS t FROM abonos").fetchone()
    return round(fila["t"], 2)


def contar_abonos():
    with closing(get_connection()) as conn:
        fila = conn.execute("SELECT COUNT(*) AS n FROM abonos").fetchone()
    return fila["n"]


def get_config(clave, default=""):
    with closing(get_connection()) as conn:
        fila = conn.execute("SELECT valor FROM config WHERE clave = ?", (clave,)).fetchone()
    return fila["valor"] if fila else default


def set_config(clave, valor):
    with closing(get_connection()) as conn, conn:
        conn.execute(
            """
            INSERT INTO config (clave, valor) VALUES (?, ?)
            ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor
            """,
            (clave, str(valor)),
        )


def get_deuda_inicial():
    try:
        return round(float(get_config("deuda_inicial", "0")), 2)
    except ValueError:
        return 0.0


def set_deuda_inicial(valor):
    if isinstance(valor, str):
        limpio = valor.strip().replace("$", "").replace(",", "").replace(" ", "")
        valor = float(limpio or 0)
    if valor < 0:
        raise ValueError("La deuda inicial no puede ser negativa")
    set_config("deuda_inicial", round(float(valor), 2))


def saldo_pendiente():
    return round(get_deuda_inicial() - total_abonado(), 2)

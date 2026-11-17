"""Conexión a PostgreSQL, creación de tablas y datos iniciales."""
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

# CAMBIA "TU_CLAVE" por la contraseña que pusiste al instalar PostgreSQL (o define la variable DATABASE_URL)
URL = os.getenv("DATABASE_URL", "postgresql://postgres:TU_CLAVE@localhost:5432/erp")

# Toneladas mensuales que ingresan a la Central Mayorista de Antioquia (DANE, SIPSA-A), dic 2025 a ago 2026
TON = [102341, 93718, 93743, 100501, 94819, 98957, 96431, 104728, 98519]
MESES = ["2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"]

# Precios: DANE SIPSA, boletín diario 24-sep-2026. El resto son supuestos documentados.
PRODUCTOS = [
    ("PC-01", "Papa criolla", "kg", 4225, 120000, 0.35, 2, 95, 15, 1800, 18000,
     "Peñol, Marinilla, El Santuario, La Unión, Sonsón, San Vicente Ferrer", "FEFO"),
    ("PG-02", "Plátano guineo", "kg", 1325, 120000, 0.35, 2, 97, 7, 1900, 30000,
     "Andes, Jardín, Pueblorrico, Peñol (Antioquia); Aguadas, Pácora (Caldas)", "FEFO"),
    ("PI-03", "Pimentón", "kg", 2675, 120000, 0.35, 1, 90, 10, 400, 9000,
     "El Santuario, Marinilla, Peñol (Antioquia)", "FEFO"),
]


def conn():
    return psycopg.connect(URL, row_factory=dict_row)


def init():
    with conn() as c:
        c.execute((Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))
        if c.execute("SELECT COUNT(*) AS n FROM productos").fetchone()["n"] == 0:
            with c.cursor() as cur:
                cur.executemany("INSERT INTO productos VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", PRODUCTOS)
                prom = sum(TON) / len(TON)
                for p in PRODUCTOS:
                    for mes, t in zip(MESES, TON):
                        cur.execute("INSERT INTO demanda VALUES (%s,%s,%s)", (p[0], mes, round(p[10] * t / prom)))

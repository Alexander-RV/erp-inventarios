"""API del ERP de inventarios. Ejecutar: uvicorn main:app --reload"""
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

import db
from models import calcular, simular

UMBRAL_CONSUMO = 1.3   # alarma de consumo: se activa si lo consumido en 24 h supera 1,3 veces el consumo diario esperado

app = FastAPI(title="ERP de Inventarios", version="2.0")
db.init()


def _producto(c, pid):
    p = c.execute("SELECT * FROM productos WHERE id=%s", (pid,)).fetchone()
    if not p:
        raise HTTPException(404, "Producto no existe")
    hist = [r["cantidad"] for r in c.execute("SELECT cantidad FROM demanda WHERE producto_id=%s ORDER BY mes", (pid,))]
    return p, hist


def _mover(c, pid, tipo, cantidad, nota):
    p, hist = _producto(c, pid)
    if tipo == "salida" and cantidad > p["stock"]:
        raise HTTPException(400, "No hay stock suficiente")
    nuevo = p["stock"] + (cantidad if tipo == "entrada" else -cantidad)
    c.execute("UPDATE productos SET stock=%s WHERE id=%s", (nuevo, pid))
    c.execute("INSERT INTO movimientos(producto_id,tipo,cantidad,stock_resultante,nota) VALUES (%s,%s,%s,%s,%s)",
              (pid, tipo, cantidad, nuevo, nota))
    p["stock"] = nuevo
    return {"stock": nuevo, **calcular(p, hist)}


@app.get("/")
def inicio():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/productos")
def productos():
    with db.conn() as c:
        out = []
        for r in c.execute("SELECT id FROM productos ORDER BY id").fetchall():
            p, hist = _producto(c, r["id"])
            m = calcular(p, hist)
            cons = c.execute("""SELECT COALESCE(SUM(cantidad),0) AS q FROM movimientos
                                WHERE producto_id=%s AND tipo='salida' AND fecha >= now() - interval '24 hours'""",
                             (r["id"],)).fetchone()["q"]
            ratio = round(cons / m["demanda_diaria"], 2) if m["demanda_diaria"] else 0
            out.append({**p, "demanda_mensual": hist, **m, "consumo_24h": cons, "ratio_consumo": ratio,
                        "umbral_consumo": UMBRAL_CONSUMO, "alarma_consumo": ratio > UMBRAL_CONSUMO})
        return out


class Movimiento(BaseModel):
    producto_id: str
    tipo: str          # "salida" (consumo) o "entrada" (recepción)
    cantidad: float
    nota: str = ""


@app.post("/api/movimientos")
def registrar(m: Movimiento):
    if m.tipo not in ("entrada", "salida") or m.cantidad <= 0:
        raise HTTPException(400, "Tipo o cantidad inválidos")
    with db.conn() as c:
        return _mover(c, m.producto_id, m.tipo, m.cantidad, m.nota)


@app.get("/api/alarmas")
def alarmas():
    return [p for p in productos() if p["estado"] != "NORMAL"]


@app.get("/api/kardex")
def kardex():
    with db.conn() as c:
        return c.execute("""SELECT m.*, p.nombre FROM movimientos m JOIN productos p ON p.id=m.producto_id
                            ORDER BY m.id DESC LIMIT 30""").fetchall()


class Orden(BaseModel):
    producto_id: str


@app.get("/api/ordenes")
def ordenes():
    with db.conn() as c:
        return c.execute("""SELECT o.*, p.nombre, p.unidad FROM ordenes_compra o JOIN productos p ON p.id=o.producto_id
                            ORDER BY o.id DESC""").fetchall()


@app.post("/api/ordenes")
def crear_orden(o: Orden):
    with db.conn() as c:
        p, hist = _producto(c, o.producto_id)
        if c.execute("SELECT 1 FROM ordenes_compra WHERE producto_id=%s AND estado='PENDIENTE'", (o.producto_id,)).fetchone():
            raise HTTPException(400, "Ya existe una orden pendiente para este producto")
        q = calcular(p, hist)["eoq"]
        return c.execute("INSERT INTO ordenes_compra(producto_id,cantidad) VALUES (%s,%s) RETURNING *", (o.producto_id, q)).fetchone()


@app.post("/api/ordenes/{oid}/recibir")
def recibir_orden(oid: int):
    with db.conn() as c:
        o = c.execute("SELECT * FROM ordenes_compra WHERE id=%s", (oid,)).fetchone()
        if not o or o["estado"] != "PENDIENTE":
            raise HTTPException(400, "Orden no existe o ya fue recibida")
        c.execute("UPDATE ordenes_compra SET estado='RECIBIDA', recibida=now() WHERE id=%s", (oid,))
        return _mover(c, o["producto_id"], "entrada", o["cantidad"], f"Recepción orden de compra #{oid}")


@app.get("/api/simulacion/{pid}")
def simulacion(pid: str, dias: int = Query(365, ge=30, le=730), semilla: int = 7):
    with db.conn() as c:
        p, hist = _producto(c, pid)
    return {"producto": p["nombre"], "dias": dias, "punto_reorden": calcular(p, hist)["punto_reorden"],
            "sQ": simular(p, hist, "sQ", dias, semilla), "RS": simular(p, hist, "RS", dias, semilla)}

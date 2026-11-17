"""Modelos de inventario: EOQ, stock de seguridad, punto de reorden, pronóstico y simulación."""
import random
from math import ceil, floor, sqrt
from statistics import NormalDist, mean

CV_DIARIO = 0.109  # variabilidad diaria real del abastecimiento, DANE-SIPSA (Central Mayorista de Antioquia)


def pronostico(hist, alpha=0.3):
    """Suavización exponencial simple: pronóstico del próximo mes."""
    f = hist[0]
    for x in hist:
        f = alpha * x + (1 - alpha) * f
    return f


def calcular(p, hist):
    D = mean(hist) * 12                                   # demanda anual
    f = pronostico(hist)
    d = f / 30                                            # demanda diaria
    sigma_d = CV_DIARIO * d                               # desviación diaria
    H = p["costo"] * p["tasa_mantener"]                   # costo de mantener por unidad-año
    z = NormalDist().inv_cdf(p["nivel_servicio"] / 100)   # factor de servicio

    eoq_teorico = ceil(sqrt(2 * D * p["costo_pedir"] / H))            # Q* = raíz(2DS/H)
    eoq = max(1, min(eoq_teorico, floor(d * p["vida_util"] * 0.8)))   # límite por vida útil
    ss = ceil(z * sigma_d * sqrt(p["lead_time"]))                     # SS = z·σd·raíz(L)
    rop = ceil(d * p["lead_time"] + ss)                               # ROP = d·L + SS
    maximo = rop + eoq

    stock = p["stock"]
    if stock <= ss:
        estado = "CRITICO"
    elif stock <= rop:
        estado = "REORDENAR"
    elif stock > maximo:
        estado = "SOBRESTOCK"
    else:
        estado = "NORMAL"

    # Alarma de tiempo: ¿cuánto falta para el punto de reorden y alcanza el stock hasta que llegue un pedido?
    dias_rop = max(0.0, (stock - rop) / d)
    dias_quiebre = stock / d
    if dias_quiebre <= p["lead_time"]:
        alarma_tiempo = "CRITICA"       # el stock se acaba antes de que llegue un pedido hecho hoy
    elif stock <= rop:
        alarma_tiempo = "REORDENAR"     # ya se llegó al punto de reorden
    elif dias_rop <= 0.5:
        alarma_tiempo = "PRONTO"        # faltan menos de 12 horas para el punto de reorden
    else:
        alarma_tiempo = "OK"

    return {
        "demanda_anual": round(D), "demanda_diaria": round(d, 1), "pronostico_mensual": round(f),
        "z": round(z, 3), "H": round(H, 1), "eoq_teorico": eoq_teorico, "eoq": eoq,
        "stock_seguridad": ss, "punto_reorden": rop, "maximo": maximo,
        "pedidos_anuales": round(D / eoq, 1),
        "costo_anual": round(D * p["costo"] + D / eoq * p["costo_pedir"] + eoq / 2 * H + ss * H),
        "cobertura_dias": round(stock / d, 1), "estado": estado,
        "dias_hasta_rop": round(dias_rop, 1), "dias_hasta_quiebre": round(dias_quiebre, 1), "alarma_tiempo": alarma_tiempo,
    }


def simular(p, hist, politica, dias=365, semilla=7):
    """Simula `dias` de operación. politica: 'sQ' (revisión continua) o 'RS' (revisión periódica cada 7 días)."""
    rnd = random.Random(semilla)            # misma semilla = misma demanda para ambas políticas
    m = calcular(p, hist)
    d = pronostico(hist) / 30
    sigma = CV_DIARIO * d
    L = p["lead_time"]
    z = NormalDist().inv_cdf(p["nivel_servicio"] / 100)
    h_dia = p["costo"] * p["tasa_mantener"] / 365
    R = 7
    S = ceil(d * (R + L) + z * sigma * sqrt(R + L))   # nivel objetivo de la revisión periódica

    stock = float(m["maximo"])
    transito = []                                      # pedidos en camino: (día de llegada, cantidad)
    pedidos, perdidas, demanda_total, costo_mant, dias_quiebre = 0, 0.0, 0.0, 0.0, 0
    serie, suma_stock = [round(stock)], 0.0

    for dia in range(1, dias + 1):
        stock += sum(q for t, q in transito if t == dia)
        transito = [(t, q) for t, q in transito if t != dia]
        dem = max(0.0, rnd.gauss(d, sigma))
        demanda_total += dem
        servido = min(stock, dem)
        if dem > servido:
            perdidas += dem - servido
            dias_quiebre += 1
        stock -= servido
        costo_mant += stock * h_dia
        suma_stock += stock
        pos = stock + sum(q for _, q in transito)
        if politica == "sQ":
            if pos <= m["punto_reorden"]:
                transito.append((dia + L, m["eoq"]))
                pedidos += 1
        elif dia % R == 0 and pos < S:
            transito.append((dia + L, S - pos))
            pedidos += 1
        serie.append(round(stock))

    costo_pedir = pedidos * p["costo_pedir"]
    return {
        "politica": politica, "pedidos": pedidos, "dias_quiebre": dias_quiebre,
        "nivel_servicio": round(100 * (1 - perdidas / demanda_total), 2),
        "unidades_perdidas": round(perdidas), "stock_promedio": round(suma_stock / dias),
        "costo_pedir": round(costo_pedir), "costo_mantener": round(costo_mant),
        "costo_total": round(costo_pedir + costo_mant), "serie": serie,
    }

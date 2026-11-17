CREATE TABLE IF NOT EXISTS productos(
  id TEXT PRIMARY KEY, nombre TEXT NOT NULL, unidad TEXT NOT NULL,
  costo DOUBLE PRECISION NOT NULL, costo_pedir DOUBLE PRECISION NOT NULL,
  tasa_mantener DOUBLE PRECISION NOT NULL, lead_time INT NOT NULL,
  nivel_servicio INT NOT NULL, vida_util INT NOT NULL,
  stock DOUBLE PRECISION NOT NULL, demanda_base DOUBLE PRECISION NOT NULL,
  origen TEXT, politica TEXT);
CREATE TABLE IF NOT EXISTS demanda(
  producto_id TEXT REFERENCES productos(id), mes TEXT, cantidad DOUBLE PRECISION,
  PRIMARY KEY(producto_id, mes));
CREATE TABLE IF NOT EXISTS movimientos(
  id SERIAL PRIMARY KEY, producto_id TEXT REFERENCES productos(id),
  fecha TIMESTAMP DEFAULT now(), tipo TEXT, cantidad DOUBLE PRECISION,
  stock_resultante DOUBLE PRECISION, nota TEXT);
CREATE TABLE IF NOT EXISTS ordenes_compra(
  id SERIAL PRIMARY KEY, producto_id TEXT REFERENCES productos(id),
  cantidad DOUBLE PRECISION, estado TEXT DEFAULT 'PENDIENTE',
  creada TIMESTAMP DEFAULT now(), recibida TIMESTAMP);

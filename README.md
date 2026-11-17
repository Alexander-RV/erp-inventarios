# ERP de Inventarios · Central Mayorista de Antioquia
Control de inventarios de papa criolla, plátano guineo y pimentón con datos del DANE (SIPSA).
Python (FastAPI) + PostgreSQL + interfaz web.

## Ejecutar en local
1. Crear la base `erp` en PostgreSQL.
2. Definir la conexión con la variable DATABASE_URL, por ejemplo:
   postgresql://postgres:TU_CLAVE@localhost:5432/erp
   (o cambiar TU_CLAVE en db.py)
3. pip install -r requirements.txt
4. uvicorn main:app --reload
5. Abrir http://127.0.0.1:8000

## Despliegue en Render
El archivo render.yaml crea el servicio web y la base PostgreSQL. La app lee DATABASE_URL.

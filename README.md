# TrendMode MX — Tiendita 24/7 (Proyecto 4)

![Python](https://shields.io)
![FastAPI](https://shields.io)
![Polars](https://shields.io)
![Chart.js](https://shields.io)

Proyecto de tienda de ropa con API REST en **FastAPI**, persistencia en archivos planos (`productos.csv`, `ventas.csv`), histórico columnar en **Parquet**, consultas analíticas con **Polars**, corte de caja automático con **APScheduler** y dashboard interactivo con **Chart.js**.

> **Docente:** Prof. Diego Ayala — Programación IV  
> **Autora:** Esther Bautista  
> **Entrega:** Repositorio público en GitHub  

---

## 1. Descripción del proyecto

Sistema full-stack que simula una tienda de ropa operando 24/7. Permite:

- Registrar, listar y eliminar productos del inventario (`productos.csv`).
- Comprar productos con descuento de stock protegido por `asyncio.Lock()`.
- Registrar cada venta al final de `ventas.csv` (append transaccional).
- Consultar KPIs y gráficas que combinan el **histórico** (`ventas.parquet`) con las **ventas del día** (`ventas.csv`) mediante `pl.concat()` en memoria (unión virtual, cero duplicados).
- Ejecutar un **Corte de Caja automático** con `APScheduler` dentro del `lifespan` de FastAPI, que fusiona el CSV en el Parquet y deja `ventas.csv` vacío (solo encabezados), sin detener la API.

---

## 2. Resumen por unidad

| Unidad | Enfoque técnico | Implementación en el sistema |
| :--- | :--- | :--- |
| **U1** | Arquitectura API y Cliente Web | Servidor REST en FastAPI (`main.py`) y cliente en HTML/CSS/JS (`index.html`, `app.js`) con peticiones `fetch()` asíncronas. Endpoints: `GET /productos`, `POST /productos`, `PUT /productos/{id}/comprar`, `DELETE /productos/{id}`, `GET /kpis`, `GET /ventas-por-producto`, `GET /ventas-por-fecha`. |
| **U2** | Concurrencia y Tolerancia a Fallas | Validación con **Pydantic** (`CrearProducto`, `RespuestaProducto`), manejo de `HTTPException` (400, 404, 500) y protección contra condiciones de carrera con **`asyncio.Lock()`** en compra y corte. |
| **U3** | Persistencia y Visualización | Inventario en `productos.csv`, registro transaccional en `ventas.csv` (con Pandas) y tablero interactivo con **Chart.js** (barras + línea) y tarjetas KPI. |
| **U4** | Big Data y Operación 24/7 | Generación masiva con **NumPy** (`generar_parquet.py`), almacenamiento columnar en **Parquet**, consulta paralela con **Polars** (`scan_parquet` + `scan_csv` + `concat`) y corte automático con **APScheduler**. |

---

## 3. Tecnologías

- **Backend:** Python, FastAPI, Uvicorn, Pandas, Polars, NumPy, Pydantic, APScheduler
- **Frontend:** HTML5, CSS3 (Bootstrap 5), JavaScript (Fetch API, Chart.js)
- **Persistencia:** Archivos planos (`productos.csv`, `ventas.csv`) + histórico columnar (`ventas.parquet`)

---

## 4. Estructura del repositorio

```text
Tiendita-Proyecto4/
├── main.py              # Backend FastAPI + APScheduler
├── generar_parquet.py   # Generador masivo NumPy/Polars -> ventas.parquet
├── productos.csv        # Inventario (id, nombre, precio, cantidad, categoria)
├── ventas.csv           # Plantilla de ventas del turno (solo encabezados)
├── ventas.parquet       # Histórico columnar (generado, puede no subirse)
├── index.html           # Cliente web
├── app.js               # Lógica del dashboard
└── README.md            # Documentación del proyecto
```

> **Nota sobre archivos pesados:** Si `ventas.parquet` supera el límite de GitHub o para mantener el repo ligero, **no se sube**. Antes de iniciar el servidor ejecuta `python generar_parquet.py`.

---

## 5. Instalación y ejecución paso a paso

### 5.1. Requisitos

- Python 3.10 o superior
- Navegador moderno

### 5.2. Instalar dependencias

```bash
pip install fastapi uvicorn pandas polars numpy pydantic apscheduler
```

### 5.3. (Opcional pero recomendado) Generar el histórico Parquet

```bash
python generar_parquet.py
```

Esto crea `ventas.parquet` con entre **1,000,000 y 2,000,000** de registros simulados usando los productos y precios reales de la tienda, manteniendo un esquema idéntico al de `ventas.csv`.

### 5.4. Iniciar el servidor

```bash
uvicorn main:app --reload --port 8000
```

### 5.5. Abrir el cliente web

Abre `index.html` en el navegador (o sírvelo con Live Server). El dashboard consume la API en `http://127.0.0.1:8000`.

---

## 6. Endpoints principales

| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `GET` | `/productos` | Lista el inventario completo. |
| `POST` | `/productos` | Registra un producto nuevo (valida con Pydantic). |
| `PUT` | `/productos/{producto_id}/comprar` | Procesa compra con `asyncio.Lock()`, descuenta stock y hace append a `ventas.csv`. |
| `DELETE` | `/productos/{producto_id}` | Elimina un producto del inventario. |
| `GET` | `/kpis` | Ingresos totales, transacciones y producto estrella (Parquet + CSV con Polars). |
| `GET` | `/ventas-por-producto` | Top 10 productos por ingresos (Chart.js barras). |
| `GET` | `/ventas-por-fecha` | Ingresos por fecha, últimos 30 días (Chart.js línea). |

---

## 7. Corte de Caja automático (APScheduler)

Integrado en el `lifespan` de FastAPI con `AsyncIOScheduler`. Se ejecuta por intervalo de minutos (demostración en clase) o por cron diario. Bajo `async with lock:`:

1. Lee `ventas.csv` si existen registros nuevos.
2. Fusiona físicamente los datos con `ventas.parquet` y guarda en disco.
3. Vacía `ventas.csv` dejando únicamente los encabezados.
4. El servicio **no se detiene** en ningún momento durante el proceso.

---

## 8. Lista de verificación

- [x] Catálogo, compra con descuento de stock, gráficas Chart.js y tarjetas KPI funcionando de inicio a fin.
- [x] Al comprar, el contador total del dashboard aumenta sin duplicar registros anteriores (unión virtual `pl.concat`).
- [x] Al ejecutarse el corte, `ventas.csv` queda vacío (solo encabezados) y `ventas.parquet` conserva el histórico.
- [x] `generar_parquet.py` crea entre 1M y 2M de registros con NumPy/Polars y esquema idéntico a `ventas.csv`.
- [x] Repositorio público con código actualizado y este `README.md`.

---

## 9. Autoría

**Esther Bautista** — Proyecto 4, Programación IV.

# main.py
# ============================================================
# Titulo: Tienda de ropa - TrendMode MX (Proyecto 4)
# Autora: Esther Bautista
# Fecha:  23 de noviembre de 2026
# Descripcion: FastAPI + Pandas + Polars + Parquet + APScheduler
#              con proteccion de condiciones de carrera (asyncio.Lock)
#              y corte de caja automatico 24/7.
# ============================================================

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import BaseModel, Field
import pandas as pd
import polars as pl
import os
from datetime import datetime
import asyncio

# ============================================================
# LOCK GLOBAL (protege secciones criticas: compra y corte)
# ============================================================
lock = asyncio.Lock()

# ============================================================
# RUTAS DE ARCHIVOS
# ============================================================
ruta_actual = os.path.dirname(os.path.abspath(__file__))
ruta_productos = os.path.join(ruta_actual, "productos.csv")
ruta_ventas = os.path.join(ruta_actual, "ventas.csv")
ruta_parquet = os.path.join(ruta_actual, "ventas.parquet")

# ============================================================
# SCHEDULER + CORTE DE CAJA
# ============================================================
scheduler = AsyncIOScheduler()


async def ejecutar_corte_de_caja():
    """
    Corte de caja automatico:
      1. Lee ventas.csv del turno (si hay registros nuevos).
      2. Fusiona con ventas.parquet y guarda en disco.
      3. Vacia ventas.csv dejando solo los encabezados.
    Protegido con async with lock para no chocar con compras en curso.
    """
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] INICIANDO CORTE DE CAJA AUTOMATICO...")

    async with lock:
        try:
            # 1) Verificar que exista y tenga datos (mas de 50 bytes = header + algo)
            if not os.path.exists(ruta_ventas) or os.path.getsize(ruta_ventas) < 50:
                print("No hay ventas nuevas en el CSV para procesar.")
                return

            # 2) Leer el CSV del turno
            df_dia = pl.read_csv(ruta_ventas, infer_schema_length=10000)

            # 3) Fusionar con el historico Parquet (si existe)
            if os.path.exists(ruta_parquet):
                df_historico = pl.read_parquet(ruta_parquet)
                df_final = pl.concat([df_historico, df_dia], how="diagonal_relaxed")
            else:
                df_final = df_dia

            # 4) Escribir el nuevo Parquet comprimido
            df_final.write_parquet(ruta_parquet, compression="zstd")

            # 5) Vaciar ventas.csv (solo encabezados)
            df_dia.clear().write_csv(ruta_ventas)

            print(f"Corte exitoso. {len(df_dia)} ventas archivadas. CSV limpio.")
        except Exception as e:
            print(f"Error en el corte de caja: {e}")


# ============================================================
# LIFESPAN (arranque / apagado del servidor)
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Intervalo de 2 minutos para demostracion en clase.
    # En produccion: CronTrigger(hour=23, minute=59)
    scheduler.add_job(ejecutar_corte_de_caja, "interval", minutes=2) #2min demo clase ///hours=12
    scheduler.start()
    yield
    scheduler.shutdown()


# ============================================================
# APP + CORS
# ============================================================
app = FastAPI(
    title="TrendMode MX - Tiendita 24/7",
    description="API REST con Polars, Parquet y Corte de Caja automatico.",
    version="4.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# MODELOS PYDANTIC
# ============================================================
class CrearProducto(BaseModel):
    nombre: str = Field(..., min_length=1)
    precio: float = Field(..., gt=0)
    cantidad: int = Field(..., ge=0)
    categoria: str = Field(default="General")


class RespuestaProducto(BaseModel):
    id: int
    nombre: str
    precio: float
    cantidad: int
    categoria: str


# ============================================================
# HELPERS
# ============================================================
COLUMNAS_PRODUCTOS = ["id", "nombre", "precio", "cantidad", "categoria"]


def leer_productos_seguro() -> pd.DataFrame:
    """Lee productos.csv con tolerancia a fallos (si esta corrupto lo recrea)."""
    if not os.path.exists(ruta_productos) or os.path.getsize(ruta_productos) == 0:
        df = pd.DataFrame(columns=COLUMNAS_PRODUCTOS)
        df.to_csv(ruta_productos, index=False, encoding="utf-8")
        return df
    try:
        df = pd.read_csv(ruta_productos, dtype=str, encoding="utf-8")
        df.columns = df.columns.str.strip()
        if "id" not in df.columns or "nombre" not in df.columns:
            raise ValueError("Columnas incorrectas")
        return df
    except Exception:
        df = pd.DataFrame(columns=COLUMNAS_PRODUCTOS)
        df.to_csv(ruta_productos, index=False, encoding="utf-8")
        return df


def obtener_lazy_ventas():
    """
    Devuelve un LazyFrame de Polars que concatena:
      - ventas.parquet (historico)
      - ventas.csv    (ventas del turno actual)
    Se hace 'union virtual' en memoria: no se reescribe el Parquet.
    """
    fuentes = []

    if os.path.exists(ruta_parquet):
        pq_lf = pl.scan_parquet(ruta_parquet).with_columns([
            pl.col("Cantidad").cast(pl.Int64),
            pl.col("Precio_Unitario").cast(pl.Float64),
            pl.col("Total_Venta").cast(pl.Float64),
            pl.col("Descuento").cast(pl.Float64),
            pl.col("Cliente_Frecuente").cast(pl.Utf8),
        ])
        fuentes.append(pq_lf)

    if os.path.exists(ruta_ventas):
        with open(ruta_ventas, encoding="utf-8") as f:
            if sum(1 for _ in f) > 1:  # header + al menos 1 fila
                csv_lf = pl.scan_csv(ruta_ventas, infer_schema_length=10000).with_columns([
                    pl.col("Cantidad").cast(pl.Int64),
                    pl.col("Precio_Unitario").cast(pl.Float64),
                    pl.col("Total_Venta").cast(pl.Float64),
                    pl.col("Descuento").cast(pl.Float64),
                    pl.col("Cliente_Frecuente").cast(pl.Utf8),
                ])
                fuentes.append(csv_lf)

    if fuentes:
        return pl.concat(fuentes, how="diagonal_relaxed")
    return None


# ============================================================
# ENDPOINTS DE PRODUCTOS (CSV)
# ============================================================
@app.get("/productos")
async def getProductos():
    try:
        df = leer_productos_seguro()
        if df.empty:
            return []
        df["precio"] = pd.to_numeric(df["precio"], errors="coerce").fillna(0)
        df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0).astype(int)
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error GET productos: {e}")
        return []


@app.post("/productos", response_model=RespuestaProducto, status_code=status.HTTP_201_CREATED)
async def addProducto(producto: CrearProducto):
    try:
        df = leer_productos_seguro()
        nuevo_id = int(pd.to_numeric(df["id"], errors="coerce").max() + 1) if not df.empty else 1

        nuevo_producto = {
            "id": nuevo_id,
            "nombre": producto.nombre.strip(),
            "precio": producto.precio,
            "cantidad": producto.cantidad,
            "categoria": producto.categoria.strip(),
        }
        df_nuevo = pd.DataFrame([nuevo_producto])
        df_final = pd.concat([df, df_nuevo], ignore_index=True)
        df_final.to_csv(ruta_productos, index=False, encoding="utf-8")
        return nuevo_producto
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/productos/{producto_id}/comprar", response_model=RespuestaProducto)
async def comprarProducto(producto_id: int, cantidad_comprada: int):
    """
    Compra protegida con asyncio.Lock() para evitar condiciones de carrera
    (dos clientes comprando el mismo producto al mismo tiempo).
    """
    async with lock:
        try:
            df = leer_productos_seguro()
            df["id_num"] = pd.to_numeric(df["id"], errors="coerce")
            index = df.index[df["id_num"] == producto_id].tolist()
            if not index:
                raise HTTPException(status_code=404, detail="Producto no encontrado")

            i = index[0]
            stock_actual = int(pd.to_numeric(df.at[i, "cantidad"], errors="coerce"))
            precio_actual = float(pd.to_numeric(df.at[i, "precio"], errors="coerce"))

            if stock_actual < cantidad_comprada:
                raise HTTPException(status_code=400, detail="No hay suficiente stock")

            # Descontar stock y guardar productos.csv
            df.at[i, "cantidad"] = stock_actual - cantidad_comprada
            df = df.drop(columns=["id_num"])
            df.to_csv(ruta_productos, index=False, encoding="utf-8")

            # Registrar la venta en ventas.csv (append)
            timestamp_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            fecha_actual = datetime.now().strftime("%d/%m/%Y")

            nueva_venta = {
                "ID_Venta": f"WEB_{timestamp_id}",
                "Fecha": fecha_actual,
                "Tienda": "Tienda_Online",
                "Producto": str(df.at[i, "nombre"]).strip(),
                "Categoria": str(df.at[i, "categoria"]).strip(),
                "Cantidad": cantidad_comprada,
                "Precio_Unitario": precio_actual,
                "Total_Venta": precio_actual * cantidad_comprada,
                "Talla": "N/A",
                "Descuento": 0.0,
                "Metodo_Pago": "Web",
                "Cliente_Frecuente": "FALSE",
            }

            archivo_existe = os.path.exists(ruta_ventas)
            df_venta = pd.DataFrame([nueva_venta])
            if archivo_existe:
                columnas_originales = pd.read_csv(ruta_ventas, nrows=0, encoding="utf-8").columns.tolist()
                df_venta = df_venta.reindex(columns=columnas_originales, fill_value="")

            df_venta.to_csv(
                ruta_ventas,
                mode="a",
                header=not archivo_existe,
                index=False,
                encoding="utf-8",
            )

            return {
                "id": producto_id,
                "nombre": str(df.at[i, "nombre"]),
                "precio": precio_actual,
                "cantidad": stock_actual - cantidad_comprada,
                "categoria": str(df.at[i, "categoria"]),
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.delete("/productos/{producto_id}")
async def deleteProducto(producto_id: int):
    try:
        df = leer_productos_seguro()
        df["id_num"] = pd.to_numeric(df["id"], errors="coerce")
        if producto_id not in df["id_num"].values:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        df = df[df["id_num"] != producto_id]
        df = df.drop(columns=["id_num"])
        df.to_csv(ruta_productos, index=False, encoding="utf-8")
        return {"Message": f"Producto {producto_id} eliminado"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINTS ANALITICOS (POLARS + LAZY + PARQUET + CSV)
# Se exponen con doble ruta: /api/analisis/... (spec PDF) y alias corto.
# ============================================================

@app.get("/api/analisis/kpis")
@app.get("/kpis")
async def get_kpis():
    lf = obtener_lazy_ventas()
    if lf is None:
        return {"ingresos_totales": 0, "transacciones": 0, "producto_estrella": "N/A"}

    try:
        resumen = lf.select([
            pl.col("Total_Venta").sum().alias("ingresos"),
            pl.len().alias("transacciones"),
        ]).collect()

        top_prod = (
            lf.group_by("Producto")
            .agg(pl.col("Total_Venta").sum())
            .sort("Total_Venta", descending=True)
            .limit(1)
            .collect()
        )
        producto_estrella = top_prod["Producto"][0] if not top_prod.is_empty() else "N/A"

        return {
            "ingresos_totales": float(resumen["ingresos"][0]) if resumen["ingresos"][0] is not None else 0,
            "transacciones": int(resumen["transacciones"][0]),
            "producto_estrella": producto_estrella,
        }
    except Exception as e:
        print(f"Error KPIs: {e}")
        return {"ingresos_totales": 0, "transacciones": 0, "producto_estrella": "N/A"}


@app.get("/api/analisis/mas-vendidos")
@app.get("/ventas-por-producto")
async def get_ventas_por_producto():
    lf = obtener_lazy_ventas()
    if lf is None:
        return []

    try:
        df_agrupado = (
            lf.group_by("Producto")
            .agg(pl.col("Total_Venta").sum())
            .sort("Total_Venta", descending=True)
            .limit(10)
            .collect()
        )
        return df_agrupado.to_dicts()
    except Exception as e:
        print(f"Error grafico productos: {e}")
        return []


@app.get("/api/analisis/ventas-por-fecha")
@app.get("/ventas-por-fecha")
async def get_ventas_por_fecha():
    lf = obtener_lazy_ventas()
    if lf is None:
        return []

    try:
        df_agrupado = (
            lf.group_by("Fecha")
            .agg(pl.col("Total_Venta").sum())
            .sort("Fecha")
            .collect()
        )
        res = df_agrupado.to_dicts()
        return res[-30:] if len(res) > 30 else res
    except Exception as e:
        print(f"Error grafico fechas: {e}")
        return []

@app.get("/forzar-corte")
async def forzar_corte():
    await ejecutar_corte_de_caja()
    return {"mensaje": "Corte de caja ejecutado manualmente"}



# ============================================================
# EJECUCION
# uvicorn main:app --reload
# ============================================================
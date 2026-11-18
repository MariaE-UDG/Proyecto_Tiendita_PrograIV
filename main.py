# ENCABEZADO
'''
Titulo: Tiendita Full-Stack
Autor: Esther Bautista
Fecha de creación: 2026-11-18
Descripción: Persistencia en CSV, API con Pandas y Dashboard Chart.js
'''
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import os
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- RUTAS DE ARCHIVOS ---
ruta_actual = os.path.dirname(os.path.abspath(__file__))
ruta_productos = os.path.join(ruta_actual, 'productos.csv')
ruta_ventas = os.path.join(ruta_actual, 'ventas.csv')

# --- FUNCIÓN AUXILIAR PARA LEER PRODUCTOS (A PRUEBA DE BALAS) ---
def leer_productos_seguro():
    # Si no existe o está vacío, creamos el esqueleto
    if not os.path.exists(ruta_productos) or os.path.getsize(ruta_productos) == 0:
        df = pd.DataFrame(columns=["id", "nombre", "precio", "cantidad", "categoria"])
        df.to_csv(ruta_productos, index=False, encoding='utf-8')
        return df
    
    try:
        # Leemos forzando a que todo sea string primero
        df = pd.read_csv(ruta_productos, dtype=str, encoding='utf-8')
        
        # Limpiamos los nombres de las columnas (quitamos espacios en blanco invisibles)
        df.columns = df.columns.str.strip()
        
        # Verificamos que las columnas vitales existan
        if 'id' not in df.columns or 'nombre' not in df.columns:
            raise ValueError("Columnas incorrectas")
            
        return df
    except Exception as e:
        print(f"⚠️ Archivo corrupto, reiniciando... {e}")
        df = pd.DataFrame(columns=["id", "nombre", "precio", "cantidad", "categoria"])
        df.to_csv(ruta_productos, index=False, encoding='utf-8')
        return df

# Modelos de Pydantic
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
# ENDPOINTS DE PRODUCTOS (CSV)
# ============================================================

@app.get("/productos")
async def getProductos():
    try:
        df = leer_productos_seguro()
        if df.empty:
            return []
        
        # Convertimos los tipos numéricos de forma segura
        df['precio'] = pd.to_numeric(df['precio'], errors='coerce').fillna(0)
        df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0).astype(int)
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error en GET productos: {e}")
        return []

@app.post("/productos", response_model=RespuestaProducto, status_code=status.HTTP_201_CREATED)
async def addProducto(producto: CrearProducto):
    try:
        df = leer_productos_seguro()
        
        # Calculamos el nuevo ID
        if df.empty:
            nuevo_id = 1
        else:
            # Extraemos IDs válidos y buscamos el mayor
            ids_validos = pd.to_numeric(df['id'], errors='coerce').dropna()
            nuevo_id = int(ids_validos.max() + 1) if not ids_validos.empty else 1
        
        nuevo_producto = {
            "id": nuevo_id,
            "nombre": producto.nombre.strip(),
            "precio": producto.precio,
            "cantidad": producto.cantidad,
            "categoria": producto.categoria.strip()
        }
        
        # En lugar de hacer un append ciego, reescribimos el DataFrame completo
        # Esto asegura que las columnas siempre queden perfectamente alineadas
        df_nuevo = pd.DataFrame([nuevo_producto])
        df_final = pd.concat([df, df_nuevo], ignore_index=True)
        
        # Guardamos todo el archivo de nuevo, limpio
        df_final.to_csv(ruta_productos, index=False, encoding='utf-8')
        
        return nuevo_producto
    except Exception as e:
        print(f"Error en POST productos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/productos/{producto_id}/comprar", response_model=RespuestaProducto)
async def comprarProducto(producto_id: int, cantidad_comprada: int):
    try:
        df = leer_productos_seguro()
        
        # Convertimos el id a número para comparar
        df['id_num'] = pd.to_numeric(df['id'], errors='coerce')
        index = df.index[df['id_num'] == producto_id].tolist()
        
        if not index:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        i = index[0]
        
        stock_actual = int(pd.to_numeric(df.at[i, 'cantidad'], errors='coerce'))
        precio_actual = float(pd.to_numeric(df.at[i, 'precio'], errors='coerce'))
        
        if stock_actual < cantidad_comprada:
            raise HTTPException(status_code=400, detail="No hay suficiente stock")
        
        # 1. Restar stock
        df.at[i, 'cantidad'] = stock_actual - cantidad_comprada
        df = df.drop(columns=['id_num']) # Limpiamos la columna temporal
        df.to_csv(ruta_productos, index=False, encoding='utf-8')
        
        # 2. Registrar venta
        timestamp_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        fecha_actual = datetime.now().strftime('%d/%m/%Y')
        
        nueva_venta = {
            'ID_Venta': f'WEB_{timestamp_id}',
            'Fecha': fecha_actual,
            'Tienda': 'Tienda_Online',
            'Producto': str(df.at[i, 'nombre']).strip(),
            'Categoria': str(df.at[i, 'categoria']).strip(),
            'Cantidad': cantidad_comprada,
            'Precio_Unitario': precio_actual,
            'Total_Venta': precio_actual * cantidad_comprada,
            'Talla': 'N/A',
            'Descuento': 0.0,
            'Metodo_Pago': 'Web',
            'Cliente_Frecuente': 'FALSE'
        }
        
        archivo_existe = os.path.exists(ruta_ventas)
        df_venta = pd.DataFrame([nueva_venta])
        
        if archivo_existe:
            columnas_originales = pd.read_csv(ruta_ventas, nrows=0, encoding='utf-8').columns.tolist()
            df_venta = df_venta.reindex(columns=columnas_originales, fill_value="")
            
        df_venta.to_csv(ruta_ventas, mode='a', header=not archivo_existe, index=False, encoding='utf-8')
        
        return {
            "id": producto_id,
            "nombre": str(df.at[i, 'nombre']),
            "precio": precio_actual,
            "cantidad": stock_actual - cantidad_comprada,
            "categoria": str(df.at[i, 'categoria'])
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error en PUT comprar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/productos/{producto_id}")
async def deleteProducto(producto_id: int):
    try:
        df = leer_productos_seguro()
        
        df['id_num'] = pd.to_numeric(df['id'], errors='coerce')
        if producto_id not in df['id_num'].values:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        df = df[df['id_num'] != producto_id]
        df = df.drop(columns=['id_num'])
        
        df.to_csv(ruta_productos, index=False, encoding='utf-8')
        return {"Message": f"Producto {producto_id} eliminado"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# ENDPOINTS ANALÍTICOS (DASHBOARD)
# ============================================================

@app.get("/kpis")
async def get_kpis():
    try:
        if not os.path.exists(ruta_ventas):
            return {"ingresos_totales": 0, "transacciones": 0, "producto_estrella": "N/A"}
            
        df = pd.read_csv(ruta_ventas, encoding='utf-8')
        df.columns = df.columns.str.strip()
        
        if df.empty:
            return {"ingresos_totales": 0, "transacciones": 0, "producto_estrella": "N/A"}
        
        ingresos = float(df['Total_Venta'].sum())
        transacciones = int(len(df))
        
        ventas_por_producto = df.groupby('Producto')['Cantidad'].sum()
        producto_estrella = ventas_por_producto.idxmax() if not ventas_por_producto.empty else "N/A"
        
        return {
            "ingresos_totales": ingresos,
            "transacciones": transacciones,
            "producto_estrella": producto_estrella
        }
    except Exception as e:
        print("Error KPIs:", e)
        return {"ingresos_totales": 0, "transacciones": 0, "producto_estrella": "N/A"}

@app.get("/ventas-por-producto")
async def get_ventas_por_producto():
    try:
        if not os.path.exists(ruta_ventas):
            return []
        df = pd.read_csv(ruta_ventas, encoding='utf-8')
        df.columns = df.columns.str.strip()
        
        ventas = df.groupby('Producto')['Total_Venta'].sum().reset_index()
        ventas = ventas.sort_values(by='Total_Venta', ascending=False)
        return ventas.to_dict(orient="records")
    except Exception:
        return []

@app.get("/ventas-por-fecha")
async def get_ventas_por_fecha():
    try:
        if not os.path.exists(ruta_ventas):
            return []
        df = pd.read_csv(ruta_ventas, encoding='utf-8')
        df.columns = df.columns.str.strip()
        
        df['Fecha_DT'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y', errors='coerce')
        df = df.dropna(subset=['Fecha_DT'])
        
        ventas = df.groupby('Fecha_DT')['Total_Venta'].sum().reset_index()
        ventas = ventas.sort_values(by='Fecha_DT')
        
        ventas['Fecha'] = ventas['Fecha_DT'].dt.strftime('%d/%m/%Y')
        return ventas[['Fecha', 'Total_Venta']].to_dict(orient="records")
    except Exception:
        return []
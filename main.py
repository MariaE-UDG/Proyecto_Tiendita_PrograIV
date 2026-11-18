# ENCABEZADO
# ENCABEZADO
'''
Titulo: Tiendita
Autor: Esther Bautista
Fecha de creación: 2026-11-04
Descripción: Actualización del proyecto Tiendita con persistencia JSON.
'''
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from pydantic import BaseModel, Field
import pandas as pd
import os
import json # <-- Nueva librería para el JSON
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
ruta_csv = os.path.join(ruta_actual, 'ventas_trendmode.csv')
ruta_json = os.path.join(ruta_actual, 'inventario.json') # <-- Ruta del nuevo JSON

# --- LÓGICA DE PERSISTENCIA DEL INVENTARIO (JSON) ---
def cargar_inventario():
    if os.path.exists(ruta_json):
        with open(ruta_json, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Inventario inicial (si el JSON no existe, se crea con estos datos)
        inventario_inicial = [
            {"id": 1, "nombre": "Pantalón Mezclilla", "precio": 699.0, "cantidad": 50, "categoria": "Pantalones"},
            {"id": 2, "nombre": "Chaqueta Cuero", "precio": 1299.0, "cantidad": 20, "categoria": "Chaquetas"},
            {"id": 3, "nombre": "Vestido Floral", "precio": 899.0, "cantidad": 30, "categoria": "Vestidos"},
            {"id": 4, "nombre": "Camisa Blanca", "precio": 399.0, "cantidad": 60, "categoria": "Camisas"}
        ]
        guardar_inventario(inventario_inicial)
        return inventario_inicial

def guardar_inventario(datos):
    with open(ruta_json, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

# Inicializamos el inventario desde el JSON
inventario = cargar_inventario()

# Modelos de Pydantic
class CrearProducto(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre del producto")
    precio: float = Field(..., gt=0, description="Precio del producto")
    cantidad: int = Field(..., ge=0, description="Cantidad del producto")
    # Nota: No puse 'categoria' en el modelo porque el HTML actual no lo pide.
    # Si luego agregas un <select> en el HTML, puedes agregarlo aquí.

class RespuestaProducto(BaseModel):
    id: int
    nombre: str
    precio: float
    cantidad: int
    categoria: str = "Compra_Web" # Valor por defecto por si acaso

# Función auxiliar para simular latencia
async def simular_conexion_db(segundos: float = 0.5):
    await asyncio.sleep(segundos)

# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
async def home():
    return {"Message": "API de TrendMode MX funcionando correctamente"}

@app.get("/ventas-por-categoria")
async def get_ventas_por_categoria():
    try:
        df = pd.read_csv(ruta_csv, encoding='utf-8')
        ventas = df.groupby('Categoria')['Total_Venta'].sum().reset_index()
        return ventas.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/productos")
async def getProductos():
    await simular_conexion_db(0.5)
    return inventario

@app.post("/productos", response_model=RespuestaProducto, status_code=status.HTTP_201_CREATED)
async def addProducto(producto: CrearProducto):
    try:
        await simular_conexion_db(0.5)
        nuevo_id = max((p["id"] for p in inventario), default=0) + 1
        nuevo_producto = {
            "id": nuevo_id,    
            "nombre": producto.nombre,
            "precio": producto.precio,
            "cantidad": producto.cantidad,
            "categoria": "Compra_Web" # Como el form no pide categoría, le ponemos esta por defecto
        }
        inventario.append(nuevo_producto)
        guardar_inventario(inventario) # <-- GUARDAMOS EN EL JSON
        return nuevo_producto
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error en la base de datos: {str(error)}"
        )

@app.put("/productos/{producto_id}/comprar", response_model=RespuestaProducto)
async def comprarProducto(producto_id: int, cantidad_comprada: int):
    try:
        await simular_conexion_db(0.5)
        
        for producto in inventario:
            if producto["id"] == producto_id:
                if producto["cantidad"] < cantidad_comprada:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No hay suficiente stock disponible"
                    )
                
                # 1. Restamos el stock en memoria
                producto["cantidad"] -= cantidad_comprada
                
                # 2. PERSISTENCIA: Guardamos la venta en el CSV
                try:
                    timestamp_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    fecha_actual = datetime.now().strftime('%d/%m/%Y')
                    
                    nueva_venta = {
                        'ID_Venta': f'WEB_{timestamp_id}',
                        'Fecha': fecha_actual,
                        'Tienda': 'Tienda_Online',
                        'Producto': producto["nombre"],
                        'Categoria': producto.get("categoria", "Compra_Web"), # <-- Usa la categoría real
                        'Talla': 'N/A',
                        'Cantidad': cantidad_comprada,
                        'Precio_Unitario': producto["precio"],
                        'Descuento': 0.0,
                        'Total_Venta': producto["precio"] * cantidad_comprada,
                        'Metodo_Pago': 'Web',
                        'Cliente_Frecuente': False
                    }
                    
                    df_nueva_venta = pd.DataFrame([nueva_venta])
                    df_nueva_venta.to_csv(ruta_csv, mode='a', header=False, index=False, encoding='utf-8')
                    
                    print(f"✅ Venta guardada en CSV con ID: {timestamp_id}")
                    
                except Exception as e:
                    print(f"⚠️ Error al guardar en el CSV: {e}")
                
                # 3. GUARDAMOS EL NUEVO STOCK EN EL JSON
                guardar_inventario(inventario) 
                
                return producto
                
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="El producto no fue encontrado"
        )
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error al comprar: {str(e)}"
        )

@app.delete("/productos/{producto_id}")
async def deleteProducto(producto_id: int):
    try:
        await simular_conexion_db(0.5)
        for producto in inventario:
            if producto["id"] == producto_id:
                inventario.remove(producto)
                guardar_inventario(inventario) # <-- GUARDAMOS LA ELIMINACIÓN EN EL JSON
                return {"Message": f"El producto {producto_id} fue eliminado"}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="El producto no fue encontrado"
        )
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error al eliminar: {str(e)}"
        )
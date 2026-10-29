# ENCABEZADO
'''
Titulo: Tiendita
Autor: Esther Bautista
Fecha de creación: 28 de octubre de 2026
Descripción: Integracion de LOCUST al proyecto Tiendita. 

EJECUTAR CON: "uvicorn main:app --reload"
NAVEGADOR: http://localhost:8089

'''
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from pydantic import BaseModel, Field

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Base de datos simulada en memoria
inventario = [
    {"id": 1, "nombre": "Coca-Cola", "precio": 20.0, "cantidad": 25},
    {"id": 2, "nombre": "Papas", "precio": 15.0, "cantidad": 40},
    {"id": 3, "nombre": "Café", "precio": 18.0, "cantidad": 15}
]

# Modelos de Pydantic
class CrearProducto(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre del producto")
    precio: float = Field(..., gt=0, description="Precio del producto")
    cantidad: int = Field(..., ge=0, description="Cantidad del producto")

class RespuestaProducto(BaseModel):
    id: int
    nombre: str
    precio: float
    cantidad: int

# Función auxiliar para simular la latencia de una Base de Datos real
async def simular_conexion_db(segundos: float = 0.5):
    await asyncio.sleep(segundos)

# ============================================================
# ENDPOINTS REFACTORIZADOS (PROFESIONALES + ASÍNCRONOS)
# ============================================================

@app.get("/")
async def home():
    return {"Message": "Hola bienvenido a la tiendita asíncrona"}

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
            "cantidad": producto.cantidad
        }
        inventario.append(nuevo_producto)
        return nuevo_producto
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error en la base de datos: {str(error)}"
        )

# NUEVO ENDPOINT: Para comprar (restar stock)
# Declaramos el Lock justo arriba del endpoint o debajo de app = FastAPI()
lock = asyncio.Lock()

@app.put("/productos/{producto_id}/comprar", response_model=RespuestaProducto)
async def comprarProducto(producto_id: int, cantidad_comprada: int):
    try:
        # EXPERIMENTO A: Comenta la línea de abajo ('async with lock:') para romper la API
        # EXPERIMENTO B: Descomenta la línea de abajo para proteger la API
        # async with lock: 

        await simular_conexion_db(0.5)
        
        for producto in inventario:
            if producto["id"] == producto_id:
                if producto["cantidad"] < cantidad_comprada:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No hay suficiente stock disponible"
                    )
                
                producto["cantidad"] -= cantidad_comprada
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

    
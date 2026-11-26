# generar_parquet.py

import polars as pl
import numpy as np
from datetime import datetime, timedelta
import random

# 1. Definimos un catálogo más grande y variado
productos = [
    "Pantalon Mezclilla", "Chaqueta Cuero", "Vestido Floral", "Camisa Blanca", 
    "Vestido Liso", "Zapatos Piel", "Sudadera Oversize", "Falda Plisada", 
    "Blusa Seda", "Bufanda Lana", "Cinturon Cuero", "Playera Basica", 
    "Shorts Denim", "Chamarra Gala", "Top Deportivo", "Gorra Snapback", 
    "Calcetines", "Bolsa Piel", "Falda Corta", "Sueter Tejido"
]

# Diccionario de precios realistas
precios = {
    "Pantalon Mezclilla": 699.0, "Chaqueta Cuero": 1299.0, "Vestido Floral": 899.0, 
    "Camisa Blanca": 399.0, "Vestido Liso": 1000.0, "Zapatos Piel": 999.0, 
    "Sudadera Oversize": 699.0, "Falda Plisada": 599.0, "Blusa Seda": 499.0, 
    "Bufanda Lana": 299.0, "Cinturon Cuero": 349.0, "Playera Basica": 199.0, 
    "Shorts Denim": 449.0, "Chamarra Gala": 1599.0, "Top Deportivo": 299.0, 
    "Gorra Snapback": 249.0, "Calcetines": 99.0, "Bolsa Piel": 899.0, 
    "Falda Corta": 399.0, "Sueter Tejido": 599.0
}

# Categorías correspondientes
categorias = {
    "Pantalon Mezclilla": "Pantalones", "Chaqueta Cuero": "Chaquetas", "Vestido Floral": "Vestidos", 
    "Camisa Blanca": "Camisas", "Vestido Liso": "Vestidos", "Zapatos Piel": "Calzado", 
    "Sudadera Oversize": "Sudaderas", "Falda Plisada": "Faldas", "Blusa Seda": "Blusas", 
    "Bufanda Lana": "Accesorios", "Cinturon Cuero": "Accesorios", "Playera Basica": "Camisas", 
    "Shorts Denim": "Shorts", "Chamarra Gala": "Chaquetas", "Top Deportivo": "Tops", 
    "Gorra Snapback": "Accesorios", "Calcetines": "Accesorios", "Bolsa Piel": "Accesorios", 
    "Falda Corta": "Faldas", "Sueter Tejido": "Sueteres"
}

N = 2_000_000
print(f"⏳ Generando {N} registros con 20 productos distintos...")

# 2. Generación aleatoria con NumPy
prod_elegidos = np.random.choice(productos, size=N)
cantidades = np.random.randint(1, 6, N)
precios_arr = np.array([precios[p] for p in prod_elegidos])
cat_arr = np.array([categorias[p] for p in prod_elegidos])

hoy = datetime.now()
fechas = [ (hoy - timedelta(days=random.randint(1, 730))).strftime('%d/%m/%Y') for _ in range(N) ]

# 3. Creación del DataFrame con Polars
df = pl.DataFrame({
    "ID_Venta": [f"HIST_{i}" for i in range(1, N + 1)],
    "Fecha": fechas,
    "Tienda": np.random.choice(["CDMX_Polanco", "GDL_Andares", "MTY_SanPedro", "Online"], N),
    "Producto": prod_elegidos,
    "Categoria": cat_arr,
    "Talla": np.random.choice(["S", "M", "L", "XL", "N/A"], N),
    "Cantidad": cantidades,
    "Precio_Unitario": precios_arr,
    "Descuento": 0.0,
    "Total_Venta": precios_arr * cantidades,
    "Metodo_Pago": np.random.choice(["Efectivo", "Tarjeta", "Transferencia", "Web"], N),
    "Cliente_Frecuente": np.random.choice(["TRUE", "FALSE"], N)
})

df.write_parquet("ventas.parquet")
print("✅ ¡Archivo 'ventas.parquet' regenerado con 20 productos distintos!")
const API_URL = "http://127.0.0.1:8000/productos";

// Selección de Elementos del DOM
const formProducto = document.getElementById("formProducto");
const tablaProductos = document.getElementById("tablaProductos");
const totalProductos = document.getElementById("totalProductos");

// Instancia global del gráfico (para poder destruirlo y recrearlo)
let graficoVentasInstance = null;


// 1. Función para Cargar Productos (GET)
async function cargarProductos() {
    try {
        const respuesta = await fetch(API_URL);
        const productos = await respuesta.json();

        tablaProductos.innerHTML = "";
        totalProductos.textContent = `${productos.length} productos`;

        if (productos.length === 0) {
            tablaProductos.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted py-5">
                        No hay productos registrados en la tiendita.
                    </td>
                </tr>`;
            return;
        }

        productos.forEach(p => {
            // Lógica de colores para el badge (igual que antes)
            const badgeClass = p.cantidad < 10 ? 'bg-stock-low' : 'bg-stock-ok';
            
            const fila = document.createElement("tr");
            fila.innerHTML = `
                <td class="ps-4 fw-bold text-secondary">#${p.id}</td>
                <td class="fw-medium text-dark">${p.nombre}</td>
                <td class="text-dark">$${p.precio}</td>
                <td>
                    <span class="badge badge-stock ${badgeClass}">
                        ${p.cantidad} unidades
                    </span>
                </td>
                <td class="text-end pe-4">
                    <!-- Botón COMPRAR (Azul) -->
                    <button class="btn btn-action btn-outline-blue me-1" onclick="comprarProducto(${p.id}, '${p.nombre}')">
                        Comprar
                    </button>
                    <!-- Botón Eliminar (Rojo) -->
                    <button class="btn btn-action btn-outline-red" onclick="eliminarProducto(${p.id})">
                        Eliminar
                    </button>
                </td>
            `;
            tablaProductos.appendChild(fila);
        });

    } catch (error) {
        console.error("Error al cargar productos:", error);
    }
}

// 2. Función para Agregar Producto (POST) - Sin cambios, solo limpieza
async function agregarProducto(event){
    event.preventDefault();

    const nombre = document.getElementById("nombre").value;
    const precio = document.getElementById("precio").value;
    const cantidad = document.getElementById("cantidad").value;

    const nuevoContenido = { nombre, precio, cantidad };
    
    try {
        const respuesta = await fetch(API_URL, {
            method: "POST", 
            headers: {"Content-Type": "application/json"}, 
            body: JSON.stringify(nuevoContenido)
        });

        if(respuesta.ok){
            formProducto.reset();
            await cargarProductos();
        } else {
            console.error("Hubo un error al guardar el producto");
        }
    } catch (error) {
        console.log(error);
    }
}

// 3. NUEVA FUNCIÓN: Comprar Producto (PUT)

// 3. NUEVA FUNCIÓN: Comprar Producto (PUT)
async function comprarProducto(id_producto, nombre_producto) {
    // Usamos prompt para pedir la cantidad de forma rápida y limpia
    const cantidadInput = prompt(`¿Cuántas unidades de "${nombre_producto}" deseas comprar?`, "1");
    
    // Si el usuario cancela o no ingresa nada, salimos
    if (cantidadInput === null || cantidadInput.trim() === "") return;

    const cantidad = parseInt(cantidadInput);

    // Validación básica en el frontend
    if (isNaN(cantidad) || cantidad <= 0) {
        alert("Por favor, ingresa un número válido mayor a 0.");
        return;
    }

    try {
        // Hacemos la petición PUT al endpoint específico de compra
        const respuesta = await fetch(`${API_URL}/${id_producto}/comprar?cantidad_comprada=${cantidad}`, {
            method: "PUT",
            headers: {"Content-Type": "application/json"}
        });

        if (respuesta.ok) {
            // Si todo sale bien, recargamos la tabla para ver el nuevo stock
            await cargarProductos();
            // 👇 Recargamos también el gráfico (ya refleja la nueva venta del CSV)
            await cargarGrafico();
            alert(`¡Compra exitosa! Se compraron ${cantidad} unidades de ${nombre_producto}.`);
        } else {
            // Si el backend devuelve error (ej. no hay stock), mostramos el mensaje
            const errorData = await respuesta.json();
            alert(`Error: ${errorData.detail || "No se pudo realizar la compra"}`);
        }
    } catch (error) {
        console.error("Error al conectar con el servidor:", error);
        alert("Hubo un problema de conexión al intentar comprar.");
    }
}


// 4. Función para Eliminar Producto (DELETE)
async function eliminarProducto(id_producto){
    if(!confirm("¿Estás seguro de eliminar este producto?")) return;

    try {
        const respuesta = await fetch(`${API_URL}/${id_producto}`, {
            method: "DELETE", 
            headers: {"Content-Type": "application/json"}
        });

        if(respuesta.ok){
            await cargarProductos();
        } else {
            console.error("Hubo un error al eliminar");
        }
    } catch (error) {
        console.log(error);
    }
}


// Evento para el formulario
formProducto.addEventListener("submit", agregarProducto);


// ==========================================
// LÓGICA PARA CHART.JS (TAREA EXTRA)
// ==========================================

async function cargarGrafico() {
    const canvas = document.getElementById('graficoVentas');
    if (!canvas) return;

    try {
        // Llamamos a nuestro nuevo endpoint
        const respuesta = await fetch("http://127.0.0.1:8000/ventas-por-categoria");
        const datos = await respuesta.json();

        // Preparamos las etiquetas (Categorías) y los datos (Totales)
        const etiquetas = datos.map(item => item.Categoria);
        const valores = datos.map(item => item.Total_Venta);

        // Configuración visual del gráfico
        const ctx = canvas.getContext('2d');

        // 👇 Destruimos el gráfico anterior si ya existía
        if (graficoVentasInstance) {
            graficoVentasInstance.destroy();
        }

        // 👇 Guardamos la nueva instancia en la variable global
        graficoVentasInstance = new Chart(ctx, {
            type: 'bar', // Tipo de gráfico: barras
            data: {
                labels: etiquetas,
                datasets: [{
                    label: 'Ventas Totales ($)',
                    data: valores,
                    backgroundColor: 'rgba(37, 99, 235, 0.7)', // Azul moderno (igual a tus botones)
                    borderColor: 'rgba(37, 99, 235, 1)',
                    borderWidth: 1,
                    borderRadius: 6 // Bordes redondeados en las barras
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false } // Ocultamos la leyenda porque solo hay un dataset
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + value; // Formato de moneda en el eje Y
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error("Error al cargar el gráfico:", error);
    }
}


// Modificamos el evento DOMContentLoaded para que cargue tabla y gráfico
document.addEventListener("DOMContentLoaded", () => {
    cargarProductos(); // Tu función original
    cargarGrafico();   // La nueva función de la tarea
});
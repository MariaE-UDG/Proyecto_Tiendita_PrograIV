const API_URL = "http://127.0.0.1:8000/productos";

const formProducto = document.getElementById("formProducto");
const tablaProductos = document.getElementById("tablaProductos");
const totalProductos = document.getElementById("totalProductos");

let graficoProductoInstance = null;
let graficoFechaInstance = null;

// Formateadores de números
const formatoMoneda = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' });
const formatoNumero = new Intl.NumberFormat('es-MX');

// 1. Cargar Productos
async function cargarProductos() {
    try {
        const respuesta = await fetch(API_URL);
        const productos = await respuesta.json();
        tablaProductos.innerHTML = "";
        totalProductos.textContent = `${productos.length} productos`;

        productos.forEach(p => {
            const badgeClass = p.cantidad < 10 ? 'bg-stock-low' : 'bg-stock-ok';
            const fila = document.createElement("tr");
            fila.innerHTML = `
                <td class="ps-4 fw-bold text-secondary">#${p.id}</td>
                <td class="fw-medium text-dark">${p.nombre}</td>
                <td>${formatoMoneda.format(p.precio)}</td>
                <td><span class="badge bg-secondary">${p.categoria}</span></td>
                <td><span class="badge badge-stock ${badgeClass}">${p.cantidad}</span></td>
                <td class="text-end pe-4">
                    <button class="btn btn-action btn-outline-primary me-1" onclick="comprarProducto(${p.id}, '${p.nombre}')">Comprar</button>
                    <button class="btn btn-action btn-outline-danger" onclick="eliminarProducto(${p.id})">Eliminar</button>
                </td>
            `;
            tablaProductos.appendChild(fila);
        });
    } catch (error) { console.error("Error al cargar productos:", error); }
}

// 2. Agregar Producto
async function agregarProducto(event) {
    event.preventDefault();
    const nuevoContenido = {
        nombre: document.getElementById("nombre").value,
        precio: parseFloat(document.getElementById("precio").value),
        cantidad: parseInt(document.getElementById("cantidad").value),
        categoria: document.getElementById("categoria").value
    };
    try {
        const respuesta = await fetch(API_URL, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(nuevoContenido)
        });
        if(respuesta.ok){
            formProducto.reset();
            await actualizarTodo();
        }
    } catch (error) { console.log(error); }
}

// 3. Comprar Producto
async function comprarProducto(id, nombre) {
    const cant = prompt(`¿Cuántas unidades de "${nombre}" deseas comprar?`, "1");
    if (!cant || isNaN(cant) || cant <= 0) return;
    
    try {
        const respuesta = await fetch(`${API_URL}/${id}/comprar?cantidad_comprada=${cant}`, {
            method: "PUT",
            headers: {"Content-Type": "application/json"}
        });
        if (respuesta.ok) {
            await actualizarTodo();
            alert(`Compra exitosa de ${cant} unidades.`);
        } else {
            const err = await respuesta.json();
            alert(`Error: ${err.detail}`);
        }
    } catch (error) { alert("Error de conexión"); }
}

// 4. Eliminar Producto
async function eliminarProducto(id) {
    if(!confirm("¿Seguro que deseas eliminar este producto del inventario?")) return;
    try {
        const respuesta = await fetch(`${API_URL}/${id}`, { method: "DELETE" });
        if(respuesta.ok){
            await actualizarTodo();
        }
    } catch (error) { console.log(error); }
}

// 5. Cargar KPIs (Tarjetas) con formato
async function cargarKPIs() {
    try {
        const respuesta = await fetch("http://127.0.0.1:8000/kpis");
        const datos = await respuesta.json();
        
        document.getElementById("kpiIngresos").textContent = formatoMoneda.format(datos.ingresos_totales);
        document.getElementById("kpiTransacciones").textContent = formatoNumero.format(datos.transacciones);
        document.getElementById("kpiProducto").textContent = datos.producto_estrella;
    } catch (error) { console.error("Error KPIs:", error); }
}

// 6. Gráficas (Productos y Fechas)
async function cargarGraficos() {
    try {
        // Gráfica 1 (Barras - Por producto)
        const resProd = await fetch("http://127.0.0.1:8000/ventas-por-producto");
        const datosProd = await resProd.json();
        const ctxProd = document.getElementById('graficoCategoria').getContext('2d');
        
        if (graficoProductoInstance) graficoProductoInstance.destroy();
        
        graficoProductoInstance = new Chart(ctxProd, {
            type: 'bar',
            data: {
                labels: datosProd.map(d => d.Producto), // Nombres exactos
                datasets: [{
                    label: 'Ingresos',
                    data: datosProd.map(d => d.Total_Venta),
                    backgroundColor: 'rgba(37, 99, 235, 0.7)',
                    borderRadius: 6
                }]
            },
            options: { 
                responsive: true, 
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) { return 'Ingresos: ' + formatoMoneda.format(context.raw); }
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            callback: function(value) { return '$' + formatoNumero.format(value); }
                        }
                    }
                }
            }
        });

        // Gráfica 2 (Líneas - Por fecha)
        const resFec = await fetch("http://127.0.0.1:8000/ventas-por-fecha");
        const datosFec = await resFec.json();
        const ctxFec = document.getElementById('graficoFecha').getContext('2d');
        
        if (graficoFechaInstance) graficoFechaInstance.destroy();
        
        graficoFechaInstance = new Chart(ctxFec, {
            type: 'line',
            data: {
                labels: datosFec.map(d => d.Fecha),
                datasets: [{
                    label: 'Ingresos por Día',
                    data: datosFec.map(d => d.Total_Venta),
                    backgroundColor: 'rgba(220, 53, 69, 0.2)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                }]
            },
            options: { 
                responsive: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) { return 'Ingresos: ' + formatoMoneda.format(context.raw); }
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            callback: function(value) { return '$' + formatoNumero.format(value); }
                        }
                    }
                }
            }
        });

    } catch (error) { console.error("Error gráficos:", error); }
}

// Función unificadora
async function actualizarTodo() {
    await cargarProductos();
    await cargarKPIs();
    await cargarGraficos();
}

// Inicio
document.addEventListener("DOMContentLoaded", actualizarTodo);
formProducto.addEventListener("submit", agregarProducto);
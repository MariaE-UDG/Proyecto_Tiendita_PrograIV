// app.js
const API_URL = "http://127.0.0.1:8000/productos";
const formProducto = document.getElementById("formProducto");
const tablaProductos = document.getElementById("tablaProductos");
const totalProductos = document.getElementById("totalProductos");
const tabsCategorias = document.getElementById("tabsCategorias");

let graficoProductoInstance = null;
let graficoFechaInstance = null;

// Estado global: todos los productos y la categoría activa
let todosLosProductos = [];
let categoriaActiva = "";

const formatoMoneda = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' });
const formatoNumero = new Intl.NumberFormat('es-MX');

// ============================================================
// 1. Cargar Productos + construir tabs
// ============================================================
async function cargarProductos() {
    try {
        const respuesta = await fetch(API_URL);
        todosLosProductos = await respuesta.json();

        construirTabs();
        renderizarTabla();
    } catch (error) {
        console.error("Error al cargar productos:", error);
    }
}

// ============================================================
// 2. Construir tabs dinámicamente (solo la primera vez)
// ============================================================
function construirTabs() {
    // Si ya hay tabs generadas (más de 1), solo actualizar los contadores
    const tabsExistentes = tabsCategorias.querySelectorAll("[data-categoria]:not([data-categoria=''])");

    if (tabsExistentes.length === 0) {
        // Primera vez: generar las tabs
        const categorias = [...new Set(todosLosProductos.map(p => p.categoria))].sort();

        categorias.forEach(cat => {
            const li = document.createElement("li");
            li.className = "nav-item";
            li.setAttribute("role", "presentation");
            li.innerHTML = `
                <button class="nav-link" data-categoria="${cat}" type="button">
                    ${cat}
                    <span class="badge badge-tab" data-badge="${cat}">0</span>
                </button>
            `;
            tabsCategorias.appendChild(li);
        });
    }

    // Actualizar contadores de cada tab
    document.getElementById("badgeTodas").textContent = todosLosProductos.length;

    document.querySelectorAll("[data-badge]").forEach(badge => {
        const cat = badge.getAttribute("data-badge");
        const count = todosLosProductos.filter(p => p.categoria === cat).length;
        badge.textContent = count;
    });
}

// ============================================================
// 3. Renderizar tabla según la categoría activa
// ============================================================
function renderizarTabla() {
    const productos = categoriaActiva
        ? todosLosProductos.filter(p => p.categoria === categoriaActiva)
        : todosLosProductos;

    tablaProductos.innerHTML = "";
    totalProductos.textContent = `${productos.length} productos`;

    if (productos.length === 0) {
        tablaProductos.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-4 text-muted">
                    <i class="bi bi-inbox fs-3 d-block mb-2"></i>
                    No hay productos en esta categoría
                </td>
            </tr>
        `;
        return;
    }

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
}

// ============================================================
// 4. Escuchar clicks en las tabs
// ============================================================
tabsCategorias.addEventListener("click", (e) => {
    const btn = e.target.closest(".nav-link");
    if (!btn) return;

    // Quitar activa de todas
    tabsCategorias.querySelectorAll(".nav-link").forEach(t => t.classList.remove("active"));
    btn.classList.add("active");

    // Actualizar categoría activa y renderizar
    categoriaActiva = btn.getAttribute("data-categoria") || "";
    renderizarTabla();
});

// ============================================================
// 5. Agregar Producto
// ============================================================
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
        if (respuesta.ok) {
            formProducto.reset();
            await actualizarTodo();
        }
    } catch (error) {
        console.log(error);
    }
}

// ============================================================
// 6. Comprar Producto
// ============================================================
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
    } catch (error) {
        alert("Error de conexión");
    }
}

// ============================================================
// 7. Eliminar Producto
// ============================================================
async function eliminarProducto(id) {
    if (!confirm("¿Seguro que deseas eliminar este producto del inventario?")) return;
    try {
        const respuesta = await fetch(`${API_URL}/${id}`, { method: "DELETE" });
        if (respuesta.ok) {
            await actualizarTodo();
        }
    } catch (error) {
        console.log(error);
    }
}

// ============================================================
// 8. Cargar KPIs
// ============================================================
async function cargarKPIs() {
    try {
        const respuesta = await fetch("http://127.0.0.1:8000/kpis");
        const datos = await respuesta.json();

        document.getElementById("kpiIngresos").textContent = formatoMoneda.format(datos.ingresos_totales);
        document.getElementById("kpiTransacciones").textContent = formatoNumero.format(datos.transacciones);
        document.getElementById("kpiProducto").textContent = datos.producto_estrella;
    } catch (error) {
        console.error("Error KPIs:", error);
    }
}

// ============================================================
// 9. Gráficas con Chart.js
// ============================================================
async function cargarGraficos() {
    try {
        // Gráfica 1 (Top 10 Productos)
        const resProd = await fetch("http://127.0.0.1:8000/ventas-por-producto");
        const datosProd = await resProd.json();
        const ctxProd = document.getElementById('graficoCategoria').getContext('2d');

        if (graficoProductoInstance) graficoProductoInstance.destroy();

        graficoProductoInstance = new Chart(ctxProd, {
            type: 'bar',
            data: {
                labels: datosProd.map(d => d.Producto),
                datasets: [{
                    label: 'Ingresos',
                    data: datosProd.map(d => d.Total_Venta),
                    backgroundColor: 'rgba(234, 88, 12, 0.8)',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return 'Ingresos: ' + formatoMoneda.format(context.raw);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            callback: function(value) {
                                return '$' + formatoNumero.format(value);
                            }
                        }
                    }
                }
            }
        });

        // Gráfica 2 (Últimos 30 días)
        const resFec = await fetch("http://127.0.0.1:8000/ventas-por-fecha");
        let datosFec = await resFec.json();

        if (datosFec.length > 30) {
            datosFec = datosFec.slice(-30);
        }

        const ctxFec = document.getElementById('graficoFecha').getContext('2d');

        if (graficoFechaInstance) graficoFechaInstance.destroy();

        graficoFechaInstance = new Chart(ctxFec, {
            type: 'line',
            data: {
                labels: datosFec.map(d => d.Fecha),
                datasets: [{
                    label: 'Ingresos por Día',
                    data: datosFec.map(d => d.Total_Venta),
                    backgroundColor: 'rgba(220, 38, 38, 0.2)',
                    borderColor: 'rgba(220, 38, 38, 1)',
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
                            label: function(context) {
                                return 'Ingresos: ' + formatoMoneda.format(context.raw);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            callback: function(value) {
                                return '$' + formatoNumero.format(value);
                            }
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error("Error gráficos:", error);
    }
}

// ============================================================
// 10. Actualizar todo
// ============================================================
async function actualizarTodo() {
    await cargarProductos();
    await cargarKPIs();
    await cargarGraficos();
}

// ============================================================
// 11. Init
// ============================================================
document.addEventListener("DOMContentLoaded", actualizarTodo);
formProducto.addEventListener("submit", agregarProducto);
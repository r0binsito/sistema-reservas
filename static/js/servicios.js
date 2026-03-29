// === SELECCIÓN DE ELEMENTOS DEL DOM ===
const servicioModal = document.getElementById('servicioModal');
const deleteModal = document.getElementById('deleteModal');
const servicioForm = document.getElementById('servicioForm');

/**
 * Prepara y abre el modal para crear un servicio nuevo.
 * Limpia el formulario y cambia los textos para que digan "Nuevo".
 */
function openCreateModal() {
    servicioForm.reset(); // Borra cualquier dato escrito anteriormente
    document.getElementById('servicioId').value = ''; // Asegura que el ID esté vacío
    document.getElementById('modalTitle').innerText = 'Nuevo Servicio';
    document.getElementById('btnText').innerText = 'Guardar servicio';
    servicioModal.classList.add('active'); // Muestra el modal (usando CSS)
}

/**
 * Obtiene los datos de un servicio desde la API y abre el modal para editar.
 * @param {number} id - El ID del servicio a editar.
 */
async function openEditModal(id) {
    try {
        // Petición a tu ruta de Flask para obtener un servicio específico
        const response = await fetch(`/api/servicios/${id}`);
        const data = await response.json();
        
        if (response.ok) {
            // Rellena los campos del formulario con los datos de la DB
            document.getElementById('servicioId').value = data.id;
            document.getElementById('nombre').value = data.nombre;
            document.getElementById('duracion_min').value = data.duracion_min;
            document.getElementById('precio').value = data.precio;
            
            // Cambia la apariencia del modal para modo "Edición"
            document.getElementById('modalTitle').innerText = 'Editar Servicio';
            document.getElementById('btnText').innerText = 'Actualizar cambios';
            servicioModal.classList.add('active');
        }
    } catch (e) { 
        showToast('Error al cargar datos', 'error'); 
    }
}

// === FUNCIONES DE CIERRE ===
function closeModal() { servicioModal.classList.remove('active'); }
function closeDeleteModal() { deleteModal.classList.remove('active'); }

/**
 * Configura el modal de confirmación de borrado.
 */
function confirmDelete(id, nombre) {
    document.getElementById('deleteServiceName').innerText = nombre;
    // Asigna la función de ejecución al botón "Sí, eliminar"
    document.getElementById('btnConfirmDelete').onclick = () => executeDelete(id);
    deleteModal.classList.add('active');
}

/**
 * Envía la petición DELETE a la API.
 */
async function executeDelete(id) {
    const response = await fetch(`/api/servicios/${id}`, { method: 'DELETE' });
    if (response.ok) {
        location.reload(); // Recarga la página para actualizar el grid
    } else {
        showToast('Error al eliminar', 'error');
    }
}

/**
 * MANEJADOR DEL FORMULARIO (CREAR / EDITAR)
 * Aquí es donde se procesan los datos antes de enviarlos al backend.
 */
servicioForm.onsubmit = async (e) => {
    e.preventDefault(); // Evita que la página se recargue automáticamente
    
    const id = document.getElementById('servicioId').value;
    const formData = new FormData(servicioForm);
    const payload = Object.fromEntries(formData.entries());

    // --- LIMPIEZA CRÍTICA DE DATOS ---
    // Convertimos a tipos numéricos para evitar errores de validación en Flask/SQL
    payload.duracion_min = parseInt(payload.duracion_min); 
    payload.precio = parseFloat(payload.precio) || 0;

    // Si hay ID usamos PUT (editar), si no POST (crear)
    const url = id ? `/api/servicios/${id}` : '/servicio/nuevo';

    const method = id ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload) // Enviamos como JSON limpio
        });

        if (response.ok) {
            location.reload(); // Éxito: refrescamos la vista
        } else {
            showToast('Error al guardar el servicio', 'error');
        }
    } catch (error) {
        showToast('Error de conexión con el servidor', 'error');
    }
};

/**
 * Muestra notificaciones visuales (Toasts).
 */
function showToast(msg, type) {
    const toast = document.getElementById('serviciosToast');
    document.getElementById('toastMessage').innerText = msg;
    // Cambia el emoji según el tipo de mensaje
    document.getElementById('toastIcon').innerText = type === 'success' ? '✅' : '❌';
    
    toast.className = `servicios-toast visible ${type}`;
    // Oculta el mensaje después de 3 segundos
    setTimeout(() => toast.classList.remove('visible'), 3000);
}

// Cierra los modales si el usuario hace clic fuera del recuadro blanco
window.onclick = (event) => {
    if (event.target == servicioModal) closeModal();
    if (event.target == deleteModal) closeDeleteModal();
};
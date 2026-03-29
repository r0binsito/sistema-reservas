(function() {
    'use strict';

    const input = document.getElementById('busqueda-clientes');
    const tableBody = document.getElementById('clientes-body');
    const loading = document.getElementById('search-loading');
    let originalHTML = ""; // Aquí vive tu tabla inicial

    if (!input || !tableBody) return;

    // GUARDAR ESTADO INICIAL (Esto es sagrado)
    originalHTML = tableBody.innerHTML;

    input.addEventListener('input', async (e) => {
        const query = e.target.value.trim();

        // 1. SI ESTÁ VACÍO: Restaurar tabla original y salir
        if (query === "") {
            tableBody.innerHTML = originalHTML;
            return;
        }

        // 2. BUSCAR (Desde la primera letra)
        try {
            if (loading) loading.style.display = 'block';

            const response = await fetch(`/api/clientes/buscar?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            const clientes = data.clientes || [];

            if (loading) loading.style.display = 'none';

            if (clientes.length === 0) {
                tableBody.innerHTML = `<tr><td colspan="3" style="text-align:center; padding:30px;">No hay resultados para "${query}"</td></tr>`;
            } else {
                // Dibujar solo los clientes encontrados
                tableBody.innerHTML = clientes.map(c => `
                    <tr class="cliente-row">
                        <td>
                            <div class="cliente-nombre-cell">
                                <span class="cliente-avatar">👤</span>
                                <span class="cliente-nombre">${c.nombre}</span>
                            </div>
                        </td>
                        <td>${c.telefono || '—'}</td>
                        <td>${c.email || '—'}</td>
                    </tr>
                `).join('');
            }
        } catch (err) {
            console.error("Error buscando:", err);
            if (loading) loading.style.display = 'none';
        }
    });
})();
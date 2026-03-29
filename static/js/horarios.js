/**
 * Módulo de Horarios - Reserfy
 * Maneja la lógica de activación/desactivación de días y envío de datos
 */

(function() {
    'use strict';

    /**
     * Inicializa el módulo de horarios
     */
    function init() {
        console.log('[Horarios] Inicializando módulo...');

        // Vincular eventos a los switches
        document.querySelectorAll('.horario-switch input').forEach(toggleSwitch => {
            toggleSwitch.addEventListener('change', handleToggleChange);
        });

        // Vincular evento al formulario
        const form = document.getElementById('horarios-form');
        if (form) {
            form.addEventListener('submit', handleSubmit);
            console.log('[Horarios] Formulario encontrado y evento vinculado');
        } else {
            console.error('[Horarios] ERROR: No se encontró el formulario con id="horarios-form"');
        }

        // Establecer estado inicial
        actualizarEstadoInicial();
    }

    /**
     * Actualiza el estado visual inicial de las tarjetas
     */
    function actualizarEstadoInicial() {
        document.querySelectorAll('.horario-card').forEach(card => {
            const switchInput = card.querySelector('.horario-switch input');
            const times = card.querySelector('.horario-times');
            const inputs = times.querySelectorAll('input[type="time"]');

            if (switchInput && switchInput.checked) {
                card.classList.add('activo');
                card.classList.remove('inactivo');
                if (times) {
                    times.style.opacity = '1';
                    times.style.pointerEvents = 'auto';
                }
                // Habilitar inputs
                inputs.forEach(input => input.disabled = false);
            } else {
                card.classList.remove('activo');
                card.classList.add('inactivo');
                if (times) {
                    times.style.opacity = '0.4';
                    times.style.pointerEvents = 'none';
                }
                // Deshabilitar inputs
                inputs.forEach(input => input.disabled = true);
            }
        });
    }

    /**
     * Maneja el cambio de estado del switch
     * @param {Event} e - Evento de cambio
     */
    function handleToggleChange(e) {
        const switchInput = e.target;
        const card = switchInput.closest('.horario-card');
        const times = card.querySelector('.horario-times');
        const inputs = times.querySelectorAll('input[type="time"]');

        if (switchInput.checked) {
            // Activar
            card.classList.add('activo');
            card.classList.remove('inactivo');
            times.style.opacity = '1';
            times.style.pointerEvents = 'auto';

            // Habilitar inputs
            inputs.forEach(input => input.disabled = false);

            // Establecer valores por defecto si están vacíos
            inputs.forEach(input => {
                if (!input.value) {
                    if (input.name.includes('apertura')) {
                        input.value = '09:00';
                    } else if (input.name.includes('cierre')) {
                        input.value = '18:00';
                    }
                }
            });
        } else {
            // Desactivar
            card.classList.remove('activo');
            card.classList.add('inactivo');
            times.style.opacity = '0.4';
            times.style.pointerEvents = 'none';

            // Deshabilitar inputs
            inputs.forEach(input => input.disabled = true);

            // Limpiar valores
            inputs.forEach(input => {
                input.value = '';
            });
        }
    }

    /**
     * Valida los datos antes de enviar
     * @returns {Object|null} - Error con mensaje o null si es válido
     */
    function validarHorarios() {
        let tieneAlgunActivo = false;
        let errores = [];

        document.querySelectorAll('.horario-card').forEach(card => {
            const switchInput = card.querySelector('.horario-switch input');
            const diaNombre = card.querySelector('.horario-dia-nombre').textContent;

            if (switchInput && switchInput.checked) {
                tieneAlgunActivo = true;

                const aperturaInput = card.querySelector('input[name^="apertura_"]');
                const cierreInput = card.querySelector('input[name^="cierre_"]');

                if (!aperturaInput || !aperturaInput.value) {
                    errores.push(`${diaNombre}: Falta hora de apertura`);
                }
                if (!cierreInput || !cierreInput.value) {
                    errores.push(`${diaNombre}: Falta hora de cierre`);
                }

                // Validar que apertura < cierre
                if (aperturaInput && cierreInput && aperturaInput.value && cierreInput.value) {
                    const apertura = new Date(`2000-01-01T${aperturaInput.value}`);
                    const cierre = new Date(`2000-01-01T${cierreInput.value}`);

                    if (apertura >= cierre) {
                        errores.push(`${diaNombre}: La hora de apertura debe ser menor a la de cierre`);
                    }
                }
            }
        });

        if (!tieneAlgunActivo) {
            return { error: 'Debes activar al menos un día de la semana' };
        }

        if (errores.length > 0) {
            return { error: errores[0] };
        }

        return null;
    }

    /**
     * Recolecta los datos de todos los días
     * @returns {Array} - Array de objetos con los datos de horarios
     */
    function recolectarDatos() {
        const datos = [];

        document.querySelectorAll('.horario-card').forEach(card => {
            const switchInput = card.querySelector('.horario-switch input');
            const diaIndex = parseInt(card.dataset.dia, 10);

            const aperturaInput = card.querySelector('input[name^="apertura_"]');
            const cierreInput = card.querySelector('input[name^="cierre_"]');

            if (switchInput && switchInput.checked) {
                datos.push({
                    dia_semana: diaIndex,
                    hora_inicio: aperturaInput ? aperturaInput.value : null,
                    hora_fin: cierreInput ? cierreInput.value : null,
                    activo: true
                });
            } else {
                datos.push({
                    dia_semana: diaIndex,
                    hora_inicio: null,
                    hora_fin: null,
                    activo: false
                });
            }
        });

        return datos;
    }

    /**
     * Muestra un toast de notificación
     * @param {string} mensaje - Mensaje a mostrar
     * @param {string} tipo - Tipo: 'success' o 'error'
     */
    function mostrarToast(mensaje, tipo = 'success') {
        console.log(`[Horarios] Toast (${tipo}): ${mensaje}`);

        // Buscar si ya existe un toast
        let toast = document.getElementById('horarios-toast');

        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'horarios-toast';
            toast.className = 'servicios-toast';
            toast.style.cssText = 'position:fixed;bottom:24px;right:24px;background:var(--bg-card);padding:16px 24px;border-radius:var(--radius-md);box-shadow:var(--shadow-lg);display:flex;align-items:center;gap:12px;transform:translateY(100px);opacity:0;transition:var(--transition);z-index:2000;border-left:4px solid;';
            document.body.appendChild(toast);
        }

        toast.textContent = mensaje;
        toast.style.borderLeftColor = tipo === 'error' ? '#DC2626' : '#16A34A';
        toast.classList.add('visible');
        toast.style.transform = 'translateY(0)';
        toast.style.opacity = '1';

        setTimeout(() => {
            toast.style.transform = 'translateY(100px)';
            toast.style.opacity = '0';
            toast.classList.remove('visible');
        }, 3000);
    }

    /**
     * Maneja el envío del formulario
     * @param {Event} e - Evento de submit
     */
    async function handleSubmit(e) {
        e.preventDefault();
        console.log('[Horarios] handleSubmit llamado');

        // Validar
        const validacion = validarHorarios();
        if (validacion) {
            console.log('[Horarios] Validación fallida:', validacion.error);
            mostrarToast(validacion.error, 'error');
            return;
        }

        // Recolectar datos
        const horarios = recolectarDatos();
        console.log('[Horarios] Datos recolectados:', horarios);

        // Filtrar solo los activos con datos válidos
        const horariosActivos = horarios.filter(h => h.activo && h.hora_inicio && h.hora_fin);
        console.log('[Horarios] Horarios activos a enviar:', horariosActivos);

        if (horariosActivos.length === 0) {
            mostrarToast('Debes activar al menos un día con horarios válidos', 'error');
            return;
        }

        // Mostrar indicador de carga
        const submitBtn = document.querySelector('.btn-primary[type="submit"]');
        const textoOriginal = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = 'Guardando...';

        try {
            console.log('[Horarios] Enviando petición a /api/horarios...');

            const response = await fetch('/api/horarios', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ horarios: horariosActivos })
            });

            const data = await response.json();
            console.log('[Horarios] Respuesta del servidor:', data);

            if (response.ok && data.success) {
                mostrarToast('Horarios guardados correctamente', 'success');
                // Redirigir al dashboard después de 1 segundo
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1000);
            } else {
                mostrarToast(data.error || 'Error al guardar los horarios', 'error');
            }
        } catch (error) {
            console.error('[Horarios] Error:', error);
            mostrarToast('Error de conexión. Intenta nuevamente.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = textoOriginal;
        }
    }

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
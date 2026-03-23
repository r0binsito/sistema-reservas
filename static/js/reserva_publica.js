// ===== ESTADO =====
let pasoActual = 1;
let servicioSeleccionado = null;
let fechaSeleccionada = null;
let horaSeleccionada = null;
let mesActual = new Date();
let pasosCompletados = new Set();

// ===== PASOS =====
function irPaso(paso) {
    if (paso > pasoActual) {
        if (pasoActual === 1 && !servicioSeleccionado) {
            mostrarAlerta('Por favor selecciona un servicio para continuar.');
            return;
        }
        if (pasoActual === 2 && !fechaSeleccionada) {
            mostrarAlerta('Por favor selecciona una fecha para continuar.');
            return;
        }
        if (pasoActual === 2 && !horaSeleccionada) {
            mostrarAlerta('Por favor selecciona un horario para continuar.');
            return;
        }
    }

    // Registrar pasos completados
    if (paso > pasoActual) {
        pasosCompletados.add(pasoActual);
    }

    document.querySelectorAll('.reserva-panel').forEach(p => p.style.display = 'none');
    document.getElementById('panel-' + paso).style.display = 'block';

    document.querySelectorAll('.reserva-step').forEach((s, i) => {
        const num = i + 1;
        s.classList.remove('activo', 'completado', 'activo-completado');
        const circle = s.querySelector('.reserva-step-circle');

        if (num === paso && pasosCompletados.has(num)) {
            // Estás aquí pero ya lo completaste
            s.classList.add('activo-completado');
            circle.textContent = '✓';
            s.style.cursor = 'default';
            s.onclick = null;
        } else if (num === paso) {
            s.classList.add('activo');
            circle.textContent = num;
            s.style.cursor = 'default';
            s.onclick = null;
        } else if (pasosCompletados.has(num)) {
            s.classList.add('completado');
            circle.textContent = '✓';
            // Clickeable para navegar
            s.style.cursor = 'pointer';
            s.onclick = () => irPaso(num);
        } else if (num < paso) {
            s.classList.add('completado');
            circle.textContent = '✓';
            s.style.cursor = 'pointer';
            s.onclick = () => irPaso(num);
        } else {
            circle.textContent = num;
            s.style.cursor = 'not-allowed';
            s.onclick = null;
        }
    });

    pasoActual = paso;
    if (paso === 3) actualizarResumen();
    window.scrollTo(0, 0);
}

function mostrarAlerta(mensaje) {
    let alerta = document.getElementById('reserva-alerta');
    if (!alerta) {
        alerta = document.createElement('div');
        alerta.id = 'reserva-alerta';
        alerta.className = 'reserva-alerta-flotante';
        document.body.appendChild(alerta);
    }
    alerta.textContent = mensaje;
    alerta.classList.add('visible');
    setTimeout(() => alerta.classList.remove('visible'), 3000);
}

// ===== SERVICIOS =====
function seleccionarServicio(card) {
    document.querySelectorAll('.reserva-servicio-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    servicioSeleccionado = card.dataset.nombre;
    document.getElementById('servicio-hidden').value = servicioSeleccionado;

    if (PLAN === 'pro' || PLAN === 'elite') {
        card.classList.add('reserva-servicio-animado');
        setTimeout(() => card.classList.remove('reserva-servicio-animado'), 400);
    }
}

// ===== SLOTS =====
function cargarSlots(fecha) {
    fechaSeleccionada = fecha;
    if (document.getElementById('fecha-hidden')) {
        document.getElementById('fecha-hidden').value = fecha;
    }

    const container = document.getElementById('slots-container');
    const wrap = document.getElementById('slots-wrap');

    container.innerHTML = '<p class="reserva-cargando">Cargando horarios...</p>';
    wrap.style.display = 'block';
    horaSeleccionada = null;
    document.getElementById('btn-paso-3').disabled = true;
    document.getElementById('hora-hidden').value = '';

    fetch(`/b/${SLUG}/slots?fecha=${fecha}&servicio=${encodeURIComponent(servicioSeleccionado || '')}`)
        .then(r => r.json())
        .then(data => {
            if (data.slots && data.slots.length > 0) {
                container.innerHTML = '';
                data.slots.forEach((slot, i) => {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'slot-btn';
                    btn.textContent = slot.local;
                    btn.dataset.utc = slot.utc;
                    btn.dataset.local = slot.local;
                    setTimeout(() => btn.classList.add('visible'), i * 50);
                    btn.onclick = () => seleccionarSlot(btn, slot);
                    container.appendChild(btn);
                });
            } else {
                container.innerHTML = '<p class="reserva-sin-slots">No hay disponibilidad para este día. Intenta con otra fecha.</p>';
            }
        })
        .catch(() => {
            container.innerHTML = '<p class="reserva-error-slots">Error cargando horarios. Intenta de nuevo.</p>';
        });
}

function seleccionarSlot(btn, slot) {
    document.querySelectorAll('.slot-btn').forEach(b => {
        b.classList.remove('selected');
    });

    btn.classList.add('selected');
    horaSeleccionada = slot;
    document.getElementById('hora-hidden').value = slot.utc;

    // ACTUALIZACIÓN: Desbloqueamos el botón de siguiente al elegir hora
    document.getElementById('btn-paso-3').disabled = false; 

    if (PLAN === 'pro' || PLAN === 'elite') {
        btn.classList.add('slot-animado');
        setTimeout(() => btn.classList.remove('slot-animado'), 300);
    }
}

// ===== CALENDARIO (Pro/Elite) =====
function renderCalendario() {
    const cal = document.getElementById('reserva-calendario');
    if (!cal) return;

    const hoy = new Date();
    const year = mesActual.getFullYear();
    const mes = mesActual.getMonth();

    const diasSemana = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do'];
    const meses = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                   'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];

    const primerDia = new Date(year, mes, 1).getDay();
    const offset = primerDia === 0 ? 6 : primerDia - 1;
    const diasEnMes = new Date(year, mes + 1, 0).getDate();

    let html = `
        <div class="cal-header">
            <button type="button" class="cal-nav-btn" onclick="cambiarMes(-1)">←</button>
            <span class="cal-titulo">${meses[mes]} ${year}</span>
            <button type="button" class="cal-nav-btn" onclick="cambiarMes(1)">→</button>
        </div>
        <div class="cal-grid">
            ${diasSemana.map(d => `<div class="cal-dia-label">${d}</div>`).join('')}
    `;

    for (let i = 0; i < offset; i++) {
        html += `<div class="cal-dia disabled"></div>`;
    }

    for (let d = 1; d <= diasEnMes; d++) {
        const fecha = new Date(year, mes, d);
        const esHoy = fecha.toDateString() === hoy.toDateString();
        const esPasado = fecha < new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
        const esDomingo = fecha.getDay() === 0;
        const fechaStr = `${year}-${String(mes+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
        const esSeleccionado = fechaStr === fechaSeleccionada;

        let clase = 'cal-dia';
        if (esPasado || esDomingo) clase += ' disabled';
        else if (esSeleccionado) clase += ' selected';
        else if (esHoy) clase += ' hoy';

        const onclick = (esPasado || esDomingo) ? '' : `onclick="seleccionarFecha('${fechaStr}')"`;
        html += `<div class="${clase}" ${onclick}>${d}</div>`;
    }

    html += `</div>`;
    cal.innerHTML = html;
}

function cambiarMes(delta) {
    mesActual.setMonth(mesActual.getMonth() + delta);
    renderCalendario();
}

function seleccionarFecha(fecha) {
    fechaSeleccionada = fecha;
    if (document.getElementById('fecha-hidden')) {
        document.getElementById('fecha-hidden').value = fecha;
    }
    renderCalendario();
    cargarSlots(fecha);
}

// ===== DATOS PRECARGADOS =====
function cargarDatosGuardados() {
    const datos = JSON.parse(localStorage.getItem('reserfy_cliente') || 'null');
    if (datos && datos.email) {
        document.getElementById('input-nombre').value = datos.nombre || '';
        document.getElementById('input-email').value = datos.email || '';
        document.getElementById('input-telefono').value = datos.telefono || '';
        document.getElementById('datos-precargados-banner').style.display = 'flex';
    }
}

function limpiarDatos() {
    localStorage.removeItem('reserfy_cliente');
    document.getElementById('input-nombre').value = '';
    document.getElementById('input-email').value = '';
    document.getElementById('input-telefono').value = '';
    document.getElementById('datos-precargados-banner').style.display = 'none';
}

function guardarDatos() {
    const datos = {
        nombre: document.getElementById('input-nombre').value,
        email: document.getElementById('input-email').value,
        telefono: document.getElementById('input-telefono').value
    };
    localStorage.setItem('reserfy_cliente', JSON.stringify(datos));
}

// ===== RESUMEN =====
function actualizarResumen() {
    document.getElementById('resumen-servicio').textContent = servicioSeleccionado || '—';
    if (horaSeleccionada) {
        document.getElementById('resumen-fecha').textContent =
            `${fechaSeleccionada} a las ${horaSeleccionada.local}`;
    }
    cargarDatosGuardados();
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => {
    irPaso(1);

    if (PLAN === 'pro' || PLAN === 'elite') {
        renderCalendario();
    }

    const formReserva = document.getElementById('form-reserva');
    if (formReserva) {
        formReserva.addEventListener('submit', guardarDatos);
    }
});
// Jerarquía para medir qué plan es superior
const jerarquiaPlanes = {
    'trial': 0,
    'starter': 1,
    'pro': 2,
    'elite': 3
};

// Función principal que evalúa si es Upgrade o Downgrade
function validarCambioPlan(planElegido) {
    const planActual = document.getElementById('plan-actual-usuario').value || 'trial';
    
    const pesoActual = jerarquiaPlanes[planActual];
    const pesoElegido = jerarquiaPlanes[planElegido];

    // Si el usuario intenta elegir un plan inferior
    if (pesoElegido < pesoActual) {
        abrirDowngrade(planActual, planElegido);
    } else {
        // Si es igual o superior, fluye al modal normal
        abrirStripe(planElegido);
    }
}

// Modal original de Stripe
function abrirStripe(plan) {
    const nombres = { starter: 'Starter', pro: 'Pro', elite: 'Elite' };
    const precios = { starter: '$9.99/mes', pro: '$19.99/mes', elite: '$39.99/mes' };

    document.getElementById('modal-stripe-plan').textContent =
        `Plan ${nombres[plan]} — ${precios[plan]}`;

    const waLink = document.getElementById('modal-stripe-wa');
    waLink.href = `https://wa.me/18295551234?text=Hola, quiero contratar el plan ${nombres[plan]} de Reserfy`;

    document.getElementById('modal-stripe').style.display = 'flex';
}

function cerrarStripe() {
    document.getElementById('modal-stripe').style.display = 'none';
}

// Modal de Downgrade
function abrirDowngrade(planActual, planElegido) {
    const modal = document.getElementById('modal-downgrade');
    const waLink = document.getElementById('modal-downgrade-wa');
    
    const nombres = { trial: 'Prueba', starter: 'Starter', pro: 'Pro', elite: 'Elite' };
    
    // Personalizamos el mensaje directo para soporte
    waLink.href = `https://wa.me/18295551234?text=Hola, actualmente tengo el plan ${nombres[planActual]} y me gustaría bajar al plan ${nombres[planElegido]}.`;
    
    modal.style.display = 'flex';
}

function cerrarDowngrade() {
    document.getElementById('modal-downgrade').style.display = 'none';
}

// Cerrar al hacer clic fuera (para AMBOS modales)
document.addEventListener('DOMContentLoaded', () => {
    const overlayStripe = document.getElementById('modal-stripe');
    const overlayDowngrade = document.getElementById('modal-downgrade');

    if (overlayStripe) {
        overlayStripe.addEventListener('click', (e) => {
            if (e.target === overlayStripe) cerrarStripe();
        });
    }

    if (overlayDowngrade) {
        overlayDowngrade.addEventListener('click', (e) => {
            if (e.target === overlayDowngrade) cerrarDowngrade();
        });
    }
});
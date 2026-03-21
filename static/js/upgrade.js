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

// Cerrar al hacer clic fuera
document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.getElementById('modal-stripe');
    if (overlay) {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) cerrarStripe();
        });
    }
});
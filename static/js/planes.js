let esAnual = false;

function toggleBilling() {
    esAnual = !esAnual;

    const circle = document.getElementById('toggle-circle');
    const labelMensual = document.getElementById('label-mensual');
    const labelAnual = document.getElementById('label-anual');

    const starterPrecio = document.getElementById('starter-precio');
    const starterPeriodo = document.getElementById('starter-periodo');
    const starterAnual = document.getElementById('starter-anual');

    const proPrecio = document.getElementById('pro-precio');
    const proPeriodo = document.getElementById('pro-periodo');
    const proAnual = document.getElementById('pro-anual');

    const elitePrecio = document.getElementById('elite-precio');
    const elitePeriodo = document.getElementById('elite-periodo');
    const eliteAnual = document.getElementById('elite-anual');

    if (esAnual) {
        circle.classList.add('active');
        labelAnual.style.fontWeight = '700';
        labelAnual.style.color = '#FA8F3E';
        labelMensual.style.fontWeight = '400';
        labelMensual.style.color = 'rgba(255,255,255,0.5)';

        starterPrecio.textContent = '99.90';
        starterPeriodo.textContent = 'por año';
        starterAnual.textContent = 'equivale a $8.32/mes — ahorras $19.98';
        starterAnual.style.display = 'block';

        proPrecio.textContent = '199.90';
        proPeriodo.textContent = 'por año';
        proAnual.textContent = 'equivale a $16.66/mes — ahorras $39.98';
        proAnual.style.display = 'block';

        elitePrecio.textContent = '399.90';
        elitePeriodo.textContent = 'por año';
        eliteAnual.textContent = 'equivale a $33.32/mes — ahorras $79.98';
        eliteAnual.style.display = 'block';

    } else {
        circle.classList.remove('active');
        labelMensual.style.fontWeight = '700';
        labelMensual.style.color = '#FA8F3E';
        labelAnual.style.fontWeight = '400';
        labelAnual.style.color = 'rgba(255,255,255,0.5)';

        starterPrecio.textContent = '9.99';
        starterPeriodo.textContent = 'por mes';
        starterAnual.style.display = 'none';

        proPrecio.textContent = '19.99';
        proPeriodo.textContent = 'por mes';
        proAnual.style.display = 'none';

        elitePrecio.textContent = '39.99';
        elitePeriodo.textContent = 'por mes';
        eliteAnual.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const labelMensual = document.getElementById('label-mensual');
    if (labelMensual) {
        labelMensual.style.fontWeight = '700';
        labelMensual.style.color = '#FA8F3E';
    }
});
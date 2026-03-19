document.addEventListener('DOMContentLoaded', function() {

    // Navbar scroll effect
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 20) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // Animar cards al cargar
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, i) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 100 + i * 80);
    });

    // Animar alertas
    const alertas = document.querySelectorAll('.alerta');
    alertas.forEach(a => a.classList.add('animate-fadeInDown'));

    // Animar filas de tabla
    const rows = document.querySelectorAll('.tabla tbody tr');
    rows.forEach((row, i) => {
        row.style.opacity = '0';
        row.style.transform = 'translateX(-10px)';
        setTimeout(() => {
            row.style.transition = 'all 0.4s ease';
            row.style.opacity = '1';
            row.style.transform = 'translateX(0)';
        }, 50 + i * 50);
    });

    // Ripple effect en botones
    document.querySelectorAll('.btn-primary').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = btn.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${e.clientX - rect.left - size/2}px;
                top: ${e.clientY - rect.top - size/2}px;
                background: rgba(255,255,255,0.3);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s linear;
                pointer-events: none;
            `;
            btn.appendChild(ripple);
            setTimeout(() => ripple.remove(), 600);
        });
    });

});


// Business type card selection
function seleccionarTipo(card) {
    document.querySelectorAll('.biz-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');

    const tipo = card.dataset.type;
    const cta = document.getElementById('biz-cta');
    const selected = document.getElementById('biz-selected');
    const btn = document.getElementById('biz-register-btn');

    selected.textContent = tipo;
    cta.style.display = 'block';
    btn.href = `/registro?tipo=${encodeURIComponent(tipo)}`;
}

// Animar business cards en cascada al cargar
document.addEventListener('DOMContentLoaded', () => {
    const bizCards = document.querySelectorAll('.biz-card');
    bizCards.forEach((card, i) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 200 + i * 80);
    });
});

// FAQ toggle
function toggleFaq(item) {
    const body = item.querySelector('.faq-body');
    const arrow = item.querySelector('.faq-arrow');
    const isOpen = body.style.display === 'block';
    body.style.display = isOpen ? 'none' : 'block';
    arrow.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(180deg)';
    item.style.borderColor = isOpen ? 'var(--border-default)' : 'var(--border-cyan)';
}

// Ocultar footer en index porque el CTA final ya funciona como footer
if (window.location.pathname === '/') {
    const footer = document.getElementById('site-footer');
    if (footer) footer.style.display = 'none';
}

// Banner rotativo
document.addEventListener('DOMContentLoaded', () => {
    const items = document.querySelectorAll('.banner-rotativo-item');
    if (!items.length) return;

    let actual = 0;
    const duracion = 3500;

    function mostrar(index) {
        items.forEach(item => {
            item.style.animation = 'none';
            item.style.opacity = '0';
        });
        items[index].style.animation = `fadeSlide ${duracion}ms ease forwards`;
    }

    mostrar(actual);
    setInterval(() => {
        actual = (actual + 1) % items.length;
        mostrar(actual);
    }, duracion);
});

// Navbar hamburguesa
const hamburguesa = document.getElementById('nav-hamburguesa');
const navLinks = document.getElementById('nav-links');

if (hamburguesa && navLinks) {
    hamburguesa.addEventListener('click', () => {
        hamburguesa.classList.toggle('active');
        navLinks.classList.toggle('active');
    });

    // Cerrar al hacer clic en un link
    navLinks.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            hamburguesa.classList.remove('active');
            navLinks.classList.remove('active');
        });
    });
}
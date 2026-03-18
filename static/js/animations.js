// Animación de slots en cascada
function animarSlots() {
    const slots = document.querySelectorAll('.slot-btn');
    slots.forEach((slot, i) => {
        setTimeout(() => {
            slot.classList.add('visible');
        }, i * 60);
    });
}

// Observador para animar elementos al hacer scroll
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate-fadeInUp');
            observer.unobserve(entry.target);
        }
    });
}, { threshold: 0.1 });

document.addEventListener('DOMContentLoaded', () => {
    // Observar elementos que deben animarse al hacer scroll
    document.querySelectorAll('.card, .form-grupo').forEach(el => {
        observer.observe(el);
    });

    // Animar slots si existen
    if (document.querySelector('.slot-btn')) {
        animarSlots();
    }

    // Contador animado para stats
    document.querySelectorAll('[data-count]').forEach(el => {
        const target = parseInt(el.dataset.count);
        let current = 0;
        const step = target / 30;
        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                el.textContent = target;
                clearInterval(timer);
            } else {
                el.textContent = Math.floor(current);
            }
        }, 30);
    });
});

// Ripple keyframe
const style = document.createElement('style');
style.textContent = `
    @keyframes ripple {
        to { transform: scale(4); opacity: 0; }
    }
`;
document.head.appendChild(style);
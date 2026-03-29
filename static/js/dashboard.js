/**
 * Dashboard JavaScript - Reserfy
 * Maneja: Modal de onboarding, animación de éxito, copia de link
 */

(function() {
    'use strict';

    // ===== MODAL DE ONBOARDING =====
    const onboardingModal = document.getElementById('onboarding-modal');

    if (onboardingModal) {
        // El modal es bloqueante - no se puede cerrar hasta completar
        document.body.style.overflow = 'hidden';
    }

    // ===== MODAL DE ÉXITO =====
    const successModal = document.getElementById('success-modal');

    if (successModal) {
        // Animación de éxito
        const title = document.getElementById('success-title');
        const text = document.getElementById('success-text');
        const content = document.getElementById('success-content');

        // Secuencia de animación
        setTimeout(function() {
            // Cambiar a mensaje de éxito
            if (content) {
                content.innerHTML = `
                    <div class="success-check">✓</div>
                    <h3 class="success-title" style="color: #4ade80;">¡Link generado con éxito!</h3>
                    <p class="success-text">Tu link de reservas está listo para compartir.</p>
                `;
                successModal.classList.add('success');
            }
        }, 2000);

        // Cerrar modal después de mostrar éxito
        setTimeout(function() {
            successModal.style.opacity = '0';
            successModal.style.transition = 'opacity 0.5s ease';

            setTimeout(function() {
                successModal.style.display = 'none';
            }, 500);
        }, 4500);
    }

    // ===== BOTÓN COPIAR LINK =====
    const copyBtn = document.getElementById('copy-link-btn');

    if (copyBtn) {
        copyBtn.addEventListener('click', function() {
            const url = this.getAttribute('data-url');

            if (!url) {
                console.error('No URL found');
                return;
            }

            const btn = this;
            const textElement = btn.querySelector('.link-copy-text');

            // Intentar usar la API moderna
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(url)
                    .then(function() {
                        showCopySuccess(btn, textElement);
                    })
                    .catch(function() {
                        fallbackCopy(url, btn, textElement);
                    });
            } else {
                fallbackCopy(url, btn, textElement);
            }
        });
    }

    // Fallback para copiar
    function fallbackCopy(text, button, textElement) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        textarea.style.top = '-9999px';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();

        try {
            const successful = document.execCommand('copy');
            if (successful) {
                showCopySuccess(button, textElement);
            }
        } catch (err) {
            console.error('Copy failed:', err);
        }

        document.body.removeChild(textarea);
    }

    // Mostrar feedback de copia exitosa
    function showCopySuccess(button, textElement) {
        const originalText = textElement ? textElement.textContent : 'Copiar link';

        button.classList.add('copied');

        if (textElement) {
            textElement.textContent = '¡Link copiado!';
        }

        showToast('Link copiado al portapapeles');

        setTimeout(function() {
            button.classList.remove('copied');
            if (textElement) {
                textElement.textContent = originalText;
            }
        }, 2500);
    }

    // ===== TOAST DE NOTIFICACIÓN =====
    function showToast(message) {
        const existingToast = document.querySelector('.dashboard-toast');
        if (existingToast) {
            existingToast.remove();
        }

        const toast = document.createElement('div');
        toast.className = 'dashboard-toast';
        toast.textContent = message;

        Object.assign(toast.style, {
            position: 'fixed',
            bottom: '24px',
            left: '50%',
            transform: 'translateX(-50%) translateY(100px)',
            background: 'linear-gradient(135deg, #912A5C, #FA8F3E)',
            color: 'white',
            padding: '14px 28px',
            borderRadius: '50px',
            fontSize: '14px',
            fontWeight: '500',
            fontFamily: "'Inter', 'Segoe UI', sans-serif",
            zIndex: '99999',
            boxShadow: '0 4px 20px rgba(145, 42, 92, 0.35)',
            transition: 'transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)'
        });

        document.body.appendChild(toast);

        requestAnimationFrame(function() {
            toast.style.transform = 'translateX(-50%) translateY(0)';
        });

        setTimeout(function() {
            toast.style.transform = 'translateX(-50%) translateY(100px)';
            setTimeout(function() {
                toast.remove();
            }, 400);
        }, 3000);
    }

    // ===== EFECTOS HOVER EN TARJETAS BLOQUEADAS =====
    document.querySelectorAll('.stat-card-locked').forEach(function(card) {
        card.addEventListener('mouseenter', function() {
            const overlay = card.querySelector('.locked-overlay');
            if (overlay) {
                overlay.style.transform = 'scale(1.02)';
            }
        });

        card.addEventListener('mouseleave', function() {
            const overlay = card.querySelector('.locked-overlay');
            if (overlay) {
                overlay.style.transform = 'scale(1)';
            }
        });
    });

    // ===== ANIMACIÓN DE TARJETAS EN MOVIMIENTO =====
    function initCardAnimations() {
        const cards = document.querySelectorAll('.stat-card');

        cards.forEach(function(card, index) {
            // La animación CSS ya maneja fadeInUp
            // Aquí solo añadimos efectos de hover adicionales
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-4px)';
            });

            card.addEventListener('mouseleave', function() {
                this.style.transform = '';
            });
        });
    }

    // ===== RESPONSIVE HANDLING =====
    function handleResize() {
        const wrapper = document.querySelector('.dashboard-wrapper');
        if (wrapper && window.innerWidth < 768) {
            wrapper.classList.add('mobile-view');
        } else if (wrapper) {
            wrapper.classList.remove('mobile-view');
        }
    }

    window.addEventListener('resize', handleResize);

    // ===== INICIALIZACIÓN =====
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCardAnimations);
    } else {
        initCardAnimations();
    }

    handleResize();

})();
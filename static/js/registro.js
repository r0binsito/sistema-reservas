// ===== TIPO DE NEGOCIO =====
function mostrarOtro(valor) {
    const wrap = document.getElementById('tipo-otro-wrap');
    if (wrap) wrap.style.display = valor === 'Otro' ? 'block' : 'none';
}

// ===== VALIDAR PASSWORD =====
function validarPassword() {
    const password = document.querySelector('[name="password"]');
    const confirm = document.getElementById('password-confirm');
    const error = document.getElementById('password-error');
    if (!password || !confirm) return true;
    if (password.value !== confirm.value) {
        error.style.display = 'block';
        return false;
    }
    error.style.display = 'none';
    return true;
}

// ===== DRAG & DROP =====
document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('logo-dropzone');
    if (dropzone) {
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragover');
        });
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                const input = document.getElementById('logo-input');
                const dt = new DataTransfer();
                dt.items.add(file);
                input.files = dt.files;
                iniciarCropper(input);
            }
        });
    }

    // Limpiar input al abrir
    const logoInput = document.getElementById('logo-input');
    if (logoInput) {
        logoInput.addEventListener('click', function () {
            this.value = '';
        });
    }

    // Consejo animado
    const consejo = document.getElementById('consejo-senior');
    if (consejo) {
        const key = 'consejo_' + window.location.pathname;
        if (sessionStorage.getItem(key)) {
            consejo.style.display = 'none';
        } else {
            consejo.classList.add('consejo-animado');
            setTimeout(() => {
                consejo.style.display = 'none';
                sessionStorage.setItem(key, '1');
            }, 5000);
        }
    }
});

// ===== CROPPER =====
let cropperInstance = null;

function iniciarCropper(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function (e) {
            const modal = document.getElementById('modal-cropper');
            const img = document.getElementById('imagen-cropper');

            if (cropperInstance) {
                cropperInstance.destroy();
                cropperInstance = null;
            }

            // Reset sliders
            const sliderZoom = document.getElementById('slider-zoom');
            const sliderRot = document.getElementById('slider-rotacion');
            if (sliderZoom) sliderZoom.value = 1;
            if (sliderRot) sliderRot.value = 0;
            const valorZoom = document.getElementById('valor-zoom');
            const valorRot = document.getElementById('valor-rotacion');
            if (valorZoom) valorZoom.textContent = '1x';
            if (valorRot) valorRot.textContent = '0°';

            modal.style.display = 'flex';

            // Limpiar img anterior
            img.removeAttribute('src');
            img.style.display = 'block';

            setTimeout(() => {
                img.src = e.target.result;
                img.onload = function () {
                    setTimeout(() => {
                        cropperInstance = new Cropper(img, {
                            aspectRatio: 1,
                            viewMode: 1,
                            movable: true,
                            zoomable: true,
                            scalable: false,
                            cropBoxResizable: true,
                            ready() {
                                actualizarPreview();
                            },
                            cropend() {
                                actualizarPreview();
                            }
                        });
                    }, 50);
                };
            }, 50);
        };
        reader.readAsDataURL(input.files[0]);
    }
}

function actualizarPreview() {
    if (!cropperInstance) return;
    try {
        const canvas = cropperInstance.getCroppedCanvas({ width: 200, height: 200 });
        if (!canvas) return;
        const url = canvas.toDataURL('image/jpeg', 0.8);
        const prev1 = document.getElementById('preview-grande');
        const prev2 = document.getElementById('preview-chico');
        if (prev1) prev1.src = url;
        if (prev2) prev2.src = url;
    } catch(e) {
        console.log('Preview error:', e);
    }
}

function actualizarZoom(value) {
    const val = parseFloat(value);
    document.getElementById('valor-zoom').textContent = val.toFixed(1) + 'x';
    if (cropperInstance) cropperInstance.zoomTo(val);
}

function actualizarRotacion(value) {
    const val = parseInt(value);
    document.getElementById('valor-rotacion').textContent = val + '°';
    if (cropperInstance) cropperInstance.rotateTo(val);
}

function editarValorZoom() {
    const input = document.getElementById('valor-zoom');
    const slider = document.getElementById('slider-zoom');
    const val = input.textContent.replace('x', '').trim();
    const nuevo = prompt('Ingresa el zoom (0.1 — 3):', val);
    if (nuevo !== null) {
        const num = Math.min(3, Math.max(0.1, parseFloat(nuevo) || 1));
        slider.value = num;
        actualizarZoom(num);
    }
}

function editarValorRotacion() {
    const input = document.getElementById('valor-rotacion');
    const slider = document.getElementById('slider-rotacion');
    const val = input.textContent.replace('°', '').trim();
    const nuevo = prompt('Ingresa la rotación (-180 — 180):', val);
    if (nuevo !== null) {
        const num = Math.min(180, Math.max(-180, parseInt(nuevo) || 0));
        slider.value = num;
        actualizarRotacion(num);
    }
}

function cambiarZoom(delta) {
    const slider = document.getElementById('slider-zoom');
    const nuevo = Math.min(3, Math.max(0.1, parseFloat(slider.value) + delta));
    slider.value = nuevo;
    actualizarZoom(nuevo);
}

function cambiarRotacion(delta) {
    const slider = document.getElementById('slider-rotacion');
    const nuevo = Math.min(180, Math.max(-180, parseInt(slider.value) + delta));
    slider.value = nuevo;
    actualizarRotacion(nuevo);
}

function confirmarCropper() {
    if (cropperInstance) {
        const canvas = cropperInstance.getCroppedCanvas({ width: 400, height: 400 });
        const base64 = canvas.toDataURL('image/jpeg', 0.9);
        document.getElementById('logo-recortado').value = base64;

        // Mostrar preview en el dropzone
        const dropzone = document.getElementById('logo-dropzone');
        const contenido = document.getElementById('dropzone-contenido');
        if (dropzone && contenido) {
            contenido.innerHTML = `
                <img src="${base64}" style="width:80px; height:80px; border-radius:50%; object-fit:cover; border:2px solid rgba(250,143,62,0.5); margin-bottom:0.5rem;">
                <p style="font-size:0.82rem; color:rgba(255,255,255,0.6); margin:0;">Logo seleccionado ✓</p>
                <p style="font-size:0.72rem; color:rgba(250,143,62,0.6); margin:0.2rem 0 0;">Haz clic para cambiar</p>
            `;
        }
        cancelarCropper();
    }
}

function cancelarCropper() {
    const modal = document.getElementById('modal-cropper');
    if (modal) modal.style.display = 'none';
    if (cropperInstance) {
        cropperInstance.destroy();
        cropperInstance = null;
    }
}
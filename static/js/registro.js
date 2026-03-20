function mostrarOtro(valor) {
    const wrap = document.getElementById('tipo-otro-wrap');
    if (wrap) wrap.style.display = valor === 'Otro' ? 'block' : 'none';
}

function validarPassword() {
    const password = document.querySelector('[name="password"]').value;
    const confirm = document.getElementById('password-confirm').value;
    const error = document.getElementById('password-error');

    if (password !== confirm) {
        error.style.display = 'block';
        return false;
    }
    error.style.display = 'none';
    return true;
}

let cropperInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    const logoInput = document.getElementById('logo-input');
    if (logoInput) {
        logoInput.addEventListener('click', function() {
            this.value = '';
        });
    }
});

function iniciarCropper(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const modal = document.getElementById('modal-cropper');
            const img = document.getElementById('imagen-cropper');
            if (cropperInstance) {
                cropperInstance.destroy();
                cropperInstance = null;
            }
            img.src = e.target.result;
            modal.style.display = 'flex';
            img.onload = function() {
                cropperInstance = new Cropper(img, {
                    aspectRatio: 1,
                    viewMode: 1,
                    movable: true,
                    zoomable: true,
                    scalable: false,
                    cropBoxResizable: true
                });
            }
        }
        reader.readAsDataURL(input.files[0]);
    }
}

function confirmarCropper() {
    if (cropperInstance) {
        const canvas = cropperInstance.getCroppedCanvas({ width: 400, height: 400 });
        const base64 = canvas.toDataURL('image/jpeg', 0.9);
        document.getElementById('logo-recortado').value = base64;
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
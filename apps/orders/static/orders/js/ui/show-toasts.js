export function showToasts() {
    document.querySelectorAll('.toast').forEach(function (toastEl) {
        const toast = new bootstrap.Toast(toastEl, { autohide: false });
        toastEl.classList.add('slide-in');
        toast.show();
        setTimeout(() => {
            toastEl.classList.remove('slide-in');
            toastEl.classList.add('slide-out');
            toastEl.addEventListener('animationend', () => {
                toastEl.remove();
            }, { once: true });
        }, 7000);
    });
}

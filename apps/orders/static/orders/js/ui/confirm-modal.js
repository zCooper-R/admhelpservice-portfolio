function getConfirmModalContainer() {
  let container = document.getElementById("confirmModalContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "confirmModalContainer";
    document.body.appendChild(container);
  }
  return container;
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function buildConfirmModalHtml({
  title = "Подтверждение",
  kicker = "Подтверждение",
  heading = "Подтвердите действие",
  message = "Вы уверены, что хотите продолжить?",
  hint = "",
  confirmText = "Подтвердить",
  cancelText = "Отмена",
  confirmButtonClass = "btn-primary",
  confirmIconClass = "",
}) {
  const iconHtml = confirmIconClass ? `<i class="${escapeHtml(confirmIconClass)}"></i>` : "";
  const hintHtml = hint
    ? `<p class="mb-0 text-body-secondary">${escapeHtml(hint)}</p>`
    : "";

  return `
    <div class="modal fade text-black orders-modal" id="confirmActionModal" tabindex="-1" aria-hidden="true" data-bs-backdrop="static">
      <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable orders-modal-dialog--confirm">
        <div class="modal-content orders-modal-shell">
          <div class="modal-header orders-modal-header">
            <div class="orders-modal-heading">
              <div class="orders-modal-kicker">${escapeHtml(kicker)}</div>
              <h3 class="modal-title orders-modal-title">${escapeHtml(title)}</h3>
            </div>
            <button type="button" class="btn-close orders-modal-close" data-bs-dismiss="modal" title="Закрыть" aria-label="Close"></button>
          </div>
          <div class="modal-body orders-modal-body">
            <div class="orders-modal-section">
              <div class="orders-modal-section__header">
                <div class="orders-modal-section__eyebrow">${escapeHtml(kicker)}</div>
                <h4 class="orders-modal-section__title">${escapeHtml(heading)}</h4>
              </div>
              <div class="orders-detail-grid">
                <div class="orders-detail-card orders-detail-card--wide">
                  <div class="orders-detail-card__value orders-detail-card__value--text">
                    <p>${escapeHtml(message)}</p>
                    ${hintHtml}
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer orders-modal-footer">
            <button type="button" class="btn btn-sm btn-outline-secondary d-inline-flex align-items-center justify-content-center" data-bs-dismiss="modal">${escapeHtml(cancelText)}</button>
            <button type="button" class="btn btn-sm ${escapeHtml(confirmButtonClass)} d-inline-flex align-items-center justify-content-center gap-2" data-confirm-accept>
              ${iconHtml}
              <span>${escapeHtml(confirmText)}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
}

export function openConfirmModal(options = {}) {
  return new Promise((resolve) => {
    const container = getConfirmModalContainer();
    container.innerHTML = buildConfirmModalHtml(options);

    const modalEl = document.getElementById("confirmActionModal");
    if (!modalEl) {
      resolve(false);
      return;
    }

    let settled = false;
    const settle = (result) => {
      if (settled) {
        return;
      }
      settled = true;
      resolve(result);
    };

    modalEl.querySelector("[data-confirm-accept]")?.addEventListener("click", () => {
      settle(true);
      bootstrap.Modal.getInstance(modalEl)?.hide();
    });

    modalEl.addEventListener(
      "hidden.bs.modal",
      () => {
        container.innerHTML = "";
        settle(false);
      },
      { once: true },
    );

    new bootstrap.Modal(modalEl).show();
  });
}

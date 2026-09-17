import { initializeHelpPopovers } from "../ui/init-help-popovers.js";
import { showToasts } from "../ui/show-toasts.js";
import { initializeOrderDescriptionCollapse } from "../ui/order-printer-description-collapse.js";
import { openConfirmModal } from "../ui/confirm-modal.js";
import { initializeBootstrapPopovers } from "../ui/init-popovers.js";
import { initializeTransportForm } from "../ui/order-transport-form.js";
import { initializeVksFields } from "../ui/order-vks-fields.js";
import { initializeDiscussionPanel } from "../../../order_communication/js/discussion-panel.js";
import { initializeDiscussionLazyTab } from "../../../order_communication/js/discussion-lazy-tab.js";
import { initializeThreadPolling } from "../../../order_communication/js/thread-polling.js";

function getModalContainer() {
  let container = document.getElementById("modalContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "modalContainer";
    document.body.appendChild(container);
  }
  return container;
}

function cleanupModalArtifacts() {
  document.querySelectorAll(".modal-backdrop").forEach((el) => el.remove());
  document.body.classList.remove("modal-open");
  document.body.style.removeProperty("padding-right");
}

function getCsrfToken(container = document) {
  const input = container.querySelector("input[name='csrfmiddlewaretoken']");
  if (input) {
    return input.value;
  }

  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

function clearFieldErrors(form) {
  form.querySelectorAll(".is-invalid").forEach((field) => field.classList.remove("is-invalid"));
  form.querySelectorAll(".server-error").forEach((node) => node.remove());
}

function renderServerErrors(form, errors = {}) {
  clearFieldErrors(form);

  Object.entries(errors).forEach(([name, messages]) => {
    const field = form.querySelector(`[name="${name}"]`);
    if (!field) {
      return;
    }

    field.classList.add("is-invalid");
    const feedback = document.createElement("div");
    feedback.className = "invalid-feedback server-error d-block";
    feedback.textContent = Array.isArray(messages) ? messages.join(" ") : String(messages);
    field.insertAdjacentElement("afterend", feedback);
  });
}

function validateVksEquipmentGroup(form) {
  if (form.id !== "vks") {
    return true;
  }

  const categorySelect = form.querySelector("#id_category");
  const modalRoot = form.closest(".orders-modal");
  const connectValue = Number(modalRoot?.dataset.vksConnect);
  const selectedCategory = Number(categorySelect?.value);
  if (!categorySelect || selectedCategory !== connectValue) {
    return true;
  }

  const equipmentFields = Array.from(form.querySelectorAll("input[name='equipment']"));
  if (!equipmentFields.length) {
    return true;
  }

  const hasChecked = equipmentFields.some((field) => field.checked);
  const groupWrap = equipmentFields[0].closest(".form-group");

  equipmentFields.forEach((field) => field.classList.remove("is-invalid"));
  groupWrap?.querySelectorAll(".server-error").forEach((node) => node.remove());

  if (hasChecked) {
    return true;
  }

  equipmentFields.forEach((field) => field.classList.add("is-invalid"));
  if (groupWrap) {
    const feedback = document.createElement("div");
    feedback.className = "invalid-feedback server-error d-block";
    feedback.textContent = "Выберите, что должно работать во время подключения.";
    groupWrap.appendChild(feedback);
  }
  equipmentFields[0].focus();
  return false;
}

async function confirmIfNeeded(source) {
  const confirmMessage = source?.dataset?.confirm;
  if (!confirmMessage) {
    return true;
  }

  return openConfirmModal({
    title: source.dataset.confirmTitle || "Подтверждение",
    kicker: source.dataset.confirmKicker || "Подтверждение",
    heading: source.dataset.confirmHeading || "Подтвердите действие",
    message: confirmMessage,
    hint: source.dataset.confirmHint || "",
    confirmText: source.dataset.confirmButtonText || "Подтвердить",
    cancelText: source.dataset.confirmCancelText || "Отмена",
    confirmButtonClass: source.dataset.confirmButtonClass || "btn-primary",
    confirmIconClass: source.dataset.confirmIcon || "",
  });
}

function initializeModalEnhancements(modalEl) {
  const form = modalEl.querySelector("form[name='orderForm']");
  initializeHelpPopovers(modalEl);
  initializeBootstrapPopovers(modalEl);
  initializeDiscussionPanel(modalEl);
  initializeDiscussionLazyTab(modalEl);
  initializeThreadPolling(modalEl);

  if (!form) {
    return;
  }

  switch (form.id) {
    case "printer":
      initializeOrderDescriptionCollapse(form);
      break;
    case "transport":
      initializeTransportForm(form);
      break;
    case "vks":
      initializeVksFields(form);
      break;
    default:
      break;
  }

  form.classList.add("needs-validation");
  form.addEventListener("submit", async function (e) {
    if (!form.checkValidity() || !validateVksEquipmentGroup(form)) {
      e.preventDefault();
      e.stopPropagation();
      form.classList.add("was-validated");
      const firstInvalid = form.querySelector(".form-control:invalid, .form-select:invalid, .is-invalid");
      if (firstInvalid) {
        firstInvalid.focus();
      }
      return;
    }

    e.preventDefault();
    clearFieldErrors(form);

    const submitter = e.submitter || form.querySelector("button[type=submit]");
    const isConfirmed = await confirmIfNeeded(submitter || form);
    if (!isConfirmed) {
      return;
    }

    const button = form.querySelector("button[type=submit]");
    const originalText = button ? button.innerHTML : "";
    if (button) {
      button.innerHTML = "Отправка...";
      button.disabled = true;
    }

    try {
      const csrfToken = getCsrfToken(form);
      const response = await fetch(form.action, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrfToken,
        },
        credentials: "same-origin",
        body: new FormData(form),
      });
      const data = await response.json();

      if (!response.ok || !data.success) {
        renderServerErrors(form, data.errors);
        return;
      }

      const modal = bootstrap.Modal.getInstance(modalEl);
      if (modal) {
        modal.hide();
      }

      const toastContainer = document.getElementById("toast-container");
      if (toastContainer && data.messages_html) {
        toastContainer.insertAdjacentHTML("beforeend", data.messages_html);
        showToasts();
      }

      document.dispatchEvent(new CustomEvent("orders:changed"));
    } finally {
      if (button) {
        button.innerHTML = originalText;
        button.disabled = false;
      }
    }
  });
}

function focusFirstInteractiveField(modalEl) {
  const selector = [
    "input:not([type='hidden']):not([readonly]):not([disabled])",
    "select:not([disabled])",
    "textarea:not([readonly]):not([disabled])",
  ].join(", ");
  const field = modalEl.querySelector(selector);
  if (field) {
    field.focus();
  }
}

function bindEscapeClose(modalEl) {
  modalEl.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }

    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) {
      modal.hide();
    }
  });
}

function openDiscussionTab(modalEl) {
  const discussionTab = modalEl?.querySelector("#order-discussion-tab");
  if (!discussionTab) {
    return;
  }

  bootstrap.Tab.getOrCreateInstance(discussionTab).show();
}

export async function openOrderModal(url, { openDiscussion = false } = {}) {
  const response = await fetch(url, {
    headers: { "X-Requested-With": "XMLHttpRequest" },
  });
  const html = await response.text();

  const tempContainer = document.createElement("div");
  tempContainer.innerHTML = html;
  const incomingModalEl = tempContainer.querySelector("#orderFormModal");
  if (!incomingModalEl) {
    return;
  }

  const currentModalEl = document.getElementById("orderFormModal");
  const currentModalInstance = currentModalEl
    ? bootstrap.Modal.getInstance(currentModalEl)
    : null;
  const isModalAlreadyOpen = Boolean(
    currentModalEl &&
    currentModalInstance &&
    currentModalEl.classList.contains("show"),
  );

  if (isModalAlreadyOpen) {
    const currentDialog = currentModalEl.querySelector(".modal-dialog");
    const incomingDialog = incomingModalEl.querySelector(".modal-dialog");

    if (!currentDialog || !incomingDialog) {
      return;
    }

    currentDialog.className = incomingDialog.className;
    currentDialog.innerHTML = incomingDialog.innerHTML;
    initializeModalEnhancements(currentModalEl);
    if (openDiscussion) {
      openDiscussionTab(currentModalEl);
    }
    focusFirstInteractiveField(currentModalEl);
    return;
  }

  cleanupModalArtifacts();

  const container = getModalContainer();
  container.innerHTML = incomingModalEl.outerHTML;

  const modalEl = document.getElementById("orderFormModal");
  if (!modalEl) {
    return;
  }

  initializeModalEnhancements(modalEl);
  bindEscapeClose(modalEl);

  modalEl.addEventListener(
    "shown.bs.modal",
    () => {
      if (openDiscussion) {
        openDiscussionTab(modalEl);
        return;
      }
      focusFirstInteractiveField(modalEl);
    },
    { once: true },
  );

  modalEl.addEventListener(
    "hidden.bs.modal",
    () => {
      container.innerHTML = "";
      cleanupModalArtifacts();
    },
    { once: true },
  );

  new bootstrap.Modal(modalEl).show();
}

export function initializeFormModal() {
  if (document.body.dataset.orderModalInitialized === "true") {
    return;
  }
  document.body.dataset.orderModalInitialized = "true";

  document.addEventListener("keydown", async function (event) {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    const discussionTrigger = event.target.closest("[data-order-discussion-row-badge]");
    if (!discussionTrigger) {
      return;
    }

    event.preventDefault();
    const url = discussionTrigger.dataset.orderDiscussionUrl;
    if (url) {
      await openOrderModal(url, { openDiscussion: true });
    }
  });

  document.addEventListener("click", async function (event) {
    const discussionTrigger = event.target.closest("[data-order-discussion-row-badge]");
    if (discussionTrigger) {
      event.preventDefault();
      const url = discussionTrigger.dataset.orderDiscussionUrl;
      if (url) {
        await openOrderModal(url, { openDiscussion: true });
      }
      return;
    }

    const modalTrigger = event.target.closest(".openOrderFormBtn, .openOrderModalBtn, .detail-order");
    if (modalTrigger) {
      event.preventDefault();
      const url = modalTrigger.dataset.url || modalTrigger.dataset.formUrl;
      if (url) {
        await openOrderModal(url);
      }
      return;
    }

    const actionTrigger = event.target.closest(".notifyOrderActionBtn");
    if (!actionTrigger) {
      return;
    }

    event.preventDefault();
    const isConfirmed = await confirmIfNeeded(actionTrigger);
    if (!isConfirmed) {
      return;
    }

    const response = await fetch(actionTrigger.dataset.postUrl, {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrfToken(),
      },
      credentials: "same-origin",
    });

    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (!response.ok || data?.success === false) {
      window.alert("Не удалось выполнить действие.");
      return;
    }

    const toastContainer = document.getElementById("toast-container");
    if (toastContainer && data?.messages_html) {
      toastContainer.insertAdjacentHTML("beforeend", data.messages_html);
      showToasts();
    }

    document.dispatchEvent(new CustomEvent("orders:changed"));

    if (data?.detail_url) {
      await openOrderModal(data.detail_url);
      return;
    }

    window.alert(actionTrigger.dataset.successMessage || "Действие выполнено.");
  });
}

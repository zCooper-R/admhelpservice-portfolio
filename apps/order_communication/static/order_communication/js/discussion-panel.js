import { markThreadReadForRoot, scrollThreadTimelineToRelevantPosition, syncDiscussionBadge } from "./thread-polling.js";
import { isActiveStatus, renderStatusWithIcon, renderWaitingForCell } from "../../orders/js/renderers.js";

function getCsrfToken(container = document) {
  const input = container.querySelector("input[name='csrfmiddlewaretoken']");
  if (input) {
    return input.value;
  }

  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

function formatFileSize(size) {
  if (!size) {
    return "";
  }
  if (size < 1024) {
    return `${size} Б`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} КБ`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} МБ`;
}

function renderSelectedFiles(input) {
  const form = input.closest("[data-order-thread-composer]");
  if (!form) {
    return;
  }

  const fileList = form.querySelector("[data-order-thread-file-list]");
  if (!fileList) {
    return;
  }

  const files = Array.from(input.files || []);
  if (!files.length) {
    fileList.innerHTML = "";
    fileList.hidden = true;
    return;
  }

  fileList.hidden = false;
  fileList.replaceChildren();
  files.forEach((file, index) => {
    const item = document.createElement("div");
    item.className = "order-thread__selected-file";
    item.dataset.fileIndex = String(index);

    const meta = document.createElement("div");
    meta.className = "order-thread__selected-file-meta";

    const name = document.createElement("span");
    name.className = "order-thread__selected-file-name";
    name.textContent = file.name;

    const size = document.createElement("span");
    size.className = "order-thread__selected-file-size";
    size.textContent = formatFileSize(file.size);

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "order-thread__selected-file-remove";
    removeButton.dataset.removeFileIndex = String(index);
    removeButton.setAttribute("aria-label", "Удалить файл");
    removeButton.textContent = "×";

    meta.append(name, size);
    item.append(meta, removeButton);
    fileList.appendChild(item);
  });
}

function removeSelectedFile(button) {
  const form = button.closest("[data-order-thread-composer]");
  if (!form) {
    return;
  }

  const input = form.querySelector("input[type='file']");
  if (!input || !input.files || typeof DataTransfer === "undefined") {
    return;
  }

  const removeIndex = Number(button.dataset.removeFileIndex);
  if (Number.isNaN(removeIndex)) {
    return;
  }

  const dataTransfer = new DataTransfer();
  Array.from(input.files).forEach((file, index) => {
    if (index !== removeIndex) {
      dataTransfer.items.add(file);
    }
  });

  input.files = dataTransfer.files;
  renderSelectedFiles(input);
}

function activateComposerPane(root, targetType) {
  const switcher = root.querySelector("[data-order-thread-composer-switcher]");
  if (!switcher) {
    return;
  }

  root.querySelectorAll("[data-order-thread-composer-pane]").forEach((pane) => {
    const isActive = pane.dataset.orderThreadComposerPane === targetType;
    pane.hidden = !isActive;
    pane.dataset.isActive = isActive ? "true" : "false";
  });

  switcher.querySelectorAll("[data-composer-target]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.composerTarget === targetType);
  });
}

function applyImmediateOrderSummary(modalRoot, orderId, summary = {}) {
  if (!orderId || !summary) {
    return;
  }

  const normalizedOrderId = String(orderId);
  const openModal = modalRoot?.closest?.(".orders-modal") || modalRoot;

  if (summary.status && openModal && String(openModal.dataset.orderId || "") === normalizedOrderId) {
    openModal.querySelectorAll("[data-order-status-value]").forEach((node) => {
      node.textContent = summary.status;
    });
  }

  if (summary.waiting_for && openModal && String(openModal.dataset.orderId || "") === normalizedOrderId) {
    openModal.querySelectorAll("[data-order-waiting-value]").forEach((node) => {
      node.textContent = summary.waiting_for;
    });
  }

  const row = document.getElementById(`order-${normalizedOrderId}`);
  if (!row) {
    return;
  }

  if (summary.status) {
    const statusCell = row.querySelector("td.dt-col-status");
    if (statusCell) {
      statusCell.innerHTML = renderStatusWithIcon(summary.status);
    }
    row.classList.toggle("orders-row--active", isActiveStatus(summary.status));
  }

  if (summary.waiting_for) {
    const waitingCell = row.querySelector("td.dt-col-waiting_for");
    if (waitingCell) {
      waitingCell.innerHTML = renderWaitingForCell(summary.waiting_for);
    }
  }
}

function applyImmediateThreadSummary(modalRoot, summary = {}) {
  if (!modalRoot || !summary) {
    return;
  }

  const metaNodes = modalRoot.querySelectorAll("[data-order-thread-meta]");
  if (!metaNodes.length) {
    return;
  }

  const messagesCount = Number(summary.messages_count || 0);
  const latestVisibleMessageAt = summary.latest_visible_message_at || "";
  const text = latestVisibleMessageAt
    ? `Сообщений: ${messagesCount} • обновлено ${latestVisibleMessageAt}`
    : `Сообщений: ${messagesCount}`;

  metaNodes.forEach((node) => {
    node.textContent = text;
  });
}

async function submitComposer(form) {
  const response = await fetch(form.action, {
    method: "POST",
    headers: {
      "X-Requested-With": "XMLHttpRequest",
      "X-CSRFToken": getCsrfToken(form),
    },
    credentials: "same-origin",
    body: new FormData(form),
  });

  const payload = await response.json();
  if (!response.ok || !payload.success) {
    window.alert("Не удалось отправить сообщение. Проверьте заполнение формы.");
    return payload;
  }

  const modalRoot = form.closest(".orders-modal") || document;
  const threadRoot = form.closest("[data-order-thread-root]");
  if (threadRoot && payload.thread_html) {
    threadRoot.outerHTML = payload.thread_html;
    const nextThreadRoot = modalRoot.querySelector("[data-order-thread-root]");
    const orderId = nextThreadRoot?.dataset.orderId || threadRoot.dataset.orderId || modalRoot.dataset.orderId;
    if (nextThreadRoot) {
      window.requestAnimationFrame(() => {
        scrollThreadTimelineToRelevantPosition(nextThreadRoot, { behavior: "auto" });
      });
    }
    if (orderId && payload.order_summary) {
      applyImmediateOrderSummary(modalRoot, orderId, payload.order_summary);
    }
    if (payload.thread_summary) {
      applyImmediateThreadSummary(modalRoot, payload.thread_summary);
    }
    syncDiscussionBadge(modalRoot, payload.unread_count || 0);
    if (Number(payload.unread_count || 0) > 0) {
      await markThreadReadForRoot(modalRoot);
    }
    document.dispatchEvent(new CustomEvent("orders:summary-refresh"));
  }
  return payload;
}

export function initializeDiscussionPanel(root = document) {
  if (root.dataset && root.dataset.orderDiscussionInitialized === "true") {
    return;
  }
  if (root.dataset) {
    root.dataset.orderDiscussionInitialized = "true";
  }

  root.addEventListener("submit", (event) => {
    const form = event.target.closest("[data-order-thread-composer]");
    if (!form) {
      return;
    }

    event.preventDefault();
    submitComposer(form).catch(() => null);
  });

  root.addEventListener("click", (event) => {
    const switchButton = event.target.closest("[data-composer-target]");
    if (switchButton) {
      const threadRoot = switchButton.closest("[data-order-thread-root]");
      if (threadRoot) {
        activateComposerPane(threadRoot, switchButton.dataset.composerTarget);
      }
      return;
    }

    const removeButton = event.target.closest("[data-remove-file-index]");
    if (removeButton) {
      removeSelectedFile(removeButton);
    }
  });

  root.addEventListener("change", (event) => {
    const fileInput = event.target.closest("[data-order-thread-composer] input[type='file']");
    if (fileInput) {
      renderSelectedFiles(fileInput);
    }
  });
}

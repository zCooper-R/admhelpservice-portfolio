import { fetchNotificationsPanel, applyNotificationSummary } from "./notifications-center.js";
import { syncDiscussionBadge } from "../../../order_communication/js/thread-polling.js";
import { isActiveStatus, renderStatusWithIcon, renderWaitingForCell } from "../renderers.js";

function initializeTooltips(container) {
  if (!container) {
    return;
  }

  container.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((tooltipEl) => {
    const existing = bootstrap.Tooltip.getInstance(tooltipEl);
    if (existing) {
      existing.dispose();
    }
    bootstrap.Tooltip.getOrCreateInstance(tooltipEl);
  });
}

function disposeTooltips(container) {
  if (!container) {
    return;
  }

  container.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((tooltipEl) => {
    const existing = bootstrap.Tooltip.getInstance(tooltipEl);
    if (existing) {
      existing.dispose();
    }
  });

  document.querySelectorAll(".tooltip").forEach((tooltipEl) => {
    tooltipEl.remove();
  });
}

function getSummaryUrl() {
  return document.body?.dataset?.globalSummaryUrl || "";
}

function isDiscussionTabActive(modalRoot) {
  const pane = modalRoot?.querySelector("#order-discussion-pane");
  return Boolean(pane && pane.classList.contains("active"));
}

function getVisibleOrderIds() {
  const ids = new Set();

  document.querySelectorAll("tr[id^='order-']").forEach((row) => {
    const value = row.id.replace("order-", "");
    if (value) {
      ids.add(value);
    }
  });

  const openModal = document.querySelector(".orders-modal.show");
  const discussionPane = openModal?.querySelector("#order-discussion-pane");
  const lazyPane = discussionPane?.querySelector("[data-order-discussion-lazy-pane]");
  const threadRoot = discussionPane?.querySelector("[data-order-thread-root]");
  const modalOrderId = openModal?.dataset.orderId || threadRoot?.dataset.orderId || lazyPane?.dataset.orderId;
  if (modalOrderId) {
    ids.add(modalOrderId);
  }

  return [...ids].filter(Boolean);
}

function updateOrderRowBadge(orderId, unreadCount) {
  const row = document.getElementById(`order-${orderId}`);
  if (!row) {
    return;
  }

  const badge = row.querySelector("[data-order-discussion-row-badge]");
  const countNode = row.querySelector("[data-order-discussion-row-count]");
  if (!badge || !countNode) {
    return;
  }

  const normalizedCount = Number(unreadCount || 0);
  countNode.textContent = String(normalizedCount);
  badge.hidden = normalizedCount <= 0;
}

function updateModalDiscussionBadge(orderId, unreadCount) {
  const openModal = document.querySelector(".orders-modal.show");
  if (!openModal || isDiscussionTabActive(openModal)) {
    return;
  }

  const discussionPane = openModal.querySelector("#order-discussion-pane");
  const lazyPane = discussionPane?.querySelector("[data-order-discussion-lazy-pane]");
  const threadRoot = discussionPane?.querySelector("[data-order-thread-root]");
  const currentOrderId = threadRoot?.dataset.orderId || lazyPane?.dataset.orderId;

  if (!currentOrderId || String(currentOrderId) !== String(orderId)) {
    return;
  }

  if (threadRoot) {
    threadRoot.dataset.unreadCount = String(Number(unreadCount || 0));
  }
  syncDiscussionBadge(openModal, unreadCount);
}

function updateOrderRowStatus(orderId, status) {
  const row = document.getElementById(`order-${orderId}`);
  if (!row || !status) {
    return;
  }

  const statusCell = row.querySelector("td.dt-col-status");
  if (statusCell) {
    disposeTooltips(statusCell);
    statusCell.innerHTML = renderStatusWithIcon(status);
    initializeTooltips(statusCell);
  }

  row.classList.toggle("orders-row--active", isActiveStatus(status));
}

function updateModalStatus(orderId, status) {
  const openModal = document.querySelector(".orders-modal.show");
  if (!openModal || !status) {
    return;
  }

  if (String(openModal.dataset.orderId || "") !== String(orderId)) {
    return;
  }

  openModal.querySelectorAll("[data-order-status-value]").forEach((node) => {
    node.textContent = status;
  });
}

function updateOrderRowWaiting(orderId, waitingInfo) {
  const row = document.getElementById(`order-${orderId}`);
  if (!row || !waitingInfo) {
    return;
  }

  const waitingCell = row.querySelector("td.dt-col-waiting_for");
  if (waitingCell) {
    disposeTooltips(waitingCell);
    waitingCell.innerHTML = renderWaitingForCell(waitingInfo);
    initializeTooltips(waitingCell);
  }
}

function updateModalWaiting(orderId, waitingInfo) {
  const openModal = document.querySelector(".orders-modal.show");
  if (!openModal || !waitingInfo) {
    return;
  }

  if (String(openModal.dataset.orderId || "") !== String(orderId)) {
    return;
  }

  openModal.querySelectorAll("[data-order-waiting-value]").forEach((node) => {
    node.textContent = waitingInfo.label || "";
  });

  openModal.querySelectorAll("[data-order-waiting-detail]").forEach((node) => {
    node.textContent = waitingInfo.detail || "";
    node.classList.remove("orders-detail-card__meta--warning", "orders-detail-card__meta--overdue");
    if (waitingInfo.sla_state === "warning") {
      node.classList.add("orders-detail-card__meta--warning");
    }
    if (waitingInfo.sla_state === "overdue") {
      node.classList.add("orders-detail-card__meta--overdue");
    }
    node.hidden = !waitingInfo.detail;
  });
}

function applyDiscussionSummary(counts) {
  const normalizedCounts = counts || {};
  const visibleOrderIds = getVisibleOrderIds();

  visibleOrderIds.forEach((orderId) => {
    const unreadCount = Number(normalizedCounts[orderId] || 0);
    updateOrderRowBadge(orderId, unreadCount);
    updateModalDiscussionBadge(orderId, unreadCount);
  });
}

function applyOrderSummary(statuses) {
  const normalizedStatuses = statuses || {};
  const visibleOrderIds = getVisibleOrderIds();

  visibleOrderIds.forEach((orderId) => {
    const status = normalizedStatuses[orderId];
    updateOrderRowStatus(orderId, status);
    updateModalStatus(orderId, status);
  });
}

function applyWaitingSummary(waitingMap) {
  const normalizedWaitingMap = waitingMap || {};
  const visibleOrderIds = getVisibleOrderIds();

  visibleOrderIds.forEach((orderId) => {
    const waitingInfo = normalizedWaitingMap[orderId];
    updateOrderRowWaiting(orderId, waitingInfo);
    updateModalWaiting(orderId, waitingInfo);
  });
}

export function applyImmediateOrderSummary(orderId, summary = {}) {
  if (!orderId || !summary) {
    return;
  }

  if (summary.status) {
    updateOrderRowStatus(orderId, summary.status);
    updateModalStatus(orderId, summary.status);
  }

  if (summary.waiting_for) {
    updateOrderRowWaiting(orderId, summary.waiting_for);
    updateModalWaiting(orderId, summary.waiting_for);
  }
}

async function fetchGlobalSummary() {
  const summaryUrl = getSummaryUrl();
  if (!summaryUrl) {
    return null;
  }

  const url = new URL(summaryUrl, window.location.origin);
  getVisibleOrderIds().forEach((orderId) => {
    url.searchParams.append("order_ids", orderId);
  });

  const response = await fetch(url.toString(), {
    headers: {
      "X-Requested-With": "XMLHttpRequest",
    },
    credentials: "same-origin",
  });

  if (!response.ok) {
    throw new Error("Failed to fetch global summary");
  }

  return response.json();
}

async function refreshGlobalSummary() {
  const payload = await fetchGlobalSummary();
  if (!payload) {
    return null;
  }

  const notificationCenter = document.querySelector("[data-notification-center]");
  if (notificationCenter && payload.notifications) {
    applyNotificationSummary(notificationCenter, payload.notifications);
    const openMenu = notificationCenter.querySelector(".orders-topbar__dropdown.show");
    if (openMenu) {
      fetchNotificationsPanel(notificationCenter).catch(() => null);
    }
  }

  applyDiscussionSummary(payload.discussion?.counts);
  applyOrderSummary(payload.orders?.statuses);
  applyWaitingSummary(payload.orders?.waiting);
  return payload;
}

export function initializeGlobalSummaryPolling() {
  if (document.body?.dataset?.globalSummaryPollingInitialized === "true") {
    return;
  }
  if (document.body) {
    document.body.dataset.globalSummaryPollingInitialized = "true";
  }

  refreshGlobalSummary().catch(() => null);

  document.addEventListener("orders:summary-refresh", () => {
    refreshGlobalSummary().catch(() => null);
  });

  window.setInterval(() => {
    if (document.visibilityState !== "visible") {
      return;
    }
    refreshGlobalSummary().catch(() => null);
  }, 10000);
}

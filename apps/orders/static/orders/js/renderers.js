const STATUS_MAP = {
  "В очереди": {
    icon: "fa-hourglass-start",
    badgeClass: "badge bg-secondary",
    hint: "Заявка принята и ожидает, когда специалист возьмёт её в работу.",
  },
  "В работе": {
    icon: "fa-spinner fa-spin",
    badgeClass: "badge bg-info text-dark",
    hint: "По заявке уже идёт работа или назначен ответственный специалист.",
  },
  "Выполнена": {
    icon: "fa-check",
    badgeClass: "badge bg-success",
    hint: "Работы по заявке завершены.",
  },
  "Закрыта": {
    icon: "fa-lock",
    badgeClass: "badge bg-warning text-dark",
    hint: "Заявка закрыта и не требует дополнительных действий.",
  },
  "Отменена": {
    icon: "fa-times",
    badgeClass: "badge bg-danger",
    hint: "Заявка отменена и не будет выполняться.",
  },
};

const WAITING_MAP = {
  "Ждёт исполнителя": {
    shortLabel: "Исполнитель",
    variant: "executor",
  },
  "Ждёт заявителя": {
    shortLabel: "Заявитель",
    variant: "requester",
  },
  "Не ожидает ответа": {
    shortLabel: "—",
    variant: "none",
  },
};

export function renderCategoryCell(data, type, row) {
  const unreadCount = Number(row?.discussion_unread_count || 0);
  const badgeHtml = `
    <span
      class="orders-discussion-badge"
      data-order-discussion-row-badge
      data-order-discussion-url="${row?.url || "#"}"
      role="button"
      tabindex="0"
      title="Новые сообщения в обсуждении"
      ${unreadCount > 0 ? "" : "hidden"}
    >
      <i class="fas fa-comment-dots" aria-hidden="true"></i>
      <span data-order-discussion-row-count>${unreadCount}</span>
    </span>
  `;

  return `
    <div class="orders-category-cell" title="${data}">
      <span class="orders-category-chip">${data}</span>
      ${badgeHtml}
    </div>
  `;
}

export function renderClientCell(data) {
  return `
    <div class="orders-client-cell" title="${data}">
      <span class="orders-client-cell__avatar">
        <i class="fas fa-user"></i>
      </span>
      <span class="orders-client-cell__name">${data}</span>
    </div>
  `;
}

export function renderExecutorCell(data) {
  const isAssigned = data && data !== "Не назначен";
  const chipClass = isAssigned ? "orders-category-chip" : "orders-category-chip orders-category-chip--muted";
  return `
    <span class="${chipClass}" title="${data}">
      ${data}
    </span>
  `;
}

export function renderStatusWithIcon(data) {
  const config = STATUS_MAP[data] || {
    icon: "fa-circle-info",
    badgeClass: "badge bg-dark",
    hint: "Текущий статус заявки.",
  };

  return `
    <span
      class="${config.badgeClass} orders-status-badge"
      data-bs-toggle="tooltip"
      data-bs-placement="top"
      title="${config.hint}"
    >
      <i class="fas ${config.icon} me-1"></i>${data}
    </span>
  `;
}

export function renderWaitingForCell(data) {
  const payload = typeof data === "object" && data !== null ? data : { label: data };
  const fallbackLabel = "Не ожидает ответа";
  const label = payload.label || fallbackLabel;
  const config = WAITING_MAP[label] || WAITING_MAP[fallbackLabel];
  const variant = payload.variant || config.variant;
  const slaState = payload.sla_state || "ok";
  const tooltip = payload.detail ? `${label} - ${payload.detail}` : label;
  return `
    <span
      class="orders-waiting-chip orders-waiting-chip--${variant} orders-waiting-chip--${slaState}"
      title="${tooltip}"
      data-bs-toggle="tooltip"
      data-bs-placement="top"
    >
      ${payload.short_label || config.shortLabel}
    </span>
  `;
}

export function isActiveStatus(status) {
  return status === "В очереди" || status === "В работе";
}

export function renderDetailButton(url) {
  return `
    <button
      type="button"
      class="detail-order orders-action-btn btn btn-sm btn-outline-info d-inline-flex align-items-center justify-content-center gap-2 px-3"
      data-form-url="${url}"
      title="Открыть заявку"
      aria-label="Открыть заявку"
    >
      <i class="fas fa-eye"></i>
      <span class="orders-action-btn__label">Открыть</span>
    </button>
  `;
}

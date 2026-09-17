import { openConfirmModal } from "./confirm-modal.js";

function getCookie(name) {
  const cookieValue = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`));
  return cookieValue ? decodeURIComponent(cookieValue.split('=').slice(1).join('=')) : '';
}

export function applyNotificationSummary(root, payload) {
  const badge = root.querySelector('[data-notification-badge]');
  const labels = document.querySelectorAll('[data-notification-count-label]');
  if (!badge) {
    return;
  }

  const unreadCount = Number(payload.unread_count || 0);
  const displayValue = payload.unread_count_display || '0';

  badge.textContent = displayValue;
  badge.classList.toggle('is-hidden', unreadCount === 0);
  labels.forEach((label) => {
    label.textContent = displayValue;
  });
}

export async function fetchNotificationsPanel(root) {
  const panelUrl = root.dataset.panelUrl;
  const dropdownMenu = root.querySelector('.orders-topbar__dropdown');
  if (!panelUrl || !dropdownMenu) {
    return;
  }

  dropdownMenu.classList.add('is-loading');
  const response = await fetch(panelUrl, {
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
    },
    credentials: 'same-origin',
  });

  dropdownMenu.classList.remove('is-loading');
  if (!response.ok) {
    dropdownMenu.innerHTML = '<div class="orders-topbar__dropdown-loading">Не удалось загрузить уведомления.</div>';
    return;
  }

  dropdownMenu.innerHTML = await response.text();
}

async function refreshListIfPresent() {
  const listContainer = document.querySelector('[data-notifications-list]');
  if (!listContainer) {
    return;
  }

  const currentUrl = new URL(window.location.href);
  currentUrl.searchParams.set('fragment', 'list');

  const response = await fetch(currentUrl.toString(), {
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
    },
    credentials: 'same-origin',
  });

  if (!response.ok) {
    return;
  }

  listContainer.innerHTML = await response.text();
}

async function submitAction(root, form) {
  const confirmMessage = form.dataset.confirm;
  if (confirmMessage) {
    const isConfirmed = await openConfirmModal({
      title: form.dataset.confirmTitle || "Подтверждение",
      kicker: form.dataset.confirmKicker || "Уведомления",
      heading: form.dataset.confirmHeading || "Подтвердите действие",
      message: confirmMessage,
      hint: form.dataset.confirmHint || "",
      confirmText: form.dataset.confirmButtonText || "Подтвердить",
      cancelText: form.dataset.confirmCancelText || "Отмена",
      confirmButtonClass: form.dataset.confirmButtonClass || "btn-primary",
      confirmIconClass: form.dataset.confirmIcon || "",
    });
    if (!isConfirmed) {
      return;
    }
  }

  const response = await fetch(form.action, {
    method: 'POST',
    body: new FormData(form),
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    credentials: 'same-origin',
  });

  if (!response.ok) {
    throw new Error('Failed to submit notification action');
  }

  const payload = await response.json();
  applyNotificationSummary(root, payload);
  await Promise.all([fetchNotificationsPanel(root), refreshListIfPresent()]);
  document.dispatchEvent(new CustomEvent("orders:summary-refresh"));
}

export function initializeNotificationsCenter() {
  const root = document.querySelector('[data-notification-center]');
  if (!root) {
    return;
  }

  const dropdownToggle = root.querySelector('.orders-topbar__icon-button');
  if (dropdownToggle) {
    dropdownToggle.addEventListener('show.bs.dropdown', () => {
      fetchNotificationsPanel(root).catch(() => null);
    });
    dropdownToggle.addEventListener('mouseenter', () => {
      dropdownToggle.querySelector('.fa-bell')?.classList.replace('far', 'fas');
    });
    dropdownToggle.addEventListener('mouseleave', () => {
      dropdownToggle.querySelector('.fa-bell')?.classList.replace('fas', 'far');
    });
  }

  document.addEventListener('submit', (event) => {
    const form = event.target.closest('[data-notification-action]');
    if (!form) {
      return;
    }

    event.preventDefault();
    submitAction(root, form).catch(() => null);
  });
}

import { initializeFormModal, openOrderModal } from './modal/form-modal.js';
import { initializeHelpPopovers } from './ui/init-help-popovers.js';
import { initializeNotificationsCenter } from './ui/notifications-center.js';
import { initializeGlobalSummaryPolling } from './ui/global-summary-polling.js';
import { showToasts } from './ui/show-toasts.js';
import {initializeBootstrapPopovers} from "./ui/init-popovers.js";


document.addEventListener('DOMContentLoaded', function ()  {
  initializeFormModal();
  initializeHelpPopovers();
  initializeNotificationsCenter();
  initializeGlobalSummaryPolling();
  showToasts();
  initializeBootstrapPopovers();

  const params = new URLSearchParams(window.location.search);
  const modalUrl = params.get('modal');
  const modalTab = params.get('modal_tab');

  if (modalUrl) {
    openOrderModal(modalUrl, { openDiscussion: modalTab === 'discussion' }).finally(() => {
      params.delete('modal');
      params.delete('modal_tab');
      params.delete('modal_message');
      const nextQuery = params.toString();
      const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ''}${window.location.hash}`;
      window.history.replaceState({}, '', nextUrl);
    });
  }
});

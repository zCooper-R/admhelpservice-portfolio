
export function initializeBootstrapPopovers(root = document) {
  const popoverTriggerList = [].slice.call(root.querySelectorAll('[data-bs-toggle="popover"]'));
  popoverTriggerList.forEach(function (popoverTriggerEl) {
    if (bootstrap.Popover.getInstance(popoverTriggerEl)) {
      return;
    }
    new bootstrap.Popover(popoverTriggerEl);
  });

  const tooltipTriggerList = [].slice.call(root.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.forEach(function (tooltipTriggerEl) {
    if (bootstrap.Tooltip.getInstance(tooltipTriggerEl)) {
      return;
    }
    new bootstrap.Tooltip(tooltipTriggerEl);
  });
}

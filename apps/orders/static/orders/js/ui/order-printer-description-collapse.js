function syncPrinterDescriptionState(form) {
  const categorySelect = form.querySelector("#id_category");
  const descriptionButton = form.querySelector("#button_description");
  const descriptionCollapse = form.querySelector("#collapseDescription");
  const descriptionField = form.querySelector("#id_description");

  if (!categorySelect || !descriptionCollapse || !descriptionField) {
    return;
  }

  const isRefillCategory = Number(categorySelect.value) === 0;
  const collapseInstance = bootstrap.Collapse.getOrCreateInstance(descriptionCollapse, { toggle: false });
  const isExpanded = descriptionCollapse.classList.contains("show");

  descriptionField.required = !isRefillCategory;
  descriptionField.setAttribute("aria-required", isRefillCategory ? "false" : "true");

  if (!isRefillCategory && !isExpanded) {
    collapseInstance.show();
  }

  if (isRefillCategory && isExpanded) {
    collapseInstance.hide();
  }

  if (descriptionButton) {
    descriptionButton.textContent = descriptionCollapse.classList.contains("show")
      ? "Скрыть комментарий"
      : "Добавить комментарий";
  }
}

export function initializeOrderDescriptionCollapse(form) {
  if (!form || form.id !== "printer") {
    return;
  }

  if (form.dataset.printerDescriptionInitialized === "true") {
    return;
  }
  form.dataset.printerDescriptionInitialized = "true";

  const categorySelect = form.querySelector("#id_category");
  const descriptionButton = form.querySelector("#button_description");
  const descriptionCollapse = form.querySelector("#collapseDescription");
  const descriptionField = form.querySelector("#id_description");

  if (!categorySelect || !descriptionCollapse || !descriptionField) {
    return;
  }

  categorySelect.addEventListener("change", () => syncPrinterDescriptionState(form));

  descriptionCollapse.addEventListener("show.bs.collapse", () => {
    descriptionField.required = true;
    descriptionField.setAttribute("aria-required", "true");
    if (descriptionButton) {
      descriptionButton.textContent = "Скрыть комментарий";
    }
    setTimeout(() => descriptionField.focus(), 0);
  });

  descriptionCollapse.addEventListener("shown.bs.collapse", () => {
    if (descriptionButton) {
      descriptionButton.textContent = "Скрыть комментарий";
    }
    descriptionField.focus();
  });

  descriptionCollapse.addEventListener("hide.bs.collapse", () => {
    if (Number(categorySelect.value) === 0) {
      descriptionField.required = false;
      descriptionField.setAttribute("aria-required", "false");
    }
    if (descriptionButton) {
      descriptionButton.textContent = "Добавить комментарий";
    }
  });

  descriptionCollapse.addEventListener("hidden.bs.collapse", () => {
    if (descriptionButton) {
      descriptionButton.textContent = "Добавить комментарий";
    }
  });

  syncPrinterDescriptionState(form);
}

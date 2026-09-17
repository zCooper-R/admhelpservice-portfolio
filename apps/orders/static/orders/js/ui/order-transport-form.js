const MAX_ROUTE_POINTS = 5;

const ROUTE_PLACEHOLDERS = [
  "ул. Примерная, 10",
  "Комсомольский бульвар, 9",
  "ул. Грузинская, 48",
  "Кремль",
  "ул. Калинина, 40",
  "ул. Володарского, 83Б",
  "ул. Горная, д. 13",
  "ул. Белинского, 9Б",
  "ул. Почаинская, д. 17К",
  "ул. Кирова, 56А",
  "Бебяево",
  "Кирилловка",
  "Казаково",
  "ул. Либхерр, 3",
  "ул. Алексеевская, 22",
  "ул. Ванеева, 203",
  "пл. Ленина, 1",
  "м-н Спортивный, д. 36",
  "ул. Владимирского, 12",
  "ул. Калинина, 41/1",
  "ул. Студенческая, д. 23",
];

function syncTransportDescriptionState(form) {
  const descriptionButton = form.querySelector("#button_description");
  const descriptionField = form.querySelector("#id_description");
  const descriptionCollapse = form.querySelector("#div_id_description");

  if (!descriptionField || !descriptionCollapse) {
    return;
  }

  const isExpanded = descriptionCollapse.classList.contains("show");
  descriptionField.required = isExpanded;
  descriptionField.setAttribute("aria-required", isExpanded ? "true" : "false");

  if (descriptionButton) {
    descriptionButton.textContent = isExpanded
      ? "Скрыть комментарий"
      : "Добавить комментарий";
  }
}

function initializeTransportDescriptionToggle(form) {
  const descriptionCollapse = form.querySelector("#div_id_description");
  const descriptionField = form.querySelector("#id_description");
  const descriptionButton = form.querySelector("#button_description");

  if (!descriptionCollapse || !descriptionField) {
    return;
  }

  descriptionCollapse.addEventListener("show.bs.collapse", () => {
    syncTransportDescriptionState(form);
    setTimeout(() => descriptionField.focus(), 0);
  });

  descriptionCollapse.addEventListener("shown.bs.collapse", () => {
    syncTransportDescriptionState(form);
    descriptionField.focus();
  });

  descriptionCollapse.addEventListener("hide.bs.collapse", () => {
    descriptionField.required = false;
    descriptionField.setAttribute("aria-required", "false");
    if (descriptionButton) {
      descriptionButton.textContent = "Добавить комментарий";
    }
  });

  syncTransportDescriptionState(form);
}

function getRouteRows(container) {
  return Array.from(container.querySelectorAll("[data-route-stop]"));
}

function getRouteRoleLabel(index, total) {
  if (total === 1) {
    return "Пункт маршрута";
  }
  if (index === 0) {
    return "Старт";
  }
  if (index === total - 1) {
    return "Финальная точка";
  }
  return "Промежуточная точка";
}

function updateRoutePreview(form, rows) {
  const preview = form.querySelector("#transport_route_preview");
  const countBadge = form.querySelector("#transport_route_count");

  if (countBadge) {
    countBadge.textContent = `${rows.length} ${rows.length === 1 ? "точка" : "точек"}`;
  }

  if (!preview) {
    return;
  }

  const addresses = rows
    .map((row) => row.querySelector('input[name="address"]')?.value.trim())
    .filter(Boolean);

  if (!addresses.length) {
    preview.textContent = "Укажите первую точку маршрута.";
    return;
  }

  preview.textContent = addresses.join(" -> ");
}

function updateRouteRows(form, container) {
  const rows = getRouteRows(container);

  rows.forEach((row, index) => {
    const number = row.querySelector(".orders-transport-address-number");
    const role = row.querySelector(".orders-transport-address-role");
    const moveUpButton = row.querySelector(".orders-transport-move-up");
    const moveDownButton = row.querySelector(".orders-transport-move-down");
    const removeButton = row.querySelector(".remove-address-btn");

    if (number) {
      number.textContent = String(index + 1);
    }

    if (role) {
      role.textContent = getRouteRoleLabel(index, rows.length);
    }

    if (moveUpButton) {
      moveUpButton.disabled = index === 0;
    }

    if (moveDownButton) {
      moveDownButton.disabled = index === rows.length - 1;
    }

    if (removeButton) {
      removeButton.disabled = rows.length === 1;
      removeButton.classList.toggle("disabled", rows.length === 1);
    }
  });

  updateRoutePreview(form, rows);

  const addButton = form.querySelector("#add_address_button");
  if (addButton) {
    addButton.style.display = rows.length >= MAX_ROUTE_POINTS ? "none" : "";
  }
}

function createAddressRow() {
  const wrapper = document.createElement("div");
  wrapper.className = "orders-transport-address-row";
  wrapper.dataset.routeStop = "true";
  wrapper.innerHTML = `
    <div class="orders-transport-address-meta">
      <div class="orders-transport-address-number">1</div>
      <div class="orders-transport-address-role">Пункт маршрута</div>
    </div>

    <div class="orders-transport-address-input-wrap">
      <input
        type="text"
        name="address"
        maxlength="150"
        class="form-control orders-modal-input"
        required
        placeholder="${ROUTE_PLACEHOLDERS[Math.floor(Math.random() * ROUTE_PLACEHOLDERS.length)]}"
        autocomplete="off"
      >
      <div class="invalid-feedback">Пожалуйста, укажите точку маршрута.</div>
    </div>

    <div class="orders-transport-address-actions">
      <button type="button" class="btn btn-outline-secondary orders-transport-move-up" aria-label="Поднять точку" title="Поднять точку">
        <i class="fa fa-arrow-up"></i>
      </button>
      <button type="button" class="btn btn-outline-secondary orders-transport-move-down" aria-label="Опустить точку" title="Опустить точку">
        <i class="fa fa-arrow-down"></i>
      </button>
      <button type="button" class="btn btn-outline-danger remove-address-btn" aria-label="Удалить точку" title="Удалить точку">
        <i class="fa fa-times"></i>
      </button>
    </div>
  `;

  return wrapper;
}

function initializeTransportAddresses(form) {
  const addButton = form.querySelector("#add_address_button");
  const addressContainer = form.querySelector("#transport_route_list");
  if (!addButton || !addressContainer) {
    return;
  }

  addressContainer.addEventListener("input", (event) => {
    if (event.target.matches('input[name="address"]')) {
      updateRoutePreview(form, getRouteRows(addressContainer));
    }
  });

  addButton.addEventListener("click", (event) => {
    event.preventDefault();
    const rows = getRouteRows(addressContainer);
    if (rows.length >= MAX_ROUTE_POINTS) {
      updateRouteRows(form, addressContainer);
      return;
    }

    const row = createAddressRow();
    addressContainer.appendChild(row);
    updateRouteRows(form, addressContainer);
    row.querySelector('input[name="address"]')?.focus();
  });

  form.addEventListener("click", (event) => {
    const moveUpButton = event.target.closest(".orders-transport-move-up");
    const moveDownButton = event.target.closest(".orders-transport-move-down");
    const removeButton = event.target.closest(".remove-address-btn");

    if (moveUpButton) {
      event.preventDefault();
      const row = moveUpButton.closest("[data-route-stop]");
      if (!row || !row.previousElementSibling) {
        return;
      }
      addressContainer.insertBefore(row, row.previousElementSibling);
      updateRouteRows(form, addressContainer);
      row.querySelector('input[name="address"]')?.focus();
      return;
    }

    if (moveDownButton) {
      event.preventDefault();
      const row = moveDownButton.closest("[data-route-stop]");
      if (!row || !row.nextElementSibling) {
        return;
      }
      addressContainer.insertBefore(row.nextElementSibling, row);
      updateRouteRows(form, addressContainer);
      row.querySelector('input[name="address"]')?.focus();
      return;
    }

    if (!removeButton) {
      return;
    }

    event.preventDefault();
    const rows = getRouteRows(addressContainer);
    if (rows.length === 1) {
      return;
    }

    const row = removeButton.closest("[data-route-stop]");
    if (!row) {
      return;
    }

    row.classList.add("remove-input-field");
    row.addEventListener(
      "animationend",
      () => {
        row.remove();
        updateRouteRows(form, addressContainer);
      },
      { once: true },
    );
  });

  updateRouteRows(form, addressContainer);
}

function initializeComebackToggle(form) {
  const comebackField = form.querySelector("#id_comeback");
  if (!comebackField) {
    return;
  }

  comebackField.addEventListener("change", function () {
    const container = form.querySelector("#div_id_comeback .col-md-7");
    const existing = form.querySelector("#id_comeback_datetime_container");
    if (!container) {
      return;
    }

    if (this.checked) {
      if (!existing) {
        const wrapper = document.createElement("div");
        wrapper.id = "id_comeback_datetime_container";
        wrapper.className = "add-input-field mt-2 orders-transport-comeback-time";
        wrapper.innerHTML = `
          <label for="id_comeback_datetime" class="form-text text-muted">Во сколько обратно?</label>
          <input type="time" name="comeback_datetime" class="form-control orders-modal-input w-100" required id="id_comeback_datetime">
          <div class="invalid-feedback">
            Пожалуйста, укажите примерное время возвращения.
          </div>
        `;
        container.appendChild(wrapper);
        wrapper.querySelector("input")?.focus();
      }
      return;
    }

    existing?.remove();
  });
}

export function initializeTransportForm(form) {
  if (!form || form.id !== "transport") {
    return;
  }

  if (form.dataset.transportFormInitialized === "true") {
    return;
  }
  form.dataset.transportFormInitialized = "true";

  form.querySelectorAll("input").forEach((input) => {
    input.autocomplete = "off";
  });

  initializeTransportDescriptionToggle(form);
  initializeTransportAddresses(form);
  initializeComebackToggle(form);
}

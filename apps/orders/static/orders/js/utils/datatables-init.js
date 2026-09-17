export function initDataTable({
  tableId,
  ajaxUrl,
  csrfToken,
  columns,
  slaFilterSelector = null,
  order = null,
  searchPlaceholder = "Поиск по таблице",
  searchDelay = 350,
  refreshIntervalMs = 0,
  highlightNewRows = true,
  newRowHighlightDurationMs = 6000,
}) {
  let knownRowIds = new Set();
  let initialDataLoaded = false;
  let highlightNextReload = false;
  let pendingHighlightedRowIds = new Set();
  let clearHighlightTimerId = null;
  const slaFilterRoot = slaFilterSelector ? document.querySelector(slaFilterSelector) : null;

  const normalizeRowId = (rowId) => String(rowId);
  const buildDomRowId = (rowId) => `order-${normalizeRowId(rowId)}`;
  const getSelectedSlaFilter = () =>
    slaFilterRoot?.querySelector(".orders-sla-filter__button.is-active")?.dataset.slaFilter || "all";
  const createdAtIndex = columns.findIndex((column) => column?.data === "created_at");
  const waitingIndex = columns.findIndex((column) => column?.data === "waiting_for");
  const resolveDefaultOrder = () => {
    if (Array.isArray(order) && order.length) {
      return order;
    }

    if (createdAtIndex >= 0) {
      return [[createdAtIndex, "desc"]];
    }

    return [[0, "desc"]];
  };

  const syncKnownRows = (rows) => {
    const currentRowIds = new Set(
      rows
        .map((row) => row?.id)
        .filter((rowId) => rowId !== null && rowId !== undefined)
        .map(normalizeRowId),
    );

    if (!initialDataLoaded) {
      knownRowIds = currentRowIds;
      initialDataLoaded = true;
      pendingHighlightedRowIds.clear();
      return rows;
    }

    if (highlightNewRows && highlightNextReload) {
      pendingHighlightedRowIds = new Set(
        [...currentRowIds].filter((rowId) => !knownRowIds.has(rowId)),
      );
    } else {
      pendingHighlightedRowIds.clear();
    }

    knownRowIds = currentRowIds;
    highlightNextReload = false;
    return rows;
  };

  const scheduleHighlightCleanup = () => {
    if (clearHighlightTimerId) {
      window.clearTimeout(clearHighlightTimerId);
    }

    if (!pendingHighlightedRowIds.size) {
      return;
    }

    clearHighlightTimerId = window.setTimeout(() => {
      pendingHighlightedRowIds.forEach((rowId) => {
        const row = document.getElementById(buildDomRowId(rowId));
        row?.classList.remove("orders-row--new");
      });
      pendingHighlightedRowIds.clear();
      clearHighlightTimerId = null;
    }, newRowHighlightDurationMs);
  };

  const table = $(`#${tableId}`).DataTable({
    stateSave: true,
    processing: true,
    responsive: true,
    autoWidth: false,
    scrollX: true,
    serverSide: true,
    order: resolveDefaultOrder(),
    stateLoadParams(_settings, data) {
      if (!Array.isArray(data?.order) || createdAtIndex < 0 || waitingIndex < 0) {
        return;
      }

      data.order = data.order.map(([columnIndex, direction]) => {
        if (Number(columnIndex) === waitingIndex && createdAtIndex !== waitingIndex) {
          return [createdAtIndex, direction];
        }
        return [columnIndex, direction];
      });
    },
    searchDelay,
    rowId: (row) => buildDomRowId(row.id),
    ajax: {
      url: ajaxUrl,
      type: "POST",
      data: (requestData) => {
        requestData.csrfmiddlewaretoken = csrfToken;
        requestData.sla_filter = getSelectedSlaFilter();
      },
      dataSrc: (json) => {
        const rows = Array.isArray(json?.data) ? json.data : [];
        return syncKnownRows(rows);
      },
    },
    columns,
    columnDefs: [
      { width: "2%", targets: 0 },
      { width: "25%", targets: 1 },
      { width: "15%", targets: 2 },
      { width: "10%", targets: 3 },
      { width: "9%", targets: 4 },
      { width: "12%", targets: 5 },
      { width: "10%", targets: 6 },
      { className: "dt-center dt-col-index", targets: 0 },
      { className: "dt-col-category", targets: 1 },
      { className: "dt-col-client", targets: 2 },
      { className: "dt-center dt-col-status", targets: 3 },
      { className: "dt-center dt-col-waiting_for", targets: 4 },
      { className: "dt-center dt-col-created", targets: 5 },
      { className: "dt-center dt-col-actions", targets: 6 },
    ],
    language: {
      sProcessing: "Загружаем заявки...",
      sLengthMenu: "Показывать _MENU_ записей",
      sZeroRecords:
        "По вашему запросу ничего не найдено. Попробуйте изменить формулировку поиска.",
      sInfo: "Показаны записи с _START_ по _END_ из _TOTAL_",
      sInfoEmpty: "Пока нет доступных записей",
      sInfoFiltered: "(отфильтровано из _MAX_ записей)",
      sSearch: "Поиск:",
      emptyTable:
        "Пока здесь пусто. Когда появятся заявки, они будут показаны в этой таблице.",
      oPaginate: {
        sFirst: "Первая",
        sPrevious: "Назад",
        sNext: "Вперёд",
        sLast: "Последняя",
      },
      oAria: {
        sSortAscending: ": активировать для сортировки по возрастанию",
        sSortDescending: ": активировать для сортировки по убыванию",
      },
    },
    createdRow(row, data) {
      if (data.status === "В очереди" || data.status === "В работе") {
        row.classList.add("orders-row--active");
      }

      if (pendingHighlightedRowIds.has(normalizeRowId(data.id))) {
        row.classList.add("orders-row--new");
      }
    },
    initComplete() {
      const wrapper = document.getElementById(`${tableId}_wrapper`);
      const searchInput = wrapper?.querySelector(".dt-search input");
      if (searchInput) {
        searchInput.placeholder = searchPlaceholder;
        searchInput.setAttribute("aria-label", searchPlaceholder);
      }
    },
    drawCallback() {
      document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((tooltipEl) => {
        if (!bootstrap.Tooltip.getInstance(tooltipEl)) {
          new bootstrap.Tooltip(tooltipEl);
        }
      });

      scheduleHighlightCleanup();
    },
  });

  document.addEventListener("orders:changed", () => {
    table.ajax.reload(null, false);
  });

  if (slaFilterRoot) {
    slaFilterRoot.addEventListener("click", (event) => {
      const button = event.target.closest("[data-sla-filter]");
      if (!button || button.classList.contains("is-active")) {
        return;
      }

      slaFilterRoot.querySelectorAll("[data-sla-filter]").forEach((item) => {
        item.classList.toggle("is-active", item === button);
      });
      table.ajax.reload();
    });
  }

  if (refreshIntervalMs > 0) {
    window.setInterval(() => {
      if (document.visibilityState !== "visible") {
        return;
      }
      highlightNextReload = true;
      table.ajax.reload(null, false);
    }, refreshIntervalMs);
  }

  return table;
}

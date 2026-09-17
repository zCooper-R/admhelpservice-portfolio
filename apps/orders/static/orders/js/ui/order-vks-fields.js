export function initializeVksFields(form) {
  if (!form || form.id !== "vks") {
    return;
  }

  if (form.dataset.vksFieldsInitialized === "true") {
    return;
  }
  form.dataset.vksFieldsInitialized = "true";

  const categorySelect = form.querySelector("#id_category");
  const modalRoot = form.closest(".orders-modal");
  const organizationBlock = form.querySelector("#collapseVksOrganization");
  const connectBlock = form.querySelector("#collapseVksConnect");
  const linkFieldGroup = form.querySelector("#vksLinkFieldGroup");
  const equipmentGroup = form.querySelector("#vksEquipmentGroup");
  const linkField = form.querySelector("#id_link_vks");
  const nameField = form.querySelector("#id_name_vks");
  const startField = form.querySelector("#id_start_vks_datetime");
  const durationField = form.querySelector("#id_duration_vks_time");
  const recipientField = form.querySelector("#id_recipient_email");
  const equipmentFields = form.querySelectorAll("input[name='equipment']");

  if (!categorySelect || !organizationBlock || !connectBlock) {
    return;
  }

  const organizeValue = Number(modalRoot?.dataset.vksOrganize);
  const connectValue = Number(modalRoot?.dataset.vksConnect);
  const presentationValue = Number(modalRoot?.dataset.vksPresentation);

  function toggle(block, visible) {
    block.classList.toggle("show", visible);
    block.classList.toggle("d-none", !visible);
  }

  function syncFields() {
    const selectedValue = Number(categorySelect.value);

    if (selectedValue === organizeValue) {
      toggle(organizationBlock, true);
      toggle(connectBlock, false);
      if (linkFieldGroup) linkFieldGroup.classList.remove("d-none");
      if (equipmentGroup) equipmentGroup.classList.remove("d-none");
      if (linkField) linkField.required = false;
      if (nameField) nameField.required = true;
      if (startField) startField.required = true;
      if (durationField) durationField.required = true;
      if (recipientField) recipientField.required = true;
      equipmentFields.forEach((field) => {
        field.required = false;
      });
      return;
    }

    if (selectedValue === connectValue) {
      toggle(organizationBlock, false);
      toggle(connectBlock, true);
      if (linkFieldGroup) linkFieldGroup.classList.remove("d-none");
      if (equipmentGroup) equipmentGroup.classList.remove("d-none");
      if (linkField) linkField.required = true;
      if (nameField) nameField.required = false;
      if (startField) startField.required = true;
      if (durationField) durationField.required = false;
      if (recipientField) recipientField.required = false;
      equipmentFields.forEach((field) => {
        field.required = false;
      });
      return;
    }

    if (selectedValue === presentationValue) {
      toggle(organizationBlock, false);
      toggle(connectBlock, true);
      if (linkFieldGroup) linkFieldGroup.classList.add("d-none");
      if (equipmentGroup) equipmentGroup.classList.remove("d-none");
      if (linkField) linkField.required = false;
      if (nameField) nameField.required = false;
      if (startField) startField.required = true;
      if (durationField) durationField.required = false;
      if (recipientField) recipientField.required = false;
      equipmentFields.forEach((field) => {
        field.required = false;
      });
      return;
    }

    toggle(organizationBlock, false);
    toggle(connectBlock, false);
    if (linkFieldGroup) linkFieldGroup.classList.remove("d-none");
    if (equipmentGroup) equipmentGroup.classList.remove("d-none");
    if (linkField) linkField.required = false;
    if (nameField) nameField.required = false;
    if (startField) startField.required = false;
    if (durationField) durationField.required = false;
    if (recipientField) recipientField.required = false;
    equipmentFields.forEach((field) => {
      field.required = false;
    });
  }

  categorySelect.addEventListener("change", syncFields);
  syncFields();
}

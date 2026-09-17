import { showToasts } from '../../orders/js/ui/show-toasts.js';

function getCookie(name) {
  const cookieValue = document.cookie
    .split(';')
    .map((item) => item.trim())
    .find((item) => item.startsWith(`${name}=`));

  if (!cookieValue) {
    return '';
  }

  return decodeURIComponent(cookieValue.split('=').slice(1).join('='));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function getSnoozeKey(campaignId) {
  return `survey-campaign-snooze:${campaignId}`;
}

function getSnoozedUntil(campaignId) {
  const rawValue = window.localStorage.getItem(getSnoozeKey(campaignId));
  if (!rawValue) {
    return null;
  }

  const timestamp = Number(rawValue);
  if (!Number.isFinite(timestamp)) {
    window.localStorage.removeItem(getSnoozeKey(campaignId));
    return null;
  }

  return timestamp;
}

function isCampaignSnoozed(campaignId) {
  const snoozedUntil = getSnoozedUntil(campaignId);
  if (!snoozedUntil) {
    return false;
  }

  if (Date.now() >= snoozedUntil) {
    window.localStorage.removeItem(getSnoozeKey(campaignId));
    return false;
  }

  return true;
}

function snoozeCampaign(campaignId, hours) {
  const snoozedUntil = Date.now() + (hours * 60 * 60 * 1000);
  window.localStorage.setItem(getSnoozeKey(campaignId), String(snoozedUntil));
}

function renderRatingQuestion(question, requiredMark) {
  const stars = [5, 4, 3, 2, 1].map((value) => {
    const inputId = `survey-rating-${question.id}-${value}`;
    return `
      <input type="radio" id="${inputId}" name="question-${question.id}" value="${value}">
      <label class="survey-rating-star" for="${inputId}" title="${value} из 5" aria-label="${value} из 5"></label>
    `;
  }).join('');

  return `
    <div class="mb-4 survey-question" data-question-id="${question.id}" data-question-type="${question.question_type}" data-required="${question.is_required}">
      <label class="form-label fw-semibold d-block survey-question__label">${escapeHtml(question.text)} ${requiredMark}</label>
      <div class="survey-rating-stars" role="radiogroup" aria-label="${escapeHtml(question.text)}">
        ${stars}
      </div>
      <div class="survey-rating-hint">1 звезда — плохо, 5 звёзд — отлично.</div>
      <div class="invalid-feedback d-block small mt-2 d-none"></div>
    </div>
  `;
}

function renderQuestion(question) {
  const requiredMark = question.is_required ? '<span class="text-danger">*</span>' : '';

  if (question.question_type === 'rating') {
    return renderRatingQuestion(question, requiredMark);
  }

  if (question.question_type === 'single_choice') {
    const options = question.options.map((option) => `
      <div class="form-check">
        <input class="form-check-input" type="radio" name="question-${question.id}" id="survey-option-${option.id}" value="${option.id}">
        <label class="form-check-label" for="survey-option-${option.id}">${escapeHtml(option.text)}</label>
      </div>
    `).join('');

    return `
      <div class="mb-4 survey-question" data-question-id="${question.id}" data-question-type="${question.question_type}" data-required="${question.is_required}">
        <label class="form-label fw-semibold d-block survey-question__label">${escapeHtml(question.text)} ${requiredMark}</label>
        ${options}
        <div class="invalid-feedback d-block small mt-2 d-none"></div>
      </div>
    `;
  }

  if (question.question_type === 'multiple_choice') {
    const options = question.options.map((option) => `
      <div class="form-check">
        <input class="form-check-input" type="checkbox" name="question-${question.id}" id="survey-option-${option.id}" value="${option.id}">
        <label class="form-check-label" for="survey-option-${option.id}">${escapeHtml(option.text)}</label>
      </div>
    `).join('');

    return `
      <div class="mb-4 survey-question" data-question-id="${question.id}" data-question-type="${question.question_type}" data-required="${question.is_required}">
        <label class="form-label fw-semibold d-block survey-question__label">${escapeHtml(question.text)} ${requiredMark}</label>
        ${options}
        <div class="invalid-feedback d-block small mt-2 d-none"></div>
      </div>
    `;
  }

  return `
    <div class="mb-4 survey-question" data-question-id="${question.id}" data-question-type="${question.question_type}" data-required="${question.is_required}">
      <label class="form-label fw-semibold survey-question__label" for="survey-text-${question.id}">${escapeHtml(question.text)} ${requiredMark}</label>
      <textarea class="form-control" rows="4" id="survey-text-${question.id}" name="question-${question.id}"></textarea>
      <div class="invalid-feedback d-block small mt-2 d-none"></div>
    </div>
  `;
}

function clearErrors(form) {
  form.querySelectorAll('.survey-question .invalid-feedback').forEach((element) => {
    element.textContent = '';
    element.classList.add('d-none');
  });
}

function showErrors(form, errors = {}) {
  Object.entries(errors).forEach(([questionId, messages]) => {
    const container = form.querySelector(`.survey-question[data-question-id="${questionId}"] .invalid-feedback`);
    if (!container) {
      return;
    }

    container.textContent = Array.isArray(messages) ? messages.join(' ') : String(messages);
    container.classList.remove('d-none');
  });
}

function collectAnswer(questionElement) {
  const questionId = Number(questionElement.dataset.questionId);
  const questionType = questionElement.dataset.questionType;

  if (questionType === 'rating') {
    const checked = questionElement.querySelector('input[type="radio"]:checked');
    return {
      question_id: questionId,
      rating_value: checked ? Number(checked.value) : null,
    };
  }

  if (questionType === 'single_choice') {
    const checked = questionElement.querySelector('input[type="radio"]:checked');
    return {
      question_id: questionId,
      selected_option_id: checked ? Number(checked.value) : null,
    };
  }

  if (questionType === 'multiple_choice') {
    const selectedOptionIds = Array.from(questionElement.querySelectorAll('input[type="checkbox"]:checked'))
      .map((input) => Number(input.value));
    return {
      question_id: questionId,
      selected_option_ids: selectedOptionIds,
    };
  }

  return {
    question_id: questionId,
    text_answer: questionElement.querySelector('textarea')?.value?.trim() || '',
  };
}

function validateRequiredQuestions(form) {
  const questions = Array.from(form.querySelectorAll('.survey-question'));
  const errors = {};

  questions.forEach((questionElement) => {
    if (questionElement.dataset.required !== 'true') {
      return;
    }

    const questionId = questionElement.dataset.questionId;
    const questionType = questionElement.dataset.questionType;

    if (questionType === 'rating' || questionType === 'single_choice') {
      const checked = questionElement.querySelector('input[type="radio"]:checked');
      if (!checked) {
        errors[questionId] = ['Это обязательный вопрос.'];
      }
      return;
    }

    if (questionType === 'multiple_choice') {
      const checked = questionElement.querySelectorAll('input[type="checkbox"]:checked');
      if (!checked.length) {
        errors[questionId] = ['Нужно выбрать хотя бы один вариант.'];
      }
      return;
    }

    const value = questionElement.querySelector('textarea')?.value?.trim() || '';
    if (!value) {
      errors[questionId] = ['Текстовый ответ обязателен.'];
    }
  });

  return errors;
}

function resetAlert(alertElement) {
  alertElement.className = 'alert d-none';
  alertElement.textContent = '';
}

function showSuccessToast(message) {
  const toastContainer = document.getElementById('toast-container');
  if (!toastContainer || !message) {
    return;
  }

  toastContainer.insertAdjacentHTML('beforeend', `
    <div class="toast orders-toast border-0" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="toast-header">
        <i class="bi bi-check-circle-fill text-success me-2 fs-5"></i>
        <strong class="me-auto">HelpService</strong>
        <small class="text-body-secondary">только что</small>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Закрыть"></button>
      </div>
      <div class="toast-body">${escapeHtml(message)}</div>
    </div>
  `);

  showToasts();
}

export async function initializeSurveyPopup() {
  const root = document.getElementById('surveyPopupRoot');
  if (!root || !window.bootstrap || root.dataset.surveyPopupInitialized === 'true') {
    return;
  }
  root.dataset.surveyPopupInitialized = 'true';

  const modalElement = document.getElementById('surveyCampaignModal');
  const modal = new bootstrap.Modal(modalElement);
  const titleElement = document.getElementById('surveyCampaignModalTitle');
  const subtitleElement = document.getElementById('surveyCampaignModalSubtitle');
  const descriptionElement = document.getElementById('surveyCampaignDescription');
  const form = document.getElementById('surveyCampaignForm');
  const questionsContainer = document.getElementById('surveyCampaignQuestions');
  const submitButton = document.getElementById('surveyCampaignSubmitButton');
  const snoozeButton = document.getElementById('surveyCampaignSnoozeButton');
  const snoozeNote = document.getElementById('surveyCampaignSnoozeNote');
  const alertElement = document.getElementById('surveyCampaignAlert');
  const originalSubmitText = submitButton.textContent;
  const snoozeHours = Number(root.dataset.snoozeHours || 24);

  let currentCampaign = null;
  let isSubmitting = false;

  try {
    const popupResponse = await fetch(root.dataset.currentPopupUrl, {
      method: 'GET',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin',
    });

    if (!popupResponse.ok) {
      return;
    }

    const popupData = await popupResponse.json();
    if (!popupData.show || !popupData.campaign) {
      return;
    }

    currentCampaign = popupData.campaign;
    if (isCampaignSnoozed(currentCampaign.id)) {
      return;
    }

    titleElement.textContent = currentCampaign.popup_title || currentCampaign.title;
    subtitleElement.textContent = currentCampaign.title;
    descriptionElement.textContent = currentCampaign.popup_text || currentCampaign.description || '';

    if (snoozeNote) {
      snoozeNote.textContent = snoozeHours >= 24
        ? `Если сейчас неудобно, напомним через ${Math.round(snoozeHours / 24)} дн.`
        : `Если сейчас неудобно, напомним через ${snoozeHours} ч.`;
    }

    questionsContainer.innerHTML = currentCampaign.questions.map(renderQuestion).join('');
    modal.show();
  } catch (error) {
    console.error('Survey popup initialization failed', error);
    return;
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!currentCampaign || isSubmitting) {
      return;
    }

    clearErrors(form);
    resetAlert(alertElement);

    const clientErrors = validateRequiredQuestions(form);
    if (Object.keys(clientErrors).length) {
      showErrors(form, clientErrors);
      const firstInvalid = form.querySelector('.invalid-feedback:not(.d-none)');
      if (firstInvalid) {
        firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      return;
    }

    isSubmitting = true;
    submitButton.disabled = true;
    submitButton.textContent = 'Отправка...';

    const answers = Array.from(form.querySelectorAll('.survey-question')).map(collectAnswer);

    try {
      const response = await fetch(root.dataset.submitPopupUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
          'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'same-origin',
        body: JSON.stringify({
          campaign_id: currentCampaign.id,
          answers,
        }),
      });

      const responseData = await response.json();

      if (!response.ok || !responseData.success) {
        alertElement.className = 'alert alert-danger';
        alertElement.textContent = responseData.message || 'Не удалось отправить ответы.';
        showErrors(form, responseData.errors || {});
        return;
      }

      showSuccessToast(responseData.message || 'Спасибо за ответ.');
      setTimeout(() => {
        modal.hide();
      }, 900);
    } catch (error) {
      alertElement.className = 'alert alert-danger';
      alertElement.textContent = 'Не удалось отправить ответы из-за сетевой ошибки. Попробуйте ещё раз.';
    } finally {
      isSubmitting = false;
      submitButton.disabled = false;
      submitButton.textContent = originalSubmitText;
    }
  });

  snoozeButton?.addEventListener('click', () => {
    if (currentCampaign) {
      snoozeCampaign(currentCampaign.id, snoozeHours);
    }
    modal.hide();
  });

  modalElement.addEventListener('hidden.bs.modal', () => {
    form.reset();
    clearErrors(form);
    resetAlert(alertElement);
  });
}

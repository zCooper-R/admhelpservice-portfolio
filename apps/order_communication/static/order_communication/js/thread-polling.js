function getDiscussionPane(root) {
  return root.querySelector("#order-discussion-pane");
}

function getDiscussionBadge(root) {
  return root.querySelector("[data-order-discussion-badge]");
}

function getThreadRoot(root) {
  return root.querySelector("[data-order-thread-root]");
}

function getThreadTimeline(threadRoot) {
  return threadRoot?.querySelector("[data-order-thread-timeline]");
}

function getScrollContainer(threadRoot) {
  return threadRoot?.closest(".orders-modal-body");
}

function isDiscussionTabActive(root) {
  const discussionPane = getDiscussionPane(root);
  return !discussionPane || discussionPane.classList.contains("active");
}

function getCsrfToken(container = document) {
  const input = container.querySelector("input[name='csrfmiddlewaretoken']");
  if (input) {
    return input.value;
  }

  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function pollThread(threadRoot) {
  const pollUrl = threadRoot.dataset.pollUrl;
  if (!pollUrl) {
    return null;
  }

  const response = await fetch(pollUrl, {
    headers: {
      "X-Requested-With": "XMLHttpRequest",
    },
    credentials: "same-origin",
  });

  if (!response.ok) {
    return null;
  }
  return response.json();
}

export function syncDiscussionBadge(root, unreadCount) {
  const badge = getDiscussionBadge(root);
  if (!badge) {
    return;
  }

  const normalizedCount = Number(unreadCount || 0);
  badge.textContent = String(normalizedCount);
  badge.hidden = normalizedCount <= 0;
}

function replaceThreadHtml(root, threadHtml) {
  const currentThreadRoot = getThreadRoot(root);
  if (!currentThreadRoot || !threadHtml) {
    return currentThreadRoot;
  }

  currentThreadRoot.outerHTML = threadHtml;
  return getThreadRoot(root);
}

export function scrollThreadTimelineToRelevantPosition(threadRoot, { behavior = "smooth" } = {}) {
  const timeline = getThreadTimeline(threadRoot);
  const scrollContainer = getScrollContainer(threadRoot);
  if (!timeline || !scrollContainer) {
    return;
  }

  const unreadSeparator = timeline.querySelector("[data-order-thread-unread-separator]");
  if (unreadSeparator) {
    const containerRect = scrollContainer.getBoundingClientRect();
    const targetRect = unreadSeparator.getBoundingClientRect();
    const offsetTop = scrollContainer.scrollTop + (targetRect.top - containerRect.top) - 16;
    scrollContainer.scrollTo({
      top: Math.max(offsetTop, 0),
      behavior,
    });
    return;
  }

  scrollContainer.scrollTo({
    top: scrollContainer.scrollHeight,
    behavior,
  });
}

async function positionThreadBeforeRead(threadRoot) {
  if (!threadRoot) {
    return;
  }

  await new Promise((resolve) => {
    window.requestAnimationFrame(() => {
      scrollThreadTimelineToRelevantPosition(threadRoot, { behavior: "auto" });
      window.requestAnimationFrame(resolve);
    });
  });
}

export async function activateLoadedDiscussion(root, threadRoot = getThreadRoot(root)) {
  if (!threadRoot) {
    return null;
  }

  syncDiscussionBadge(root, Number(threadRoot.dataset.unreadCount || 0));
  await positionThreadBeforeRead(threadRoot);

  if (Number(threadRoot.dataset.unreadCount || 0) > 0) {
    await markThreadReadForRoot(root, threadRoot);
  }
  return threadRoot;
}

export async function markThreadReadForRoot(root, threadRoot = getThreadRoot(root)) {
  if (!threadRoot) {
    syncDiscussionBadge(root, 0);
    return null;
  }

  const readUrl = threadRoot.dataset.readUrl;
  if (!readUrl) {
    return null;
  }

  const response = await fetch(readUrl, {
    method: "POST",
    headers: {
      "X-Requested-With": "XMLHttpRequest",
      "X-CSRFToken": getCsrfToken(threadRoot),
    },
    credentials: "same-origin",
  });

  if (!response.ok) {
    return null;
  }

  const payload = await response.json();
  if (!payload?.success) {
    return payload;
  }

  const currentThreadRoot = getThreadRoot(root);
  if (currentThreadRoot) {
    currentThreadRoot.dataset.unreadCount = "0";
  }
  syncDiscussionBadge(root, 0);
  document.dispatchEvent(new CustomEvent("orders:summary-refresh"));
  return payload;
}

async function refreshDiscussion(root, { markAsRead = false, scrollToRelevant = false } = {}) {
  const currentThreadRoot = getThreadRoot(root);
  if (!currentThreadRoot) {
    syncDiscussionBadge(root, 0);
    return null;
  }

  const payload = await pollThread(currentThreadRoot);
  if (!payload?.success) {
    return payload;
  }

  syncDiscussionBadge(root, payload.unread_count);

  const isActive = isDiscussionTabActive(root);
  const currentLatestMessageId = currentThreadRoot.dataset.latestMessageId || "";
  const nextLatestMessageId = String(payload.latest_message_id || "");
  const hasNewVisibleMessages = currentLatestMessageId !== nextLatestMessageId;

  let nextThreadRoot = currentThreadRoot;
  if (isActive && payload.thread_html && hasNewVisibleMessages) {
    nextThreadRoot = replaceThreadHtml(root, payload.thread_html);
  }

  if (isActive && scrollToRelevant && nextThreadRoot) {
    await positionThreadBeforeRead(nextThreadRoot);
  }

  if (markAsRead && isActive && Number(payload.unread_count || 0) > 0) {
    await markThreadReadForRoot(root, nextThreadRoot);
  }

  return payload;
}

function bindDiscussionTabRead(root) {
  if (root.dataset.orderDiscussionReadBound === "true") {
    return;
  }

  root.dataset.orderDiscussionReadBound = "true";
  root.addEventListener("shown.bs.tab", (event) => {
    if (event.target?.id !== "order-discussion-tab") {
      return;
    }
    if (!getThreadRoot(root)) {
      return;
    }
    refreshDiscussion(root, { markAsRead: true, scrollToRelevant: true }).catch(() => null);
  });
}

export function initializeThreadPolling(root = document) {
  bindDiscussionTabRead(root);
  const threadRoot = getThreadRoot(root);
  if (threadRoot) {
    syncDiscussionBadge(root, Number(threadRoot.dataset.unreadCount || 0));
  }

  if (root.dataset && root.dataset.orderThreadPollingInitialized === "true") {
    return;
  }
  if (root.dataset) {
    root.dataset.orderThreadPollingInitialized = "true";
  }

  const intervalId = window.setInterval(() => {
    if (document.visibilityState !== "visible") {
      return;
    }

    if (!isDiscussionTabActive(root)) {
      return;
    }

    refreshDiscussion(root, { markAsRead: true }).catch(() => null);
  }, 15000);

  if (root instanceof HTMLElement && root.classList.contains("orders-modal")) {
    root.addEventListener("hidden.bs.modal", () => {
      window.clearInterval(intervalId);
    }, { once: true });
  }
}

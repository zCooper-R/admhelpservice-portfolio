import { activateLoadedDiscussion, initializeThreadPolling } from "./thread-polling.js";

function getDiscussionPane(root) {
  return root.querySelector("#order-discussion-pane");
}

function getLazyPane(root) {
  return root.querySelector("[data-order-discussion-lazy-pane]");
}

function showLoadingState(lazyPane, isLoading) {
  const placeholder = lazyPane?.querySelector("[data-thread-placeholder]");
  const loadingState = lazyPane?.querySelector("[data-thread-loading-state]");

  if (placeholder) {
    placeholder.hidden = isLoading;
  }
  if (loadingState) {
    loadingState.hidden = !isLoading;
  }
}

async function fetchDiscussionFragment(fragmentUrl) {
  const response = await fetch(fragmentUrl, {
    headers: {
      "X-Requested-With": "XMLHttpRequest",
    },
    credentials: "same-origin",
  });

  if (!response.ok) {
    throw new Error("Failed to fetch discussion fragment");
  }
  return response.text();
}

async function loadDiscussionIntoPane(root) {
  const discussionPane = getDiscussionPane(root);
  const lazyPane = getLazyPane(root);
  if (!discussionPane || !lazyPane) {
    return null;
  }

  if (lazyPane.dataset.threadLoaded === "true") {
    return discussionPane.querySelector("[data-order-thread-root]");
  }
  if (lazyPane.dataset.threadLoading === "true") {
    return null;
  }

  const fragmentUrl = lazyPane.dataset.threadFragmentUrl;
  if (!fragmentUrl) {
    return null;
  }

  lazyPane.dataset.threadLoading = "true";
  showLoadingState(lazyPane, true);

  try {
    const threadHtml = await fetchDiscussionFragment(fragmentUrl);
    discussionPane.innerHTML = threadHtml;
    lazyPane.dataset.threadLoaded = "true";
    initializeThreadPolling(root);
    const threadRoot = discussionPane.querySelector("[data-order-thread-root]");
    if (threadRoot) {
      await activateLoadedDiscussion(root, threadRoot);
    }
    return threadRoot;
  } finally {
    lazyPane.dataset.threadLoading = "false";
  }
}

export function initializeDiscussionLazyTab(root = document) {
  if (root.dataset && root.dataset.orderDiscussionLazyInitialized === "true") {
    return;
  }
  if (root.dataset) {
    root.dataset.orderDiscussionLazyInitialized = "true";
  }

  root.addEventListener("shown.bs.tab", (event) => {
    if (event.target?.id !== "order-discussion-tab") {
      return;
    }
    loadDiscussionIntoPane(root).catch(() => null);
  });
}

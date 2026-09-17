export function initializeHelpPopovers(root = document) {
    const wrappers = root.querySelectorAll('.popover-help-wrap');
    if (!wrappers.length) {
        return;
    }

    const positionPopover = (trigger, popover) => {
        const rect = trigger.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const preferredWidth = Math.min(720, viewportWidth - 24);
        const popoverMaxHeight = Math.min(420, Math.floor(viewportHeight * 0.62));

        popover.style.position = 'fixed';
        popover.style.width = `${preferredWidth}px`;
        popover.style.maxHeight = `${popoverMaxHeight}px`;

        const topBelow = rect.bottom + 12;
        const topAbove = rect.top - popoverMaxHeight - 12;
        const top = topBelow + popoverMaxHeight <= viewportHeight
            ? topBelow
            : Math.max(12, topAbove);

        let left = rect.left - 18;
        const maxLeft = viewportWidth - preferredWidth - 12;
        left = Math.max(12, Math.min(left, maxLeft));

        popover.style.top = `${top}px`;
        popover.style.left = `${left}px`;
    };

    wrappers.forEach((wrapper) => {
        if (wrapper.dataset.helpPopoverInitialized === 'true') {
            return;
        }
        wrapper.dataset.helpPopoverInitialized = 'true';

        const trigger = wrapper.querySelector('.js-toggle-help');
        const popover = wrapper.querySelector('.js-popover-help');
        if (!trigger || !popover) {
            return;
        }

        const togglePopover = (event) => {
            event.preventDefault();
            event.stopPropagation();
            wrappers.forEach((item) => {
                if (item !== wrapper) {
                    const otherPopover = item.querySelector('.js-popover-help');
                    if (otherPopover) {
                        otherPopover.style.display = 'none';
                    }
                }
            });
            const shouldOpen = popover.style.display !== 'block';
            if (shouldOpen) {
                positionPopover(trigger, popover);
                popover.style.display = 'block';
            } else {
                popover.style.display = 'none';
            }
        };

        trigger.addEventListener('click', togglePopover);
        trigger.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                togglePopover(event);
            }
        });
    });

    if (document.body.dataset.helpPopoverOutsideHandler !== 'true') {
        document.body.dataset.helpPopoverOutsideHandler = 'true';
        document.addEventListener('click', (event) => {
            document.querySelectorAll('.js-popover-help').forEach((popover) => {
                const wrapper = popover.closest('.popover-help-wrap');
                if (wrapper && !wrapper.contains(event.target)) {
                    popover.style.display = 'none';
                }
            });
        });

        window.addEventListener('resize', () => {
            document.querySelectorAll('.popover-help-wrap').forEach((wrapper) => {
                const popover = wrapper.querySelector('.js-popover-help');
                const trigger = wrapper.querySelector('.js-toggle-help');
                if (popover && trigger && popover.style.display === 'block') {
                    positionPopover(trigger, popover);
                }
            });
        });
    }
}

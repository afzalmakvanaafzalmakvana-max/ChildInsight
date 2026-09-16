// ChildInsight — Core Client JavaScript

document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss or allow closing alert notifications
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        const closeBtn = alert.querySelector('.alert-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 250);
            });
        }
    });

    // Prevent double form submissions on POST forms
    const forms = document.querySelectorAll('form[method="POST"], form[method="post"]');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            // Check HTML5 validity if supported
            if (form.checkValidity && !form.checkValidity()) {
                return;
            }
            const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                // Short timeout to allow submit event dispatch before disabling
                setTimeout(() => {
                    submitBtn.disabled = true;
                    if (submitBtn.tagName === 'BUTTON') {
                        submitBtn.setAttribute('data-original-text', submitBtn.innerHTML);
                        submitBtn.innerHTML = '<span>Processing...</span>';
                    }
                }, 0);
            }
        });
    });

    // In-Dashboard Notifications Dropdown & Realtime updates
    const notifBtn = document.getElementById('notificationBtn');
    const notifDropdown = document.getElementById('notificationDropdown');
    const notifBadge = document.getElementById('notificationBadge');
    const notifList = document.getElementById('notificationList');
    const notifUnreadPill = document.getElementById('notificationUnreadPill');
    const notifMarkAllBtn = document.getElementById('notificationMarkAllBtn');

    if (notifBtn && notifDropdown) {
        let isDropdownOpen = false;

        function formatTimeAgo(isoString) {
            if (!isoString) return '';
            const date = new Date(isoString);
            const now = new Date();
            const diffSeconds = Math.max(0, Math.floor((now - date) / 1000));
            if (diffSeconds < 60) return 'just now';
            const diffMinutes = Math.floor(diffSeconds / 60);
            if (diffMinutes < 60) return `${diffMinutes}m ago`;
            const diffHours = Math.floor(diffMinutes / 60);
            if (diffHours < 24) return `${diffHours}h ago`;
            const diffDays = Math.floor(diffHours / 24);
            return `${diffDays}d ago`;
        }

        function getNotificationIcon(type) {
            if (type === 'activity_completed') {
                return '<div class="notification-icon-wrap notification-icon-activity">🎯</div>';
            } else if (type === 'recommendation_generated') {
                return '<div class="notification-icon-wrap notification-icon-recommendation">💡</div>';
            } else if (type === 'teacher_assigned') {
                return '<div class="notification-icon-wrap notification-icon-assignment">📚</div>';
            }
            return '<div class="notification-icon-wrap notification-icon-activity">🔔</div>';
        }

        async function fetchNotifications(showLoader = false) {
            try {
                if (showLoader && notifList) {
                    notifList.innerHTML = '<div class="notification-empty">Loading updates...</div>';
                }
                const res = await fetch('/api/notifications');
                if (!res.ok) return;
                const data = await res.json();
                updateBadge(data.unread_count);
                renderList(data.notifications);
            } catch (err) {
                console.error('Error fetching notifications:', err);
            }
        }

        function updateBadge(count) {
            if (!notifBadge) return;
            if (count > 0) {
                notifBadge.textContent = count > 99 ? '99+' : count;
                notifBadge.style.display = 'inline-block';
                if (notifUnreadPill) {
                    notifUnreadPill.textContent = `${count} new`;
                    notifUnreadPill.style.display = 'inline-block';
                }
            } else {
                notifBadge.style.display = 'none';
                if (notifUnreadPill) {
                    notifUnreadPill.style.display = 'none';
                }
            }
        }

        function renderList(notifications) {
            if (!notifList) return;
            if (!notifications || notifications.length === 0) {
                notifList.innerHTML = '<div class="notification-empty">No updates yet. Notifications appear here when activities are completed or recommendations are ready.</div>';
                return;
            }

            notifList.innerHTML = notifications.map(n => {
                const unreadClass = n.is_read ? '' : 'unread';
                const timeAgo = formatTimeAgo(n.created_at);
                const iconHtml = getNotificationIcon(n.notification_type);
                const dotHtml = n.is_read ? '' : '<span class="notification-unread-dot"></span>';

                return `
                    <div class="notification-item ${unreadClass}" data-id="${n.id}" data-link="${n.link || ''}">
                        ${iconHtml}
                        <div class="notification-content">
                            <div class="notification-text">${n.message}</div>
                            <div class="notification-meta">
                                <span>${timeAgo}</span>
                                ${dotHtml}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            // Attach click handler to each item
            notifList.querySelectorAll('.notification-item').forEach(item => {
                item.addEventListener('click', async () => {
                    const id = item.getAttribute('data-id');
                    const link = item.getAttribute('data-link');

                    // Mark as read in background
                    try {
                        await fetch(`/api/notifications/${id}/read`, { method: 'POST' });
                        item.classList.remove('unread');
                        const dot = item.querySelector('.notification-unread-dot');
                        if (dot) dot.remove();
                        fetchNotifications();
                    } catch (e) {
                        console.error('Failed to mark read', e);
                    }

                    if (link) {
                        window.location.href = link;
                    }
                });
            });
        }

        function closeNotificationDropdown() {
            isDropdownOpen = false;
            if (notifDropdown) notifDropdown.style.display = 'none';
            if (notifBtn) notifBtn.setAttribute('aria-expanded', 'false');
        }

        if (!notifBtn._notifBound) {
            notifBtn._notifBound = true;
            notifBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                isDropdownOpen = !isDropdownOpen;
                if (isDropdownOpen) {
                    // Close any open navigation dropdowns when opening notifications
                    closeAllNavDropdowns();
                    notifDropdown.style.display = 'block';
                    notifBtn.setAttribute('aria-expanded', 'true');
                    fetchNotifications();
                } else {
                    closeNotificationDropdown();
                }
            });
        }

        // Mark all as read button
        if (notifMarkAllBtn && !notifMarkAllBtn._bound) {
            notifMarkAllBtn._bound = true;
            notifMarkAllBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                try {
                    await fetch('/api/notifications/mark-all-read', { method: 'POST' });
                    updateBadge(0);
                    notifList.querySelectorAll('.notification-item.unread').forEach(el => {
                        el.classList.remove('unread');
                        const dot = el.querySelector('.notification-unread-dot');
                        if (dot) dot.remove();
                    });
                } catch (e) {
                    console.error('Failed to mark all as read', e);
                }
            });
        }

        // Initial fetch on page load
        fetchNotifications();
    }

    // Helper functions for Navigation & User Profile Dropdowns
    function closeNavDropdown(container) {
        if (!container) return;
        container.classList.remove('open');
        const toggle = container.querySelector('.nav-dropdown-toggle, .user-dropdown-toggle, [data-toggle="dropdown"], [aria-expanded]');
        if (toggle) {
            toggle.setAttribute('aria-expanded', 'false');
            toggle.blur(); // Clear keyboard/focus trap so :focus-within doesn't retain open state
        }
        const menu = container.querySelector('.dropdown-menu');
        if (menu) {
            menu.style.display = '';
        }
    }

    function openNavDropdown(container, toggle) {
        if (!container) return;
        // Close other open nav dropdowns first
        document.querySelectorAll('.nav-dropdown.open, .user-dropdown.open').forEach(d => {
            if (d !== container) closeNavDropdown(d);
        });
        // Close notification dropdown if open
        const notifDropdown = document.getElementById('notificationDropdown');
        const notifBtn = document.getElementById('notificationBtn');
        if (notifDropdown && notifBtn) {
            notifDropdown.style.display = 'none';
            notifBtn.setAttribute('aria-expanded', 'false');
        }

        container.classList.add('open');
        const btn = toggle || container.querySelector('.nav-dropdown-toggle, .user-dropdown-toggle, [data-toggle="dropdown"], [aria-expanded]');
        if (btn) {
            btn.setAttribute('aria-expanded', 'true');
        }
        const menu = container.querySelector('.dropdown-menu');
        if (menu) {
            menu.style.display = 'block';
        }
    }

    function closeAllNavDropdowns() {
        document.querySelectorAll('.nav-dropdown.open, .user-dropdown.open').forEach(d => {
            closeNavDropdown(d);
        });
    }

    // Global Navigation Dropdowns (Click, Touch & Keyboard Toggle)
    const dropdownToggles = document.querySelectorAll('.nav-dropdown-toggle, .user-dropdown-toggle, [data-toggle="dropdown"]');
    dropdownToggles.forEach(btn => {
        if (btn._navDropdownBound) return; // Prevent duplicate event listeners on repeated interactions
        btn._navDropdownBound = true;

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();
            const parent = btn.closest('.nav-dropdown, .user-dropdown') || btn.parentElement;
            if (!parent) return;

            const isOpen = parent.classList.contains('open');
            if (isOpen) {
                closeNavDropdown(parent);
            } else {
                openNavDropdown(parent, btn);
            }
        });
    });

    // Dismiss dropdowns on outside click (only register once on document)
    if (!document._navbarDropdownOutsideBound) {
        document._navbarDropdownOutsideBound = true;

        document.addEventListener('click', (e) => {
            const clickedNavDropdown = e.target.closest('.nav-dropdown, .user-dropdown');
            document.querySelectorAll('.nav-dropdown.open, .user-dropdown.open').forEach(d => {
                if (d !== clickedNavDropdown) {
                    closeNavDropdown(d);
                }
            });

            const notifDropdown = document.getElementById('notificationDropdown');
            const notifBtn = document.getElementById('notificationBtn');
            if (notifDropdown && notifBtn) {
                if (!notifDropdown.contains(e.target) && !notifBtn.contains(e.target)) {
                    notifDropdown.style.display = 'none';
                    notifBtn.setAttribute('aria-expanded', 'false');
                }
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                document.querySelectorAll('.nav-dropdown.open, .user-dropdown.open').forEach(d => {
                    const toggle = d.querySelector('.nav-dropdown-toggle, .user-dropdown-toggle, [data-toggle="dropdown"], [aria-expanded]');
                    closeNavDropdown(d);
                    if (toggle) toggle.focus();
                });
                const notifDropdown = document.getElementById('notificationDropdown');
                const notifBtn = document.getElementById('notificationBtn');
                if (notifDropdown && notifBtn) {
                    notifDropdown.style.display = 'none';
                    notifBtn.setAttribute('aria-expanded', 'false');
                    notifBtn.focus();
                }
            }
        });
    }
});


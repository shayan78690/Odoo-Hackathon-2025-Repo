document.addEventListener('DOMContentLoaded', function() {
    // Tab functionality for profile page
    const tabButtons = document.querySelectorAll('.tab-btn');
    if (tabButtons.length > 0) {
        tabButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Remove active class from all buttons and content
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
                
                // Add active class to clicked button
                this.classList.add('active');
                
                // Show corresponding content
                const tabId = this.getAttribute('data-tab');
                document.getElementById(tabId + '-tab').classList.add('active');
            });
        });
    }
    
    // Voting system
    const voteButtons = document.querySelectorAll('.vote-btn');
    voteButtons.forEach(button => {
        button.addEventListener('click', function() {
            const voteType = this.classList.contains('upvote') ? 'up' : 'down';
            const contentType = this.getAttribute('data-type'); // 'question' or 'answer'
            const contentId = this.getAttribute('data-id');
            
            fetch('/vote', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    type: voteType,
                    question_id: contentType === 'question' ? contentId : null,
                    answer_id: contentType === 'answer' ? contentId : null
                })
            })
            .then(response => response.json())
            .then(data => {
                // Update vote count display
                const voteCountElement = this.closest('.vote-section').querySelector('.vote-count');
                voteCountElement.textContent = data.score;
                
                // Visual feedback
                if (voteType === 'up') {
                    this.style.color = 'var(--primary-color)';
                    this.closest('.vote-section').querySelector('.downvote').style.color = 'var(--gray-color)';
                } else {
                    this.style.color = 'var(--danger-color)';
                    this.closest('.vote-section').querySelector('.upvote').style.color = 'var(--gray-color)';
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });
    
    // Accept answer functionality
    const acceptButtons = document.querySelectorAll('.accept-btn');
    acceptButtons.forEach(button => {
        button.addEventListener('click', function() {
            const answerId = this.getAttribute('data-id');
            
            fetch('/accept_answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    answer_id: answerId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update UI
                    const answerCard = this.closest('.answer-card');
                    answerCard.classList.add('accepted-answer');
                    
                    // Remove all accepted labels first
                    document.querySelectorAll('.accepted-label').forEach(label => label.remove());
                    
                    // Add accepted label
                    const acceptedLabel = document.createElement('span');
                    acceptedLabel.className = 'accepted-label';
                    acceptedLabel.textContent = 'Accepted';
                    this.insertAdjacentElement('afterend', acceptedLabel);
                    
                    // Remove the accept button
                    this.remove();
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });
    
    // Search form submission
    const searchForm = document.querySelector('.search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const searchInput = this.querySelector('input[name="search"]');
            if (searchInput.value.trim() === '') {
                e.preventDefault();
            }
        });
    }
});


// Add this to your existing JavaScript

// Notification system
if (document.getElementById('notification-bell')) {
    const notificationBell = document.getElementById('notification-bell');
    const notificationDropdown = document.getElementById('notification-dropdown');
    const notificationList = document.getElementById('notification-list');
    
    // Load notifications
    function loadNotifications() {
        fetch('/notifications')
            .then(response => response.json())
            .then(data => {
                if (data.length > 0) {
                    document.getElementById('notification-count').textContent = data.length;
                    notificationList.innerHTML = data.map(n => `
                        <div class="notification-item ${n.is_read ? '' : 'unread'}" data-id="${n.id}">
                            <p>${n.content}</p>
                            <small>${n.created_at}</small>
                        </div>
                    `).join('');
                } else {
                    notificationList.innerHTML = '<div class="notification-item"><p>No new notifications</p></div>';
                }
            });
    }
    
    // Toggle dropdown
    notificationBell.addEventListener('click', (e) => {
        e.preventDefault();
        notificationDropdown.style.display = notificationDropdown.style.display === 'block' ? 'none' : 'block';
        loadNotifications();
    });
    
    // Click notification
    notificationList.addEventListener('click', (e) => {
        const item = e.target.closest('.notification-item');
        if (item) {
            const id = item.getAttribute('data-id');
            fetch(`/notifications/mark_read/${id}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        item.classList.remove('unread');
                    }
                });
        }
    });
    
    // Close when clicking outside
    document.addEventListener('click', (e) => {
        if (!notificationBell.contains(e.target) && !notificationDropdown.contains(e.target)) {
            notificationDropdown.style.display = 'none';
        }
    });
    
    // Poll for new notifications every 30 seconds
    setInterval(loadNotifications, 30000);
    loadNotifications();
}
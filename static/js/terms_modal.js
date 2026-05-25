document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const modalOverlay = document.getElementById('termsModalOverlay');
    const modalContent = document.getElementById('termsContent');
    const formCheckbox = document.getElementById('formTermsCheckbox');
    const openLinks = document.querySelectorAll('.terms-trigger-link');
    const closeBtn = document.getElementById('termsCloseBtn');

    if (!modalOverlay) return; // Exit if modal not present

    // Open Modal
    openLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            modalOverlay.classList.add('show');
            document.body.style.overflow = 'hidden'; // Prevent background scrolling
            checkScroll(); // Check initially in case content is short
        });
    });

    // Close Modal
    function closeModal() {
        modalOverlay.classList.remove('show');
        document.body.style.overflow = '';
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }

    // Close on click outside
    modalOverlay.addEventListener('click', function(e) {
        if (e.target === modalOverlay) {
            closeModal();
        }
    });

    // Scroll Detection
    let scrolledToBottom = false;

    function checkScroll() {
        if (scrolledToBottom) return;

        // Allow a small buffer (e.g., 5px) for calculation errors
        if (modalContent.scrollHeight - modalContent.scrollTop - modalContent.clientHeight < 10) {
            scrolledToBottom = true;
        }
    }

    modalContent.addEventListener('scroll', checkScroll);

    // Sync form checkbox with modal (if user unchecks form checkbox)
    if (formCheckbox) {
        formCheckbox.addEventListener('click', function(e) {
            // If user tries to check it directly without reading, open modal
            if (this.checked && !scrolledToBottom) {
                e.preventDefault();
                this.checked = false;
                modalOverlay.classList.add('show');
                document.body.style.overflow = 'hidden';
                checkScroll();
            }
        });
    }
});

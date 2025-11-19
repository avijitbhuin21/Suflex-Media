export function showModal(title, message, type = 'info') {
    const modal = document.getElementById('messageModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalMessage = document.getElementById('modalMessage');
    const modalContent = modal.querySelector('.modal-content');

    modalTitle.textContent = title;
    modalMessage.style.whiteSpace = 'pre-line';

    const urlRegex = /(https?:\/\/[^\s]+)/g;
    if (urlRegex.test(message)) {
        modalMessage.innerHTML = message.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer" class="modal-url-link">$1</a>');
    } else {
        modalMessage.textContent = message;
    }

    modalContent.classList.remove('error-modal', 'success-modal');

    if (type === 'error') {
        modalContent.classList.add('error-modal');
    } else if (type === 'success') {
        modalContent.classList.add('success-modal');
    }

    modal.classList.add('show');
    
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

export function closeModal() {
    const modal = document.getElementById('messageModal');
    modal.classList.remove('show');
}

export function showCopyFeedback(button, message) {
    const originalContent = button.innerHTML;
    button.innerHTML = `<i data-lucide="check" class="w-4 h-4"></i>`;
    button.classList.add('bg-green-600', 'hover:bg-green-700');
    button.classList.remove('bg-blue-600', 'hover:bg-blue-700');

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    setTimeout(() => {
        button.innerHTML = originalContent;
        button.classList.remove('bg-green-600', 'hover:bg-green-700');
        button.classList.add('bg-blue-600', 'hover:bg-blue-700');
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }, 2000);
}

export function fallbackCopyTextToClipboard(text, button) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.width = "2em";
    textArea.style.height = "2em";
    textArea.style.padding = "0";
    textArea.style.border = "none";
    textArea.style.outline = "none";
    textArea.style.boxShadow = "none";
    textArea.style.background = "transparent";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        document.execCommand('copy');
        showCopyFeedback(button, 'Copied!');
    } catch (err) {
        showModal('Copy Failed', 'Unable to copy URL to clipboard. Please select and copy manually.', 'error');
    }

    document.body.removeChild(textArea);
}

export function initModalCloseHandlers() {
    document.addEventListener('click', function (event) {
        const modal = document.getElementById('messageModal');
        if (event.target === modal) {
            closeModal();
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            closeModal();
        }
    });
}
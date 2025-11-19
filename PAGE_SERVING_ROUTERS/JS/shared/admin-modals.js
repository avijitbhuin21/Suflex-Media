import { showModal, showCopyFeedback, fallbackCopyTextToClipboard } from './ui-utils.js';
import { authenticatedFetch } from './auth-utils.js';

let currentLinkTextInput = null;
let currentLinkSelectedText = '';
let currentLinkBeforeText = '';
let currentLinkAfterText = '';
let currentLinkStart = 0;
let currentContentEditableElement = null;

export function showLinkDialog(textInput, selectedText, beforeText, afterText, start) {
    currentLinkTextInput = textInput;
    currentLinkSelectedText = selectedText;
    currentLinkBeforeText = beforeText;
    currentLinkAfterText = afterText;
    currentLinkStart = start;

    const linkModal = document.getElementById('linkModal');
    const linkUrlInput = document.getElementById('linkUrl');
    const linkDisplayNameInput = document.getElementById('linkDisplayName');

    if (!linkModal || !linkUrlInput || !linkDisplayNameInput) return;

    linkUrlInput.value = '';
    linkDisplayNameInput.value = selectedText || '';
    linkModal.classList.add('show');

    setTimeout(() => {
        linkUrlInput.focus();
    }, 100);

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

export function closeLinkModal() {
    const linkModal = document.getElementById('linkModal');
    if (!linkModal) return;
    
    linkModal.classList.remove('show');
    currentLinkTextInput = null;
    currentLinkSelectedText = '';
    currentLinkBeforeText = '';
    currentLinkAfterText = '';
    currentLinkStart = 0;
}

export function insertLink() {
    if (currentContentEditableElement) {
        insertLinkInContentEditable();
        return;
    }

    const linkUrl = document.getElementById('linkUrl')?.value.trim();
    const linkDisplayName = document.getElementById('linkDisplayName')?.value.trim();

    if (!linkUrl) {
        alert('Please enter a URL');
        document.getElementById('linkUrl')?.focus();
        return;
    }

    if (!linkDisplayName) {
        alert('Please enter display text for the link');
        document.getElementById('linkDisplayName')?.focus();
        return;
    }

    try {
        new URL(linkUrl);
    } catch (e) {
        alert('Please enter a valid URL (including http:// or https://)');
        document.getElementById('linkUrl')?.focus();
        return;
    }

    const formattedText = `<a href="${linkUrl}">${linkDisplayName}</a>`;

    if (currentLinkTextInput) {
        currentLinkTextInput.value = currentLinkBeforeText + formattedText + currentLinkAfterText;
        const newCursorPos = currentLinkStart + formattedText.length;
        currentLinkTextInput.setSelectionRange(newCursorPos, newCursorPos);
        currentLinkTextInput.focus();
    }

    closeLinkModal();
}

function insertLinkInContentEditable() {
}

let currentBulletTextInput = null;
let currentBulletSelectedText = '';
let currentBulletBeforeText = '';
let currentBulletAfterText = '';
let currentBulletStart = 0;

export function showBulletDialog(textInput, selectedText, beforeText, afterText, start) {
    currentBulletTextInput = textInput;
    currentBulletSelectedText = selectedText;
    currentBulletBeforeText = beforeText;
    currentBulletAfterText = afterText;
    currentBulletStart = start;

    const bulletModal = document.getElementById('bulletModal');
    const bulletInputs = document.querySelectorAll('.bullet-input');

    if (!bulletModal) return;

    bulletInputs.forEach(input => input.value = '');

    if (selectedText) {
        const lines = selectedText.split('\n').filter(line => line.trim());
        lines.forEach((line, index) => {
            if (index < bulletInputs.length) {
                bulletInputs[index].value = line.trim();
            } else {
                addBulletPoint(line.trim());
            }
        });
    }

    bulletModal.classList.add('show');

    setTimeout(() => {
        const firstInput = document.querySelector('.bullet-input');
        if (firstInput) firstInput.focus();
    }, 100);

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

export function closeBulletModal() {
    const bulletModal = document.getElementById('bulletModal');
    if (!bulletModal) return;
    
    bulletModal.classList.remove('show');
    resetBulletPoints();
    currentBulletTextInput = null;
    currentBulletSelectedText = '';
    currentBulletBeforeText = '';
    currentBulletAfterText = '';
    currentBulletStart = 0;
}

export function addBulletPoint(value = '') {
    const container = document.getElementById('bulletPointsContainer');
    if (!container) return;
    
    const bulletCount = container.children.length + 1;

    const bulletItem = document.createElement('div');
    bulletItem.className = 'bullet-point-item flex items-center gap-2';
    bulletItem.innerHTML = `
        <input type="text" class="bullet-input form-input flex-1" placeholder="Bullet point ${bulletCount}" value="${value}" />
        <button type="button" class="remove-bullet-btn text-white/50 hover:text-red-500 transition-colors p-1" title="Remove">
            <i data-lucide="x" class="w-4 h-4"></i>
        </button>
    `;

    container.appendChild(bulletItem);
    
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    const newInput = bulletItem.querySelector('.bullet-input');
    if (newInput) newInput.focus();
}

export function resetBulletPoints() {
    const container = document.getElementById('bulletPointsContainer');
    if (!container) return;
    
    container.innerHTML = `
        <div class="bullet-point-item flex items-center gap-2">
            <input type="text" class="bullet-input form-input flex-1" placeholder="Bullet point 1" />
            <button type="button" class="remove-bullet-btn text-white/50 hover:text-red-500 transition-colors p-1" title="Remove">
                <i data-lucide="x" class="w-4 h-4"></i>
            </button>
        </div>
        <div class="bullet-point-item flex items-center gap-2">
            <input type="text" class="bullet-input form-input flex-1" placeholder="Bullet point 2" />
            <button type="button" class="remove-bullet-btn text-white/50 hover:text-red-500 transition-colors p-1" title="Remove">
                <i data-lucide="x" class="w-4 h-4"></i>
            </button>
        </div>
    `;
    
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

export function insertBulletList() {
    if (currentContentEditableElement) {
        insertBulletListInContentEditable();
        return;
    }

    const bulletInputs = document.querySelectorAll('.bullet-input');
    const bulletPoints = [];

    bulletInputs.forEach(input => {
        const value = input.value.trim();
        if (value) {
            bulletPoints.push(value);
        }
    });

    if (bulletPoints.length === 0) {
        alert('Please enter at least one bullet point');
        const firstInput = document.querySelector('.bullet-input');
        if (firstInput) firstInput.focus();
        return;
    }

    const listItems = bulletPoints.map(point => `<li> • ${point}</li>`);
    const formattedText = `<ul>\n${listItems.join('\n')}\n</ul>`;

    if (currentBulletTextInput) {
        currentBulletTextInput.value = currentBulletBeforeText + formattedText + currentBulletAfterText;
        const newCursorPos = currentBulletStart + formattedText.length;
        currentBulletTextInput.setSelectionRange(newCursorPos, newCursorPos);
        currentBulletTextInput.focus();
    }

    closeBulletModal();
}

function insertBulletListInContentEditable() {
}

let currentDeleteBlogId = null;
let currentDeleteBlogTitle = '';

export function showDeleteConfirmModal(blogId, blogTitle) {
    currentDeleteBlogId = blogId;
    currentDeleteBlogTitle = blogTitle;

    const deleteModal = document.getElementById('deleteConfirmModal');
    const deleteBlogTitleElement = document.getElementById('deleteBlogTitle');
    const confirmCheckbox = document.getElementById('confirmDeleteCheckbox');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

    if (!deleteModal || !deleteBlogTitleElement || !confirmCheckbox || !confirmDeleteBtn) return;

    deleteBlogTitleElement.textContent = blogTitle;
    confirmCheckbox.checked = false;
    confirmDeleteBtn.disabled = true;
    deleteModal.classList.add('show');

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

export function closeDeleteConfirmModal() {
    const deleteModal = document.getElementById('deleteConfirmModal');
    if (!deleteModal) return;
    
    deleteModal.classList.remove('show');
    currentDeleteBlogId = null;
    currentDeleteBlogTitle = '';
}

export function updateDeleteButtonState() {
    const confirmCheckbox = document.getElementById('confirmDeleteCheckbox');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

    if (confirmCheckbox && confirmDeleteBtn) {
        confirmDeleteBtn.disabled = !confirmCheckbox.checked;
    }
}

export async function confirmDeleteBlog(apiEndpoint, fetchCallback) {
    if (!currentDeleteBlogId) {
        showModal('Error', 'No item selected for deletion', 'error');
        return;
    }

    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    if (!confirmDeleteBtn) return;

    try {
        const originalText = confirmDeleteBtn.innerHTML;
        confirmDeleteBtn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 mr-2 animate-spin"></i>Deleting...';
        confirmDeleteBtn.disabled = true;

        const response = await authenticatedFetch(`${apiEndpoint}/${currentDeleteBlogId}`, {
            method: 'DELETE'
        });

        confirmDeleteBtn.innerHTML = originalText;
        confirmDeleteBtn.disabled = false;

        const result = await response.json();

        if (result.status === 'success') {
            let message = `"${currentDeleteBlogTitle}" has been permanently deleted from the database.`;
            showModal('Success', message, 'success');
            closeDeleteConfirmModal();
            if (fetchCallback) fetchCallback();
        } else {
            showModal('Error', result.message || 'Failed to delete item', 'error');
        }

    } catch (error) {
        confirmDeleteBtn.innerHTML = '<i data-lucide="trash-2" class="w-4 h-4 mr-2"></i>Delete';
        confirmDeleteBtn.disabled = false;
        showModal('Error', 'An error occurred while deleting. Please try again.', 'error');
    }
}

let currentBlogUrl = '';

export function showBlogUrl(blogSlug, blogTitle, urlPath = 'blog') {
    blogSlug = blogSlug.replace("[quotetation_here]", "'");
    blogTitle = blogTitle.replace("[quotetation_here]", "'");

    if (!blogSlug) {
        showModal('Error', 'Slug not found', 'error');
        return;
    }

    const baseUrl = window.location.origin;
    const blogUrl = `${baseUrl}/${urlPath}/${blogSlug}`;
    currentBlogUrl = blogUrl;

    const urlModal = document.getElementById('blogUrlModal');
    const urlBlogTitle = document.getElementById('urlBlogTitle');
    const blogUrlDisplay = document.getElementById('blogUrlDisplay');

    if (!urlModal || !urlBlogTitle || !blogUrlDisplay) return;

    urlBlogTitle.textContent = blogTitle;
    blogUrlDisplay.value = blogUrl;
    urlModal.classList.add('show');

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

export function closeBlogUrlModal() {
    const urlModal = document.getElementById('blogUrlModal');
    if (!urlModal) return;
    
    urlModal.classList.remove('show');
    currentBlogUrl = '';
}

export function copyBlogUrl() {
    const blogUrlDisplay = document.getElementById('blogUrlDisplay');
    const copyBtn = document.getElementById('copyUrlBtn');

    if (!blogUrlDisplay || !copyBtn) return;

    blogUrlDisplay.select();
    blogUrlDisplay.setSelectionRange(0, 99999);

    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(currentBlogUrl).then(() => {
            showCopyFeedback(copyBtn, 'Copied!');
        }).catch(() => {
            fallbackCopyTextToClipboard(currentBlogUrl, copyBtn);
        });
    } else {
        fallbackCopyTextToClipboard(currentBlogUrl, copyBtn);
    }
}

export function openBlogInNewTab() {
    if (currentBlogUrl) {
        window.open(currentBlogUrl, '_blank', 'noopener,noreferrer');
    }
}

export function initModalEventListeners() {
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            closeLinkModal();
            closeBulletModal();
            closeDeleteConfirmModal();
            closeBlogUrlModal();
        }
    });

    document.addEventListener('click', function (event) {
        const linkModal = document.getElementById('linkModal');
        if (event.target === linkModal) {
            closeLinkModal();
        }

        const bulletModal = document.getElementById('bulletModal');
        if (event.target === bulletModal) {
            closeBulletModal();
        }

        const deleteModal = document.getElementById('deleteConfirmModal');
        if (event.target === deleteModal) {
            closeDeleteConfirmModal();
        }

        const urlModal = document.getElementById('blogUrlModal');
        if (event.target === urlModal) {
            closeBlogUrlModal();
        }

        if (event.target.id === 'addBulletBtn' || event.target.closest('#addBulletBtn')) {
            event.preventDefault();
            addBulletPoint();
        }

        if (event.target.closest('.remove-bullet-btn')) {
            event.preventDefault();
            const bulletItem = event.target.closest('.bullet-point-item');
            const container = document.getElementById('bulletPointsContainer');

            if (container && container.children.length > 1) {
                bulletItem.remove();
            } else {
                const input = bulletItem?.querySelector('.bullet-input');
                if (input) input.value = '';
            }
        }
    });

    const confirmDeleteCheckbox = document.getElementById('confirmDeleteCheckbox');
    if (confirmDeleteCheckbox) {
        confirmDeleteCheckbox.addEventListener('change', updateDeleteButtonState);
    }

    document.addEventListener('keydown', function (event) {
        const linkModal = document.getElementById('linkModal');
        if (linkModal && linkModal.classList.contains('show')) {
            if (event.key === 'Enter') {
                event.preventDefault();
                insertLink();
            }
        }

        const bulletModal = document.getElementById('bulletModal');
        if (bulletModal && bulletModal.classList.contains('show')) {
            if (event.key === 'Enter') {
                if (event.target.classList.contains('bullet-input')) {
                    event.preventDefault();
                    addBulletPoint();
                } else {
                    event.preventDefault();
                    insertBulletList();
                }
            }
        }

        const deleteModal = document.getElementById('deleteConfirmModal');
        if (deleteModal && deleteModal.classList.contains('show')) {
            if (event.key === 'Enter') {
                event.preventDefault();
                const confirmCheckbox = document.getElementById('confirmDeleteCheckbox');
                if (confirmCheckbox && confirmCheckbox.checked) {
                }
            }
        }

        const urlModal = document.getElementById('blogUrlModal');
        if (urlModal && urlModal.classList.contains('show')) {
            if (event.key === 'Enter') {
                event.preventDefault();
                openBlogInNewTab();
            }
        }
    });

    document.addEventListener('change', function (event) {
        if (event.target.id === 'confirmDeleteCheckbox') {
            updateDeleteButtonState();
        }
    });
}
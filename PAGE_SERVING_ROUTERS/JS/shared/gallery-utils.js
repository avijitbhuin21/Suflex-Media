let galleryState = {
    isCollapsed: false
};

export function toggleGallerySection() {
    const leftSection = document.getElementById('leftSection');
    
    if (!leftSection) {
        return;
    }
    
    galleryState.isCollapsed = !galleryState.isCollapsed;
    
    if (galleryState.isCollapsed) {
        leftSection.classList.add('collapsed');
    } else {
        leftSection.classList.remove('collapsed');
    }
}

export function initGalleryToggle() {
    const toggleBtn = document.getElementById('toggleGalleryBtn');
    const galleryHeader = document.getElementById('galleryHeader');
    const leftSection = document.getElementById('leftSection');
    
    if (!toggleBtn || !galleryHeader || !leftSection) {
        return;
    }
    
    toggleBtn.addEventListener('click', function(event) {
        event.preventDefault();
        event.stopPropagation();
        toggleGallerySection();
    });
    
    galleryHeader.addEventListener('click', function(event) {
        const isTabButton = event.target.closest('.left-tab-button');
        const isToggleButton = event.target === toggleBtn || toggleBtn.contains(event.target);
        
        if (isTabButton) {
            return;
        }
        
        if (!isToggleButton && galleryState.isCollapsed) {
            toggleGallerySection();
        }
    });
    
    const tabButtons = document.querySelectorAll('.left-tab-button');
    tabButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            event.stopPropagation();
        });
    });
}

export function initGalleryOnLoad() {
    document.addEventListener('DOMContentLoaded', function() {
        initGalleryToggle();
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    });
}
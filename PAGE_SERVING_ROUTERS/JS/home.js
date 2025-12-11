document.addEventListener('DOMContentLoaded', function () {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');

    if (hamburger) {
        hamburger.addEventListener('click', function () {
            hamburger.classList.toggle('active');
            navLinks.classList.toggle('active');
        });

        const links = navLinks.querySelectorAll('a:not(.dropdown-toggle)');
        links.forEach(link => {
            link.addEventListener('click', function () {
                hamburger.classList.remove('active');
                navLinks.classList.remove('active');
            });
        });
    }

    const dropdown = document.querySelector('.dropdown');
    const dropdownToggle = document.querySelector('.dropdown-toggle');

    if (dropdown && dropdownToggle) {
        dropdownToggle.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (window.innerWidth <= 768) {
                dropdown.classList.toggle('active');
            }
        });

        document.addEventListener('click', function (e) {
            if (window.innerWidth <= 768 && !dropdown.contains(e.target)) {
                dropdown.classList.remove('active');
            }
        });
    }

    document.querySelectorAll('.faq-item').forEach(item => {
        item.addEventListener('click', () => {
            const currentlyActive = document.querySelector('.faq-item.active');
            if (currentlyActive && currentlyActive !== item) {
                currentlyActive.classList.remove('active');
                currentlyActive.querySelector('.icon').textContent = '+';
            }

            item.classList.toggle('active');
            const icon = item.querySelector('.icon');
            if (item.classList.contains('active')) {
                icon.textContent = '-';
            } else {
                icon.textContent = '+';
            }
        });
    });

    const insightsContainer = document.querySelector('.insights-cards-container');
    const prevBtn = document.getElementById('prev-insight-btn');
    const nextBtn = document.getElementById('next-insight-btn');

    if (insightsContainer && prevBtn && nextBtn) {
        const insightsCards = insightsContainer.querySelector('.insights-cards');
        const card = insightsCards.querySelector('.insight-card');
        if (card) {
            const getScrollAmount = () => {
                const cardWidth = card.offsetWidth;
                const gap = parseFloat(window.getComputedStyle(insightsCards).gap) || 0;
                return cardWidth + gap;
            }

            prevBtn.addEventListener('click', () => {
                insightsContainer.scrollBy({
                    left: -getScrollAmount(),
                    behavior: 'smooth'
                });
            });

            nextBtn.addEventListener('click', () => {
                insightsContainer.scrollBy({
                    left: getScrollAmount(),
                    behavior: 'smooth'
                });
            });

            window.addEventListener('resize', () => {
                // No need to do anything here as getScrollAmount will be called on click
            });
        }
    }
});
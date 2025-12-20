(function () {
    'use strict';

    const DEFAULT_OPTIONS = {
        minZoom: 1,
        maxZoom: 3,
        zoomStep: 0.1,
        smoothness: 0.1,
        containerSelector: '[data-zoom-container]'
    };

    class ZoomController {
        constructor(options = {}) {
            this.options = { ...DEFAULT_OPTIONS, ...options };
            this.scale = 1;
            this.translateX = 0;
            this.translateY = 0;
            this.container = null;
            this.content = null;
            this.isPanning = false;
            this.startX = 0;
            this.startY = 0;
            this.lastTranslateX = 0;
            this.lastTranslateY = 0;
            this.savedScrollTop = 0;
            this.savedScrollLeft = 0;

            this.handleWheel = this.handleWheel.bind(this);
            this.handleKeyDown = this.handleKeyDown.bind(this);
            this.handleMouseDown = this.handleMouseDown.bind(this);
            this.handleMouseMove = this.handleMouseMove.bind(this);
            this.handleMouseUp = this.handleMouseUp.bind(this);
            this.handleDoubleClick = this.handleDoubleClick.bind(this);
        }

        init() {
            this.container = document.querySelector(this.options.containerSelector);
            if (!this.container) {
                console.warn('ZoomController: Container not found with selector:', this.options.containerSelector);
                return false;
            }

            this.setupDOM();
            this.attachListeners();
            return true;
        }

        setupDOM() {
            this.container.style.overflow = 'hidden';
            this.container.style.position = 'relative';

            const wrapper = document.createElement('div');
            wrapper.className = 'zoom-content-wrapper';
            wrapper.style.cssText = `
                width: 100%;
                height: 100%;
                transform-origin: 0 0;
                will-change: transform;
                transition: transform ${this.options.smoothness}s ease-out;
            `;

            while (this.container.firstChild) {
                wrapper.appendChild(this.container.firstChild);
            }
            this.container.appendChild(wrapper);
            this.content = wrapper;
        }

        attachListeners() {
            document.addEventListener('wheel', this.handleWheel, { passive: false });
            document.addEventListener('keydown', this.handleKeyDown, { passive: false });
            this.container.addEventListener('mousedown', this.handleMouseDown);
            document.addEventListener('mousemove', this.handleMouseMove);
            document.addEventListener('mouseup', this.handleMouseUp);
            this.container.addEventListener('dblclick', this.handleDoubleClick);
        }

        handleWheel(e) {
            if (!e.ctrlKey) return;

            e.preventDefault();
            e.stopPropagation();

            this.savedScrollTop = window.scrollY;
            this.savedScrollLeft = window.scrollX;

            const rect = this.container.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            const delta = e.deltaY > 0 ? -this.options.zoomStep : this.options.zoomStep;
            const newScale = Math.min(Math.max(this.scale + delta, this.options.minZoom), this.options.maxZoom);

            if (newScale !== this.scale) {
                const scaleRatio = newScale / this.scale;

                const contentX = (mouseX - this.translateX) / this.scale;
                const contentY = (mouseY - this.translateY) / this.scale;

                this.translateX = mouseX - contentX * newScale;
                this.translateY = mouseY - contentY * newScale;

                this.scale = newScale;

                this.constrainTranslation();
                this.applyTransform();
            }

            requestAnimationFrame(() => {
                window.scrollTo(this.savedScrollLeft, this.savedScrollTop);
            });
        }

        handleKeyDown(e) {
            if (e.ctrlKey && (e.key === '+' || e.key === '=' || e.key === '-' || e.key === '0')) {
                e.preventDefault();
                e.stopPropagation();

                if (e.key === '0') {
                    this.reset();
                } else if (e.key === '+' || e.key === '=') {
                    this.zoomAtCenter(this.options.zoomStep);
                } else if (e.key === '-') {
                    this.zoomAtCenter(-this.options.zoomStep);
                }
            }
        }

        zoomAtCenter(delta) {
            this.savedScrollTop = window.scrollY;
            this.savedScrollLeft = window.scrollX;

            const rect = this.container.getBoundingClientRect();
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            const newScale = Math.min(Math.max(this.scale + delta, this.options.minZoom), this.options.maxZoom);

            if (newScale !== this.scale) {
                const scaleRatio = newScale / this.scale;

                const contentX = (centerX - this.translateX) / this.scale;
                const contentY = (centerY - this.translateY) / this.scale;

                this.translateX = centerX - contentX * newScale;
                this.translateY = centerY - contentY * newScale;

                this.scale = newScale;

                this.constrainTranslation();
                this.applyTransform();
            }

            requestAnimationFrame(() => {
                window.scrollTo(this.savedScrollLeft, this.savedScrollTop);
            });
        }

        handleMouseDown(e) {
            if (this.scale <= 1) return;
            if (e.target.closest('a, button, input, select, textarea')) return;

            this.isPanning = true;
            this.startX = e.clientX;
            this.startY = e.clientY;
            this.lastTranslateX = this.translateX;
            this.lastTranslateY = this.translateY;
            this.content.style.transition = 'none';
            this.container.style.cursor = 'grabbing';
            e.preventDefault();
        }

        handleMouseMove(e) {
            if (!this.isPanning) return;

            const deltaX = e.clientX - this.startX;
            const deltaY = e.clientY - this.startY;

            this.translateX = this.lastTranslateX + deltaX;
            this.translateY = this.lastTranslateY + deltaY;

            this.constrainTranslation();
            this.applyTransform();
        }

        handleMouseUp() {
            if (!this.isPanning) return;

            this.isPanning = false;
            this.content.style.transition = `transform ${this.options.smoothness}s ease-out`;
            this.container.style.cursor = '';
        }

        handleDoubleClick(e) {
            if (e.target.closest('a, button, input, select, textarea')) return;
            e.preventDefault();
            this.reset();
        }

        constrainTranslation() {
            const rect = this.container.getBoundingClientRect();
            const contentWidth = rect.width * this.scale;
            const contentHeight = rect.height * this.scale;

            const minX = rect.width - contentWidth;
            const minY = rect.height - contentHeight;

            if (this.scale <= 1) {
                this.translateX = 0;
                this.translateY = 0;
            } else {
                this.translateX = Math.min(0, Math.max(minX, this.translateX));
                this.translateY = Math.min(0, Math.max(minY, this.translateY));
            }
        }

        applyTransform() {
            this.content.style.transform = `translate(${this.translateX}px, ${this.translateY}px) scale(${this.scale})`;
        }

        reset() {
            this.savedScrollTop = window.scrollY;
            this.savedScrollLeft = window.scrollX;

            this.scale = 1;
            this.translateX = 0;
            this.translateY = 0;
            this.applyTransform();

            requestAnimationFrame(() => {
                window.scrollTo(this.savedScrollLeft, this.savedScrollTop);
            });
        }

        destroy() {
            document.removeEventListener('wheel', this.handleWheel);
            document.removeEventListener('keydown', this.handleKeyDown);
            this.container.removeEventListener('mousedown', this.handleMouseDown);
            document.removeEventListener('mousemove', this.handleMouseMove);
            document.removeEventListener('mouseup', this.handleMouseUp);
            this.container.removeEventListener('dblclick', this.handleDoubleClick);

            if (this.content && this.content.parentNode === this.container) {
                while (this.content.firstChild) {
                    this.container.appendChild(this.content.firstChild);
                }
                this.container.removeChild(this.content);
            }
        }

        getZoomLevel() {
            return this.scale;
        }

        setZoomLevel(level) {
            const newScale = Math.min(Math.max(level, this.options.minZoom), this.options.maxZoom);
            this.scale = newScale;
            this.constrainTranslation();
            this.applyTransform();
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        const container = document.querySelector('[data-zoom-container]');
        if (container) {
            const options = {};

            if (container.dataset.zoomMin) {
                options.minZoom = parseFloat(container.dataset.zoomMin);
            }
            if (container.dataset.zoomMax) {
                options.maxZoom = parseFloat(container.dataset.zoomMax);
            }
            if (container.dataset.zoomStep) {
                options.zoomStep = parseFloat(container.dataset.zoomStep);
            }

            window.zoomController = new ZoomController(options);
            window.zoomController.init();
        }
    });

    window.ZoomController = ZoomController;
})();

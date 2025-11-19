export class ExpandableTabs {
    constructor(container, options = {}) {
        this.container = container;
        this.tabs = options.tabs || [];
        this.activeColor = options.activeColor || 'text-blue-600';
        this.onChange = options.onChange || (() => { });
        this.selected = null;
        this.init();
    }
    
    init() {
        this.render();
        this.bindEvents();
    }
    
    render() {
        this.container.innerHTML = '';
        this.tabs.forEach((tab, index) => {
            if (tab.type === 'separator') {
                const separator = this.createSeparator();
                this.container.appendChild(separator);
            } else {
                const button = this.createTabButton(tab, index);
                this.container.appendChild(button);
            }
        });
    }
    
    createSeparator() {
        const separator = document.createElement('div');
        separator.className = 'separator';
        separator.style.background = 'rgba(255, 255, 255, 0.3)';
        separator.setAttribute('aria-hidden', 'true');
        return separator;
    }
    
    createTabButton(tab, index) {
        const button = document.createElement('button');
        const isSelected = this.selected === index;
        button.className = `tab-button relative flex items-center text-sm font-medium tracking-wide transition-all duration-[600ms] ${isSelected ? 'selected' : ''}`;
        
        if (isSelected) {
            button.style.color = this.activeColor || 'rgb(147, 197, 253)';
        } else {
            button.style.color = 'rgba(255, 255, 255, 0.6)';
        }
        
        button.dataset.index = index;
        
        const iconWrapper = document.createElement('div');
        iconWrapper.className = 'flex-shrink-0';
        iconWrapper.innerHTML = `<i data-lucide="${tab.icon}" class="w-4 h-4"></i>`;
        
        const textElement = document.createElement('span');
        textElement.className = `tab-text ${isSelected ? 'expanded' : ''}`;
        textElement.textContent = tab.title;
        
        button.appendChild(iconWrapper);
        button.appendChild(textElement);
        
        button.addEventListener('mouseenter', () => {
            if (!button.classList.contains('selected')) {
                button.style.color = 'rgba(255, 255, 255, 0.9)';
            }
        });
        
        button.addEventListener('mouseleave', () => {
            if (!button.classList.contains('selected')) {
                button.style.color = 'rgba(255, 255, 255, 0.6)';
            }
        });
        
        return button;
    }
    
    handleSelect(index) {
        this.selected = index;
        const buttons = this.container.querySelectorAll('.tab-button');
        buttons.forEach((button, i) => {
            const buttonIndex = parseInt(button.dataset.index);
            const textElement = button.querySelector('.tab-text');
            if (this.selected === buttonIndex) {
                button.classList.add('selected');
                button.style.color = this.activeColor || 'rgb(147, 197, 253)';
                textElement.classList.add('expanded');
            } else {
                button.classList.remove('selected');
                button.style.color = 'rgba(255, 255, 255, 0.6)';
                textElement.classList.remove('expanded');
            }
        });
        this.onChange(this.selected);
    }
    
    bindEvents() {
        if (this.eventsbound) return;
        this.eventsbound = true;
        this.container.addEventListener('click', (e) => {
            const button = e.target.closest('.tab-button');
            if (button && button.dataset.index !== undefined) {
                this.handleSelect(parseInt(button.dataset.index));
            }
        });
    }
}
import { showModal } from './ui-utils.js';

export function initializeLabelsSection() {
    const addLabelBtn = document.getElementById('addLabelBtn');
    const labelsContainer = document.getElementById('labelsContainer');

    if (!addLabelBtn || !labelsContainer) return;

    addLabelBtn.addEventListener('click', function () {
        addLabelRow();
    });

    labelsContainer.addEventListener('click', function (e) {
        if (e.target.closest('.remove-label-btn')) {
            const labelItem = e.target.closest('.label-item');
            const allLabels = labelsContainer.querySelectorAll('.label-item');

            if (allLabels.length > 1) {
                labelItem.remove();
            } else {
                labelItem.querySelector('.label-input').value = '';
                labelItem.querySelector('.weight-input').value = '';
            }
        }
    });
}

export function addLabelRow() {
    const labelsContainer = document.getElementById('labelsContainer');
    if (!labelsContainer) return;
    
    const labelItem = document.createElement('div');
    labelItem.className = 'label-item flex items-center gap-3';
    labelItem.innerHTML = `
        <div class="flex-1">
            <input type="text" class="label-input form-input" placeholder="Enter label name..." />
        </div>
        <div class="w-24">
            <input type="number" class="weight-input form-input" placeholder="Weight" min="1" max="100" />
        </div>
        <button type="button" class="remove-label-btn text-white/50 hover:text-red-500 transition-colors p-2 rounded-lg hover:bg-white/[0.05]" title="Remove">
            <i data-lucide="x" class="w-4 h-4"></i>
        </button>
    `;
    labelsContainer.appendChild(labelItem);
    
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

export function populateLabelsFromData(labelsData) {
    const labelsContainer = document.getElementById('labelsContainer');
    const labelsNotMandatory = document.getElementById('labelsNotMandatory');

    if (!labelsContainer || !labelsNotMandatory) return;

    labelsContainer.innerHTML = '';

    if (labelsData && typeof labelsData === 'object' && Object.keys(labelsData).length > 0) {
        Object.entries(labelsData).forEach(([label, weight]) => {
            const labelItem = document.createElement('div');
            labelItem.className = 'label-item flex items-center gap-3';
            labelItem.innerHTML = `
                <div class="flex-1">
                    <input type="text" class="label-input form-input" placeholder="Enter label name..." value="${label}" />
                </div>
                <div class="w-24">
                    <input type="number" class="weight-input form-input" placeholder="Weight" min="1" max="100" value="${weight}" />
                </div>
                <button type="button" class="remove-label-btn text-white/50 hover:text-red-500 transition-colors p-2 rounded-lg hover:bg-white/[0.05]" title="Remove">
                    <i data-lucide="x" class="w-4 h-4"></i>
                </button>
            `;
            labelsContainer.appendChild(labelItem);
        });
        labelsNotMandatory.checked = false;
    } else {
        addLabelRow();
        labelsNotMandatory.checked = true;
    }

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

export function collectLabelsData() {
    const labelsNotMandatory = document.getElementById('labelsNotMandatory');
    const labelItems = document.querySelectorAll('.label-item');
    
    if (!labelsNotMandatory) return null;
    
    const labelsObj = {};
    let hasLabels = false;

    labelItems.forEach(item => {
        const labelInput = item.querySelector('.label-input').value.trim();
        const weightInput = item.querySelector('.weight-input').value.trim();

        if (labelInput && weightInput) {
            labelsObj[labelInput] = parseInt(weightInput);
            hasLabels = true;
        }
    });

    if (!labelsNotMandatory.checked && !hasLabels) {
        showModal('Labels Required', 'Please add at least one label or check the "Labels are not mandatory" option.', 'error');
        return null;
    }

    return { labels: labelsObj, labelsNotMandatory: labelsNotMandatory.checked };
}
// Inventory Modal & Item Management
(function() {
    'use strict';

    let propertyIndex = 0;

    // --- Collapsible items ---

    window.toggleItemExpand = function(summaryEl) {
        const item = summaryEl.closest('.inventory-item');
        item.classList.toggle('expanded');
    };

    // --- Modal open/close ---

    window.openAddItemModal = function() {
        const modal = document.getElementById('inventory-modal');
        const form = modal.querySelector('form');
        const title = document.getElementById('modal-title');

        title.textContent = 'Add Item';
        form.action = form.dataset.addUrl;
        form.reset();

        // Clear all property rows
        document.getElementById('properties-container').innerHTML = '';
        propertyIndex = 0;

        modal.classList.add('active');
        document.getElementById('item-name').focus();
    };

    window.openEditItemModal = function(itemId) {
        const modal = document.getElementById('inventory-modal');
        const form = modal.querySelector('form');
        const title = document.getElementById('modal-title');
        const characterId = form.dataset.characterId;

        title.textContent = 'Edit Item';
        form.action = `/character/${characterId}/inventory/${itemId}/update`;

        // Fetch item data
        fetch(`/character/${characterId}/inventory/${itemId}/json`)
            .then(r => r.json())
            .then(item => {
                document.getElementById('item-name').value = item.name || '';
                document.getElementById('item-description').value = item.description || '';
                document.getElementById('item-location').value = item.location || '';
                document.getElementById('item-quantity').value = item.quantity != null ? item.quantity : '';

                // Rebuild properties
                const container = document.getElementById('properties-container');
                container.innerHTML = '';
                propertyIndex = 0;

                if (item.properties && item.properties.length > 0) {
                    item.properties.forEach(prop => {
                        addPropertyRow(prop.stat_modified, prop.value);
                    });
                }

                modal.classList.add('active');
                document.getElementById('item-name').focus();
            })
            .catch(() => {
                alert('Failed to load item data');
            });
    };

    window.closeItemModal = function() {
        document.getElementById('inventory-modal').classList.remove('active');
    };

    // Close modal on backdrop click
    document.addEventListener('click', function(e) {
        const modal = document.getElementById('inventory-modal');
        if (modal && e.target === modal) {
            closeItemModal();
        }
    });

    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeItemModal();
        }
    });

    // --- Property rows ---

    window.addPropertyRow = function(stat, value) {
        const container = document.getElementById('properties-container');
        const idx = propertyIndex++;

        const row = document.createElement('div');
        row.className = 'property-row';
        row.innerHTML = `
            <select name="prop_stat_${idx}" class="property-select" required>
                <option value="">Select stat...</option>
                ${getStatOptions(stat)}
            </select>
            <input type="number" name="prop_value_${idx}" class="property-value" 
                   placeholder="+/−" value="${value != null ? value : ''}" required>
            <button type="button" class="btn btn-danger btn-icon" onclick="this.parentElement.remove()" title="Remove property">✕</button>
        `;

        container.appendChild(row);
    };

    function getStatOptions(selectedValue) {
        const modal = document.getElementById('inventory-modal');
        const options = JSON.parse(modal.dataset.statOptions || '[]');
        
        return options.map(([val, label]) => {
            const selected = val === selectedValue ? ' selected' : '';
            return `<option value="${val}"${selected}>${label}</option>`;
        }).join('');
    }
})();

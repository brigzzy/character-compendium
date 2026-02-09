// Spells Modal & Management
(function() {
    'use strict';

    var spellPropertyIndex = 0;

    // --- Property rows ---

    window.addSpellPropertyRow = function(stat, value) {
        var container = document.getElementById('spell-properties-container');
        var idx = spellPropertyIndex++;

        var row = document.createElement('div');
        row.className = 'property-row';
        row.innerHTML =
            '<select name="prop_stat_' + idx + '" class="property-select" required>' +
                '<option value="">Select stat...</option>' +
                getStatOptions(stat) +
            '</select>' +
            '<input type="number" name="prop_value_' + idx + '" class="property-value" ' +
                   'placeholder="+/\u2212" value="' + (value != null ? value : '') + '" required>' +
            '<button type="button" class="btn btn-danger btn-icon" onclick="this.parentElement.remove()" title="Remove property">\u2715</button>';

        container.appendChild(row);
    };

    function getStatOptions(selectedValue) {
        var modal = document.getElementById('spell-modal');
        var options = JSON.parse(modal.dataset.statOptions || '[]');

        var html = '';
        for (var i = 0; i < options.length; i++) {
            var val = options[i][0];
            var label = options[i][1];
            var selected = val === selectedValue ? ' selected' : '';
            html += '<option value="' + val + '"' + selected + '>' + label + '</option>';
        }
        return html;
    }

    // --- Modal open/close ---

    window.openAddSpellModal = function() {
        var modal = document.getElementById('spell-modal');
        var form = modal.querySelector('form');
        var title = document.getElementById('spell-modal-title');

        title.textContent = 'Add Spell';
        form.action = form.dataset.addUrl;
        form.reset();

        document.getElementById('spell-properties-container').innerHTML = '';
        spellPropertyIndex = 0;

        modal.classList.add('active');
        document.getElementById('spell-name').focus();
    };

    window.openEditSpellModal = function(spellId) {
        var modal = document.getElementById('spell-modal');
        var form = modal.querySelector('form');
        var title = document.getElementById('spell-modal-title');
        var characterId = form.dataset.characterId;

        title.textContent = 'Edit Spell';
        form.action = '/character/' + characterId + '/spell/' + spellId + '/update';

        fetch('/character/' + characterId + '/spell/' + spellId + '/json')
            .then(function(r) { return r.json(); })
            .then(function(spell) {
                document.getElementById('spell-name').value = spell.name || '';
                document.getElementById('spell-level').value = spell.level != null ? spell.level : 0;
                document.getElementById('spell-description').value = spell.description || '';

                // Rebuild properties
                var container = document.getElementById('spell-properties-container');
                container.innerHTML = '';
                spellPropertyIndex = 0;

                if (spell.properties && spell.properties.length > 0) {
                    spell.properties.forEach(function(prop) {
                        addSpellPropertyRow(prop.stat_modified, prop.value);
                    });
                }

                modal.classList.add('active');
                document.getElementById('spell-name').focus();
            })
            .catch(function() {
                alert('Failed to load spell data');
            });
    };

    window.closeSpellModal = function() {
        document.getElementById('spell-modal').classList.remove('active');
    };

    // Close on backdrop click
    document.addEventListener('click', function(e) {
        var modal = document.getElementById('spell-modal');
        if (modal && e.target === modal) {
            closeSpellModal();
        }
    });

    // Close on Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            var modal = document.getElementById('spell-modal');
            if (modal && modal.classList.contains('active')) {
                closeSpellModal();
            }
        }
    });
})();

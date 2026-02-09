// Features Modal & Management
(function() {
    'use strict';

    var featurePropertyIndex = 0;
    var KNOWN_SOURCES = ['Class', 'Feat', 'Species'];

    // --- Source field ---

    window.toggleFeatureSourceCustom = function() {
        var select = document.getElementById('feature-source');
        var custom = document.getElementById('feature-source-custom');
        if (select.value === 'Other') {
            custom.style.display = '';
            custom.focus();
        } else {
            custom.style.display = 'none';
            custom.value = '';
        }
    };

    function setSourceValue(source) {
        var select = document.getElementById('feature-source');
        var custom = document.getElementById('feature-source-custom');

        if (!source) {
            select.value = '';
            custom.style.display = 'none';
            custom.value = '';
        } else if (KNOWN_SOURCES.indexOf(source) !== -1) {
            select.value = source;
            custom.style.display = 'none';
            custom.value = '';
        } else {
            select.value = 'Other';
            custom.style.display = '';
            custom.value = source;
        }
    }

    // --- Property rows ---

    window.addFeaturePropertyRow = function(stat, value) {
        var container = document.getElementById('feature-properties-container');
        var idx = featurePropertyIndex++;

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
        var modal = document.getElementById('feature-modal');
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

    window.openAddFeatureModal = function() {
        var modal = document.getElementById('feature-modal');
        var form = modal.querySelector('form');
        var title = document.getElementById('feature-modal-title');

        title.textContent = 'Add Feature';
        form.action = form.dataset.addUrl;
        form.reset();

        setSourceValue('');
        document.getElementById('feature-properties-container').innerHTML = '';
        featurePropertyIndex = 0;

        // Show "add with effects off" option
        document.getElementById('feature-disabled-option').style.display = '';

        modal.classList.add('active');
        document.getElementById('feature-name').focus();
    };

    window.openEditFeatureModal = function(featureId) {
        var modal = document.getElementById('feature-modal');
        var form = modal.querySelector('form');
        var title = document.getElementById('feature-modal-title');
        var characterId = form.dataset.characterId;

        title.textContent = 'Edit Feature';
        form.action = '/character/' + characterId + '/feature/' + featureId + '/update';

        // Hide "add with effects off" option in edit mode
        document.getElementById('feature-disabled-option').style.display = 'none';

        fetch('/character/' + characterId + '/feature/' + featureId + '/json')
            .then(function(r) { return r.json(); })
            .then(function(feature) {
                document.getElementById('feature-name').value = feature.name || '';
                document.getElementById('feature-description').value = feature.description || '';
                setSourceValue(feature.source || '');

                // Rebuild properties
                var container = document.getElementById('feature-properties-container');
                container.innerHTML = '';
                featurePropertyIndex = 0;

                if (feature.properties && feature.properties.length > 0) {
                    feature.properties.forEach(function(prop) {
                        addFeaturePropertyRow(prop.stat_modified, prop.value);
                    });
                }

                modal.classList.add('active');
                document.getElementById('feature-name').focus();
            })
            .catch(function() {
                alert('Failed to load feature data');
            });
    };

    window.closeFeatureModal = function() {
        document.getElementById('feature-modal').classList.remove('active');
    };

    // Close modal on backdrop click
    document.addEventListener('click', function(e) {
        var modal = document.getElementById('feature-modal');
        if (modal && e.target === modal) {
            closeFeatureModal();
        }
    });

    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeFeatureModal();
        }
    });
})();

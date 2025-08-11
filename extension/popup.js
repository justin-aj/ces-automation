// Utility functions
function showStatus(message, type) {
    const statusDiv = document.getElementById('status');
    if (!statusDiv) {
        console.warn('Status div not found');
        return;
    }
    
    statusDiv.textContent = message;
    statusDiv.className = `status ${type}`;
    setTimeout(() => {
        statusDiv.textContent = '';
        statusDiv.className = 'status';
    }, 3000);
}

function generateCSV(entries) {
    const headers = ['employer_name', 'employer_role', 'email_id', 'job_link'];
    const rows = [headers.join(',')];

    entries.forEach(entry => {
        const row = headers.map(header => {
            let value = entry[header] || '';
            if (value.includes('"') || value.includes(',') || value.includes('\n')) {
                value = '"' + value.replace(/"/g, '""') + '"';
            }
            return value;
        });
        rows.push(row.join(','));
    });

    return rows.join('\n');
}

function fillForm(entry) {
    const fields = ['employer_name', 'employer_role', 'email_id', 'job_link'];
    fields.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.value = entry[id] || '';
        }
    });
}

function displayEntries() {
    const entriesList = document.getElementById('entriesList');
    if (!entriesList) {
        console.warn('Entries list element not found');
        return;
    }

    chrome.storage.local.get(['entries'], function(result) {
        const entries = result.entries || [];
        entriesList.innerHTML = '';

        if (entries.length === 0) {
            entriesList.innerHTML = '<div class="no-entries">No entries stored</div>';
            return;
        }

        entries.forEach((entry, index) => {
            const entryDiv = document.createElement('div');
            entryDiv.className = 'entry-item';
            entryDiv.innerHTML = `
                <strong>${entry.employer_name}</strong> (${entry.employer_role})<br>
                <small>${entry.email_id}</small>
                <div class="job-link">
                    <small><a href="${entry.job_link}" target="_blank" title="Open job listing">${entry.job_link ? 'View Job Listing' : 'No link provided'}</a></small>
                </div>
                <div class="entry-actions">
                    <button class="btn-edit">Edit</button>
                    <button class="btn-delete">Delete</button>
                </div>
            `;

            const editBtn = entryDiv.querySelector('.btn-edit');
            const deleteBtn = entryDiv.querySelector('.btn-delete');
            const form = document.getElementById('jobForm');
            const entriesView = document.getElementById('entriesView');
            
            if (editBtn && form && entriesView) {
                editBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    fillForm(entry);
                    form.style.display = 'block';
                    entriesView.style.display = 'none';
                });
            }

            if (deleteBtn) {
                deleteBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    if (confirm('Are you sure you want to delete this entry?')) {
                        const updatedEntries = entries.filter((_, i) => i !== index);
                        chrome.storage.local.set({ entries: updatedEntries }, function() {
                            displayEntries();
                            loadStoredEntries();
                            showStatus('Entry deleted successfully!', 'success');
                        });
                    }
                });
            }

            entriesList.appendChild(entryDiv);
        });
    });
}

function loadStoredEntries() {
    const entryCount = document.getElementById('entryCount');
    if (!entryCount) {
        console.warn('Entry count element not found');
        return;
    }

    chrome.storage.local.get(['entries'], function(result) {
        const entries = result.entries || [];
        entryCount.textContent = `${entries.length} entries stored`;
    });
}

// Main initialization
document.addEventListener('DOMContentLoaded', function() {
    // Get all DOM elements
    const form = document.getElementById('jobForm');
    const downloadBtn = document.getElementById('downloadCSV');
    const exportBtn = document.getElementById('exportToFile');
    const clearBtn = document.getElementById('clearData');
    const viewEntriesBtn = document.getElementById('viewEntries');
    const backToFormBtn = document.getElementById('backToForm');
    const entriesView = document.getElementById('entriesView');
    
    // Validate required elements exist
    if (!form || !entriesView || !viewEntriesBtn || !backToFormBtn) {
        console.error('Required DOM elements not found');
        return;
    }

    // Initialize view state
    entriesView.style.display = 'none';
    form.style.display = 'block';

    // Load any existing entries when popup opens
    loadStoredEntries();

    // View/Hide entries list
    viewEntriesBtn.addEventListener('click', function() {
        form.style.display = 'none';
        entriesView.style.display = 'block';
        displayEntries();
    });

    backToFormBtn.addEventListener('click', function() {
        form.style.display = 'block';
        entriesView.style.display = 'none';
    });

    // Form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const entry = {
            employer_name: document.getElementById('employer_name').value,
            employer_role: document.getElementById('employer_role').value,
            email_id: document.getElementById('email_id').value,
            job_link: document.getElementById('job_link').value,
            timestamp: new Date().toISOString()
        };

        chrome.storage.local.get(['entries'], function(result) {
            const entries = result.entries || [];
            entries.push(entry);
            
            chrome.storage.local.set({ entries: entries }, function() {
                showStatus('Entry saved successfully!', 'success');
                form.reset();
                loadStoredEntries();
            });
        });
    });

    // Download CSV
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
            chrome.storage.local.get(['entries'], function(result) {
                if (!result.entries || result.entries.length === 0) {
                    showStatus('No entries to download!', 'error');
                    return;
                }

                const csvContent = generateCSV(result.entries);
                const blob = new Blob([csvContent], { type: 'text/csv' });
                const url = URL.createObjectURL(blob);
                const timestamp = new Date().toISOString().split('T')[0];
                
                chrome.downloads.download({
                    url: url,
                    filename: `contacts_${timestamp}.csv`
                });
            });
        });
    }

    // Export to sample_jobs.csv
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            chrome.storage.local.get(['entries'], function(result) {
                if (!result.entries || result.entries.length === 0) {
                    showStatus('No entries to export!', 'error');
                    return;
                }

                const csvContent = generateCSV(result.entries);
                const blob = new Blob([csvContent], { type: 'text/csv' });
                const url = URL.createObjectURL(blob);
                
                const a = document.createElement('a');
                a.href = url;
                a.download = 'contacts.csv';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                showStatus('Exported to sample_jobs.csv!', 'success');
            });
        });
    }

    // Clear all data
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            if (confirm('Are you sure you want to clear all stored entries?')) {
                chrome.storage.local.set({ entries: [] }, function() {
                    showStatus('All entries cleared!', 'success');
                    loadStoredEntries();
                    displayEntries();
                });
            }
        });
    }
});

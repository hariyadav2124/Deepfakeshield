document.addEventListener("DOMContentLoaded", function() {
    
    // Drag and drop file upload handling
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file');
    const uploadForm = document.getElementById('upload-form');
    const loader = document.getElementById('loader');
    
    if (uploadArea && fileInput) {
        
        // Trigger click on file input when clicking upload area
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });
        
        // Handle drag events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.classList.add('dragover');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.classList.remove('dragover');
            }, false);
        });
        
        // Handle drop event
        uploadArea.addEventListener('drop', (e) => {
            let dt = e.dataTransfer;
            let files = dt.files;
            fileInput.files = files;
            updateFileName();
        }, false);
        
        // Handle file selection from dialog
        fileInput.addEventListener('change', updateFileName);
        
        function updateFileName() {
            if (fileInput.files.length > 0) {
                const fileName = fileInput.files[0].name;
                uploadArea.innerHTML = `<i class="upload-icon">📄</i><p>Selected: <strong>${fileName}</strong></p><p class="text-muted mt-2">Click or drag another file to change</p>`;
            }
        }
        
        // Show loader on form submit
        if (uploadForm && loader) {
            uploadForm.addEventListener('submit', (e) => {
                if (fileInput.files.length > 0) {
                    loader.style.display = 'flex';
                }
            });
        }
    }
});

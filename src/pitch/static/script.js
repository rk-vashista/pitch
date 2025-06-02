document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('uploadForm');
    const statusDiv = document.getElementById('status');
    const statusMessage = document.getElementById('status-message');
    const progressBar = document.getElementById('progress-bar');
    const progressPercentage = document.getElementById('progress-percentage');
    const resultDiv = document.getElementById('result');
    const resultContent = document.getElementById('result-content');
    const downloadButton = document.getElementById('download-report');
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');
    const elapsedTimeElement = document.getElementById('elapsed-time');
    let socket;
    let startTime;
    let elapsedTimeInterval;

    // Toast notification function
    function showToast(message, type = 'info') {
        toastMessage.textContent = message;
        toast.className = `toast show ${type}`;
        setTimeout(() => {
            toast.className = 'toast';
        }, 3000);
    }

    // Update elapsed time
    function updateElapsedTime() {
        const now = new Date();
        const elapsed = Math.floor((now - startTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        elapsedTimeElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    // Start timer
    function startTimer() {
        startTime = new Date();
        elapsedTimeInterval = setInterval(updateElapsedTime, 1000);
    }

    // Stop timer
    function stopTimer() {
        if (elapsedTimeInterval) {
            clearInterval(elapsedTimeInterval);
        }
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Validate form
        const startupName = form.elements['startup_name'].value.trim();
        const file = form.elements['file'].files[0];

        if (!startupName) {
            showToast('Please enter your startup name', 'error');
            return;
        }

        if (!file) {
            showToast('Please select a file to analyze', 'error');
            return;
        }

        // Reset UI
        statusDiv.classList.remove('hidden');
        resultDiv.classList.add('hidden');
        progressBar.style.width = '0%';
        progressPercentage.textContent = '0%';
        statusMessage.textContent = 'Starting upload...';
        document.getElementById('log-entries').innerHTML = '';
        
        // Start timer
        startTimer();

        // Create FormData
        const formData = new FormData(form);

        try {
            // Upload file
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }

            const data = await response.json();
            
            // Connect to WebSocket
            socket = new WebSocket(`ws://${window.location.host}${data.websocket_url}`);
            
            socket.onmessage = (event) => {
                const status = JSON.parse(event.data);
                const logEntries = document.getElementById('log-entries');
                
                // Update status message
                statusMessage.textContent = status.message;

                // Add log entry with animation
                if (status.message) {
                    const logEntry = document.createElement('div');
                    logEntry.className = 'log-entry p-4 bg-white rounded-lg shadow-sm border border-gray-100';
                    
                    let logContent = `
                        <div class="flex items-start space-x-3">
                            <div class="flex-shrink-0">
                                <i class="fas ${status.type === 'error' ? 'fa-exclamation-circle text-red-500' : 'fa-info-circle text-blue-500'}"></i>
                            </div>
                            <div class="flex-1 min-w-0">
                                <p class="text-sm font-medium text-gray-900">${status.message}</p>
                    `;
                    
                    if (status.agent) {
                        logContent += `
                            <div class="mt-1 flex items-center text-xs text-gray-500">
                                <i class="fas fa-robot mr-1"></i>
                                <span>Agent: ${status.agent}</span>
                            </div>
                        `;
                    }
                    
                    if (status.timestamp) {
                        logContent += `
                            <div class="mt-1 flex items-center text-xs text-gray-500">
                                <i class="far fa-clock mr-1"></i>
                                <span>${new Date(status.timestamp).toLocaleTimeString()}</span>
                            </div>
                        `;
                    }
                    
                    if (status.output) {
                        logContent += `
                            <div class="mt-2 p-3 bg-gray-50 rounded-md">
                                <pre class="text-xs text-gray-700 whitespace-pre-wrap">${status.output}</pre>
                            </div>
                        `;
                    }
                    
                    logContent += `</div></div>`;
                    logEntry.innerHTML = logContent;
                    logEntries.appendChild(logEntry);
                    logEntries.scrollTop = logEntries.scrollHeight;
                }

                // Update progress bar for different event types
                let progress = 0;
                switch (status.type) {
                    case 'task_started':
                        progress = 33;
                        break;
                    case 'task_completed':
                        progress = 66;
                        break;
                    case 'completed':
                        progress = 100;
                        progressBar.style.width = '100%';
                        progressPercentage.textContent = '100%';
                        // Show results
                        resultDiv.classList.remove('hidden');
                        resultContent.textContent = status.result;
                        showToast('Analysis completed successfully', 'success');
                        stopTimer();
                        socket.close();
                        break;
                    case 'error':
                        statusMessage.classList.add('text-red-600');
                        progressBar.classList.add('bg-red-600');
                        showToast('An error occurred during analysis', 'error');
                        stopTimer();
                        socket.close();
                        break;
                }
                
                if (progress > 0) {
                    progressBar.style.width = `${progress}%`;
                    progressPercentage.textContent = `${progress}%`;
                }
            };

            socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                statusMessage.textContent = 'Connection error occurred';
                statusMessage.classList.add('text-red-600');
                showToast('Connection error occurred', 'error');
                stopTimer();
            };

        } catch (error) {
            console.error('Error:', error);
            statusMessage.textContent = 'Error uploading file: ' + error.message;
            statusMessage.classList.add('text-red-600');
            showToast('Error uploading file', 'error');
            stopTimer();
        }
    });

    // File drag and drop handling
    const dropZone = document.querySelector('.drop-zone');
    const fileInput = document.getElementById('file-upload');

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults (e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        dropZone.classList.add('active');
        dropZone.querySelector('i').classList.remove('fa-cloud-upload-alt');
        dropZone.querySelector('i').classList.add('fa-cloud-download-alt');
    }

    function unhighlight(e) {
        dropZone.classList.remove('active');
        dropZone.querySelector('i').classList.remove('fa-cloud-download-alt');
        dropZone.querySelector('i').classList.add('fa-cloud-upload-alt');
    }

    dropZone.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        fileInput.files = files;
    }
});

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded - Starting script initialization');
    
    const form = document.getElementById('uploadForm');
    const submitBtn = document.getElementById('submit-btn');
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
    const fileInput = document.getElementById('file-upload');
    const selectedFilesDiv = document.getElementById('selected-files');
    const dropZone = document.querySelector('.drop-zone');
    
    let socket;
    let startTime;
    let elapsedTimeInterval;

    if (!form) {
        console.error('Upload form not found!');
        return;
    }
    
    console.log('Form found, attaching event listeners');

    // Handle file selection display
    fileInput.addEventListener('change', () => {
        selectedFilesDiv.innerHTML = '';
        Array.from(fileInput.files).forEach(file => {
            const fileDiv = document.createElement('div');
            fileDiv.className = 'flex items-center justify-between bg-blue-50 p-2 rounded-md mt-2';
            fileDiv.innerHTML = `
                <div class="flex items-center">
                    <i class="fas fa-file-alt text-blue-500 mr-2"></i>
                    <span class="text-sm text-gray-700">${file.name}</span>
                </div>
                <span class="text-xs text-gray-500">${(file.size / 1024 / 1024).toFixed(2)} MB</span>
            `;
            selectedFilesDiv.appendChild(fileDiv);
        });
    });

    // Toast notification function
    function showToast(message, type = 'info') {
        toastMessage.textContent = message;
        toast.className = `toast ${type === 'error' ? 'error' : 'info'} show`;
        setTimeout(() => {
            toast.className = toast.className.replace('show', '');
        }, 3000);
    }

    // Form submission handler
    form.addEventListener('submit', async (e) => {
        console.log('Form submit event triggered');
        e.preventDefault();
        console.log('Default prevented, processing form...');
        
        const startupName = form.elements['startup_name'].value.trim();
        const files = form.elements['files'].files;

        console.log('Startup name:', startupName);
        console.log('Files:', files.length);

        if (!startupName) {
            showToast('Please enter your startup name', 'error');
            return;
        }

        if (files.length === 0) {
            showToast('Please select at least one file to analyze', 'error');
            return;
        }

        // Disable form while processing
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Processing...';

        // Reset UI
        statusDiv.classList.remove('hidden');
        resultDiv.classList.add('hidden');
        downloadButton.classList.add('hidden');
        progressBar.style.width = '0%';
        progressPercentage.textContent = '0%';
        statusMessage.textContent = 'Uploading files...';
        document.getElementById('log-entries').innerHTML = '';
        
        // Start timer
        startTimer();

        // Create FormData with multiple files
        const formData = new FormData();
        formData.append('startup_name', startupName);
        Array.from(files).forEach(file => {
            formData.append('files', file);
        });

        try {
            // Upload files
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                let errorMessage;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.message || 'Upload failed';
                } catch (e) {
                    errorMessage = await response.text() || 'Upload failed';
                }
                throw new Error(errorMessage);
            }

            const data = await response.json();
            console.log('Analysis started:', data);

            // Connect to WebSocket for status updates
            if (socket) {
                socket.close();
            }
            
            socket = new WebSocket(`ws://${window.location.host}${data.websocket_url}`);
            
            socket.onmessage = (event) => {
                try {
                    const status = JSON.parse(event.data);
                    console.log('Status update:', status);
                    
                    const logEntries = document.getElementById('log-entries');
                    
                    if (status.message) {
                        statusMessage.textContent = status.message;
                        
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
                        
                        logContent += '</div></div>';
                        logEntry.innerHTML = logContent;
                        logEntries.appendChild(logEntry);
                        logEntries.scrollTop = logEntries.scrollHeight;
                    }
                    
                    // Update progress bar
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
                } catch (error) {
                    console.error('Error processing message:', error);
                    showToast('Error processing status update', 'error');
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
            statusMessage.textContent = 'Error: ' + error.message;
            statusMessage.classList.add('text-red-600');
            showToast('Error uploading files', 'error');
            stopTimer();
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Start Analysis';
        }
    });

    // Timer functions
    function updateElapsedTime() {
        if (!startTime) return;
        const elapsed = new Date() - startTime;
        const minutes = Math.floor(elapsed / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        elapsedTimeElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    function startTimer() {
        startTime = new Date();
        if (elapsedTimeInterval) clearInterval(elapsedTimeInterval);
        elapsedTimeInterval = setInterval(updateElapsedTime, 1000);
    }

    function stopTimer() {
        if (elapsedTimeInterval) {
            clearInterval(elapsedTimeInterval);
            elapsedTimeInterval = null;
        }
    }

    // File drag and drop handling
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

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
        fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
});

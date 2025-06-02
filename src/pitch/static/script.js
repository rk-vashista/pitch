document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('uploadForm');
    const statusDiv = document.getElementById('status');
    const statusMessage = document.getElementById('status-message');
    const progressBar = document.getElementById('progress-bar');
    const resultDiv = document.getElementById('result');
    const resultContent = document.getElementById('result-content');
    const downloadButton = document.getElementById('download-report');
    let socket;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Reset UI
        statusDiv.classList.remove('hidden');
        resultDiv.classList.add('hidden');
        progressBar.style.width = '0%';
        statusMessage.textContent = 'Starting upload...';

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

                // Add log entry
                if (status.message) {
                    const logEntry = document.createElement('div');
                    logEntry.className = 'p-2 border-l-4 border-blue-500 bg-blue-50';
                    
                    let logContent = `<p class="text-sm text-gray-800">${status.message}</p>`;
                    if (status.agent) {
                        logContent += `<p class="text-xs text-gray-600">Agent: ${status.agent}</p>`;
                    }
                    if (status.timestamp) {
                        logContent += `<p class="text-xs text-gray-500">${new Date(status.timestamp).toLocaleTimeString()}</p>`;
                    }
                    if (status.output) {
                        logContent += `<pre class="mt-2 text-xs bg-gray-100 p-2 rounded">${status.output}</pre>`;
                    }
                    
                    logEntry.innerHTML = logContent;
                    logEntries.appendChild(logEntry);
                    logEntries.scrollTop = logEntries.scrollHeight;
                }

                // Update progress bar for different event types
                switch (status.type) {
                    case 'task_started':
                        progressBar.style.width = '33%';
                        break;
                    case 'task_completed':
                        progressBar.style.width = '66%';
                        break;
                    case 'completed':
                        progressBar.style.width = '100%';
                        // Show results
                        resultDiv.classList.remove('hidden');
                        resultContent.textContent = status.result;
                        socket.close();
                        break;
                    case 'error':
                        statusMessage.classList.add('text-red-600');
                        progressBar.classList.add('bg-red-600');
                        socket.close();
                        break;
                }
            };

            socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                statusMessage.textContent = 'Connection error occurred';
                statusMessage.classList.add('text-red-600');
            };

        } catch (error) {
            console.error('Error:', error);
            statusMessage.textContent = 'Error uploading file: ' + error.message;
            statusMessage.classList.add('text-red-600');
        }
    });

    // File drag and drop handling
    const dropZone = document.querySelector('.border-dashed');
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
        dropZone.classList.add('border-blue-500');
    }

    function unhighlight(e) {
        dropZone.classList.remove('border-blue-500');
    }

    dropZone.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        fileInput.files = files;
    }
});

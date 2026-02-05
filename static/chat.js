/**
 * ChatGPT-Style Interface for Analytics Assistant
 * Modern conversational UI with message bubbles
 */

// Global state
let sessionId = null;
let currentChart = null;
let uploadedDataset = null;
let uploadedSessionId = null;
let currentPage = 1;
let rowsPerPage = 100;
let activeDataset = 'superstore'; // Default dataset
let availableDatasets = [];

// API Configuration
const API_BASE = window.location.origin;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Initializing Chat Interface...');
    
    await loadDatasets();
    await loadSuggestions();
    setupEventListeners();
    await checkHealth();
    
    console.log('✓ Chat ready');
});

/**
 * Load available datasets
 */
async function loadDatasets() {
    try {
        const response = await fetch(`${API_BASE}/datasets`);
        const data = await response.json();
        availableDatasets = data.datasets || [];
        
        const container = document.getElementById('datasetList');
        container.innerHTML = '';
        
        availableDatasets.forEach(dataset => {
            const button = document.createElement('button');
            button.className = `w-full text-left px-3 py-2 text-xs rounded transition flex items-center space-x-2 ${
                activeDataset === dataset.table_name ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'
            }`;
            button.innerHTML = `
                <span class="text-base">${dataset.icon}</span>
                <div class="flex-1">
                    <div class="font-medium">${dataset.name}</div>
                    <div class="text-[10px] opacity-75">${dataset.row_count.toLocaleString()} rows</div>
                </div>
            `;
            button.onclick = () => switchDataset(dataset.table_name);
            container.appendChild(button);
        });
        
    } catch (error) {
        console.error('Failed to load datasets:', error);
    }
}

/**
 * Switch active dataset
 */
async function switchDataset(datasetName) {
    if (activeDataset === datasetName) return;
    
    activeDataset = datasetName;
    uploadedSessionId = null; // Clear uploaded CSV when switching
    
    // Update UI
    await loadDatasets();
    await loadSuggestions();
    
    // Show View Dataset button for pre-loaded datasets
    const viewBtn = document.getElementById('viewDatasetBtn');
    const statusDiv = document.getElementById('uploadStatus');
    viewBtn.classList.remove('hidden');
    statusDiv.classList.add('hidden');
    
    // Add system message
    const datasetInfo = availableDatasets.find(d => d.table_name === datasetName);
    if (datasetInfo) {
        const container = document.getElementById('messagesContainer');
        const msgDiv = document.createElement('div');
        msgDiv.className = 'flex justify-center animate-fadeIn';
        msgDiv.innerHTML = `
            <div class="bg-blue-50 border border-blue-200 rounded-full px-4 py-2">
                <p class="text-xs text-blue-800">📊 Switched to <strong>${datasetInfo.name}</strong> dataset</p>
            </div>
        `;
        container.appendChild(msgDiv);
        updateChatLayout();
        scrollToBottom();
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    document.getElementById('chatForm').addEventListener('submit', handleChatSubmit);
}

/**
 * Handle chat form submission
 */
async function handleChatSubmit(e) {
    e.preventDefault();
    
    const input = document.getElementById('messageInput');
    const question = input.value.trim();
    
    if (!question) return;
    
    // Clear input and disable send button
    input.value = '';
    input.style.height = 'auto';
    toggleSendButton(false);
    
    // Add user message to chat
    addUserMessage(question);
    
    // Show typing indicator
    const typingId = showTypingIndicator();
    
    try {
        // Prepare request
        const requestBody = {
            question: question,
            use_uploaded_data: uploadedSessionId !== null,
            dataset: uploadedSessionId ? 'dataset' : activeDataset
        };
        
        // Use uploaded dataset session ID if available, otherwise use chat session ID
        if (uploadedSessionId) {
            requestBody.session_id = uploadedSessionId;
        } else if (sessionId) {
            requestBody.session_id = sessionId;
        }
        
        // Call API
        const response = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        
        const result = await response.json();
        
        // Remove typing indicator
        removeTypingIndicator(typingId);
        
        if (result.success) {
            // Store session ID
            if (result.data.session_id && !uploadedSessionId) {
                sessionId = result.data.session_id;
            }
            
            // Add assistant response
            await addAssistantMessage(result.data);
        } else {
            // Show error message with suggestions if available
            const suggestions = result.error?.suggestions || null;
            const errorMsg = result.error?.message || 'An error occurred';
            const errorDetails = result.error?.details || result.error?.code || '';
            console.error('Query failed:', errorMsg, errorDetails);
            addErrorMessage(errorMsg, suggestions);
        }
        
    } catch (error) {
        console.error('Query error:', error);
        removeTypingIndicator(typingId);
        addErrorMessage('Sorry, something went wrong. Please try again.');
    }
    
    // Re-enable send button
    toggleSendButton(true);
    
    // Update layout
    updateChatLayout();
    
    // Scroll to bottom
    scrollToBottom();
}

/**
 * Update chat layout based on message count
 */
function updateChatLayout() {
    const container = document.getElementById('chatContainer');
    const messagesContainer = document.getElementById('messagesContainer');
    const messageCount = messagesContainer.children.length;
    
    // Switch to bottom layout if we have any messages
    if (messageCount > 0) {
        container.classList.remove('centered');
        container.classList.add('bottom');
    } else {
        container.classList.remove('bottom');
        container.classList.add('centered');
    }
}

/**
 * Add user message bubble
 */
function addUserMessage(text) {
    const container = document.getElementById('messagesContainer');
    const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex items-start space-x-3 justify-end animate-fadeIn';
    messageDiv.innerHTML = `
        <div class="flex-1 flex flex-col items-end">
            <div class="bg-blue-600 text-white rounded-2xl rounded-tr-none px-4 py-3 max-w-2xl">
                <p class="text-sm">${escapeHtml(text)}</p>
            </div>
            <p class="text-xs text-gray-400 mt-1 mr-1">${time}</p>
        </div>
        <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
            <span class="text-white text-sm">👤</span>
        </div>
    `;
    
    container.appendChild(messageDiv);
    updateChatLayout();
    scrollToBottom();
}

/**
 * Add assistant message bubble with full analysis
 */
async function addAssistantMessage(data) {
    const container = document.getElementById('messagesContainer');
    const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex items-start space-x-3 animate-fadeIn';
    messageDiv.innerHTML = `
        <div class="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0">
            <span class="text-white text-sm">🤖</span>
        </div>
        <div class="flex-1">
            <div class="bg-gray-100 rounded-2xl rounded-tl-none px-4 py-4 max-w-3xl">
                
                <!-- Summary -->
                <div class="mb-3">
                    <p id="summary-${Date.now()}" class="text-sm text-gray-800 leading-relaxed"></p>
                </div>
                
                <!-- Insights -->
                <div id="insights-${Date.now()}" class="space-y-2 mb-3"></div>
                
                <!-- Chart -->
                ${data.chart && data.chart.chart_type !== 'table' ? `
                <div class="bg-white rounded-lg p-4 my-3">
                    <div style="position: relative; height: 400px; width: 100%;">
                        <canvas id="chart-${Date.now()}"></canvas>
                    </div>
                </div>
                ` : ''}
                
                <!-- Data Preview -->
                ${data.data && data.data.length > 0 ? `
                <div class="bg-white rounded-lg overflow-hidden my-3">
                    <div class="bg-gray-50 px-3 py-2 border-b border-gray-200">
                        <p class="text-xs font-medium text-gray-700">📊 Data (${data.metadata.row_count} rows)</p>
                    </div>
                    <div class="overflow-x-auto max-h-64">
                        <table id="data-table-${Date.now()}" class="min-w-full text-xs"></table>
                    </div>
                </div>
                ` : ''}
                
                <!-- SQL Query -->
                <details class="mt-3">
                    <summary class="cursor-pointer text-xs text-gray-500 hover:text-gray-700 select-none">
                        🔍 View SQL Query
                    </summary>
                    <div class="mt-2 bg-gray-800 rounded p-3">
                        <pre class="text-xs text-green-400 font-mono overflow-x-auto">${escapeHtml(data.sql)}</pre>
                        <p class="text-xs text-gray-400 mt-2">Generated by ${data.sql_source}</p>
                    </div>
                </details>
                
            </div>
            <p class="text-xs text-gray-400 mt-1 ml-1">${time}</p>
        </div>
    `;
    
    container.appendChild(messageDiv);
    
    // Animate summary text
    const summaryId = messageDiv.querySelector('[id^="summary-"]').id;
    await typewriterEffect(document.getElementById(summaryId), data.summary, 8);
    
    // Add insights one by one
    const insightsId = messageDiv.querySelector('[id^="insights-"]').id;
    const insightsContainer = document.getElementById(insightsId);
    if (data.insights && data.insights.length > 0) {
        for (let i = 0; i < data.insights.length; i++) {
            await new Promise(resolve => setTimeout(resolve, 150));
            const insightDiv = document.createElement('div');
            insightDiv.className = 'flex items-start text-xs text-gray-700 animate-fadeIn';
            insightDiv.innerHTML = `
                <svg class="w-3 h-3 text-blue-500 mt-0.5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span>${escapeHtml(data.insights[i])}</span>
            `;
            insightsContainer.appendChild(insightDiv);
        }
    }
    
    // Render chart (with slight delay to ensure DOM is ready)
    if (data.chart && data.chart.chart_type !== 'table') {
        console.log('Chart data received:', data.chart);
        const canvasElement = messageDiv.querySelector('[id^="chart-"]');
        if (canvasElement) {
            const canvasId = canvasElement.id;
            console.log('Creating chart with ID:', canvasId);
            setTimeout(() => {
                createChart(canvasId, data.chart, data.data);
            }, 100);
        } else {
            console.warn('Canvas element not found for chart rendering');
        }
    } else {
        console.log('No chart data or chart type is table:', data.chart);
    }
    
    // Render data table
    if (data.data && data.data.length > 0) {
        const tableId = messageDiv.querySelector('[id^="data-table-"]').id;
        renderDataTable(document.getElementById(tableId), data.data.slice(0, 10));
    }
    
    updateChatLayout();
    scrollToBottom();
}

/**
 * Add error message with optional suggestions
 */
function addErrorMessage(message, suggestions = null) {
    const container = document.getElementById('messagesContainer');
    const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    
    let suggestionsHtml = '';
    if (suggestions && suggestions.length > 0) {
        suggestionsHtml = `
            <div class="mt-3 space-y-2">
                <p class="text-xs font-semibold text-gray-700">Try asking:</p>
                ${suggestions.map(s => `
                    <button onclick="askSuggestion('${escapeHtml(s).replace(/'/g, "\\'")}')" 
                            class="block w-full text-left px-3 py-2 text-xs bg-white border border-gray-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition">
                        ${escapeHtml(s)}
                    </button>
                `).join('')}
            </div>
        `;
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex items-start space-x-3 animate-fadeIn';
    messageDiv.innerHTML = `
        <div class="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0">
            <span class="text-white text-sm">🤖</span>
        </div>
        <div class="flex-1">
            <div class="bg-blue-50 border border-blue-200 rounded-2xl rounded-tl-none px-4 py-3 max-w-2xl">
                <p class="text-sm text-blue-900">${escapeHtml(message)}</p>
                ${suggestionsHtml}
            </div>
            <p class="text-xs text-gray-400 mt-1 ml-1">${time}</p>
        </div>
    `;
    
    container.appendChild(messageDiv);
    updateChatLayout();
    scrollToBottom();
}

/**
 * Ask a suggested question
 */
function askSuggestion(question) {
    document.getElementById('messageInput').value = question;
    document.getElementById('chatForm').dispatchEvent(new Event('submit'));
}

/**
 * Show typing indicator
 */
function showTypingIndicator() {
    const container = document.getElementById('messagesContainer');
    const id = `typing-${Date.now()}`;
    
    const typingDiv = document.createElement('div');
    typingDiv.id = id;
    typingDiv.className = 'flex items-start space-x-3 animate-fadeIn';
    typingDiv.innerHTML = `
        <div class="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0">
            <span class="text-white text-sm">🤖</span>
        </div>
        <div class="bg-gray-100 rounded-2xl rounded-tl-none px-4 py-3">
            <div class="typing-indicator flex space-x-1">
                <span class="w-2 h-2 bg-gray-500 rounded-full"></span>
                <span class="w-2 h-2 bg-gray-500 rounded-full"></span>
                <span class="w-2 h-2 bg-gray-500 rounded-full"></span>
            </div>
        </div>
    `;
    
    container.appendChild(typingDiv);
    scrollToBottom();
    
    return id;
}

/**
 * Remove typing indicator
 */
function removeTypingIndicator(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
    }
}

/**
 * Typewriter effect
 */
function typewriterEffect(element, text, speed = 15) {
    element.textContent = '';
    let i = 0;
    
    return new Promise((resolve) => {
        const timer = setInterval(() => {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i++;
                scrollToBottom();
            } else {
                clearInterval(timer);
                resolve();
            }
        }, speed);
    });
}

/**
 * Create chart
 */
function createChart(canvasId, config, data) {
    console.log('createChart called with:', canvasId, config, data);
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error('Canvas element not found:', canvasId);
        return;
    }
    
    console.log('Canvas found, creating chart type:', config.chart_type);
    const ctx = canvas.getContext('2d');
    
    try {
        if (config.chart_type === 'bar') {
            createBarChart(ctx, config, data);
        } else if (config.chart_type === 'line') {
            createLineChart(ctx, config, data);
        } else if (config.chart_type === 'pie') {
            createPieChart(ctx, config, data);
        }
        console.log('Chart created successfully');
    } catch (error) {
        console.error('Error creating chart:', error);
    }
}

function createBarChart(ctx, config, data) {
    const labels = data.map(row => row[config.x_axis] || 'Unknown');
    const values = data.map(row => parseFloat(row[config.y_axis]) || 0);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: config.y_axis,
                data: values,
                backgroundColor: 'rgba(37, 99, 235, 0.7)',
                borderColor: 'rgba(37, 99, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    display: false 
                },
                title: {
                    display: true,
                    text: config.y_axis,
                    font: {
                        size: 14,
                        weight: 'bold'
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45,
                        font: {
                            size: 10
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            if (value >= 1000000) return '$' + (value / 1000000).toFixed(1) + 'M';
                            if (value >= 1000) return '$' + (value / 1000).toFixed(1) + 'K';
                            return '$' + value.toFixed(0);
                        }
                    }
                }
            }
        }
    });
}

function createLineChart(ctx, config, data) {
    const labels = data.map(row => row[config.x_axis] || 'Unknown');
    const values = data.map(row => parseFloat(row[config.y_axis]) || 0);
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: config.y_axis,
                data: values,
                borderColor: 'rgba(37, 99, 235, 1)',
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function createPieChart(ctx, config, data) {
    const labels = data.map(row => row[config.x_axis] || 'Unknown');
    const values = data.map(row => parseFloat(row[config.y_axis]) || 0);
    
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    'rgba(37, 99, 235, 0.8)',
                    'rgba(99, 102, 241, 0.8)',
                    'rgba(139, 92, 246, 0.8)',
                    'rgba(168, 85, 247, 0.8)',
                    'rgba(192, 132, 252, 0.8)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

/**
 * Render data table
 */
function renderDataTable(table, data) {
    if (!data || data.length === 0) return;
    
    // Headers
    const thead = document.createElement('thead');
    thead.className = 'bg-gray-50';
    const headerRow = document.createElement('tr');
    Object.keys(data[0]).forEach(key => {
        const th = document.createElement('th');
        th.className = 'px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase';
        th.textContent = key;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // Body
    const tbody = document.createElement('tbody');
    tbody.className = 'divide-y divide-gray-200';
    data.forEach((row, idx) => {
        const tr = document.createElement('tr');
        tr.className = idx % 2 === 0 ? 'bg-white' : 'bg-gray-50';
        Object.values(row).forEach(value => {
            const td = document.createElement('td');
            td.className = 'px-3 py-2 text-xs text-gray-900 whitespace-nowrap';
            td.textContent = formatValue(value);
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
}

/**
 * Load suggested questions
 */
async function loadSuggestions() {
    try {
        const dataset = uploadedSessionId ? 'dataset' : activeDataset;
        const response = await fetch(`${API_BASE}/suggestions?dataset=${dataset}`);
        const data = await response.json();
        
        const container = document.getElementById('suggestedQuestions');
        container.innerHTML = '';
        
        // Show only first 6 suggestions
        const allSuggestions = [...data.trending, ...data.suggested].slice(0, 6);
        
        allSuggestions.forEach(q => {
            const button = document.createElement('button');
            button.className = 'w-full text-left px-3 py-2 text-xs text-gray-300 hover:bg-gray-700 rounded transition';
            button.textContent = q;
            button.onclick = () => {
                document.getElementById('messageInput').value = q;
                document.getElementById('messageInput').focus();
            };
            container.appendChild(button);
        });
        
    } catch (error) {
        console.error('Failed to load suggestions:', error);
    }
}

/**
 * Check health
 */
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        
        console.log('Health check response:', data);
        
        const indicator = document.getElementById('statusIndicator');
        if (!indicator) {
            console.error('Status indicator element not found');
            return;
        }
        
        // Show connected if system is ready (even if database is degraded, since we support CSV uploads)
        if (data.status === 'healthy' || data.status === 'degraded') {
            indicator.innerHTML = '<span class="h-2 w-2 rounded-full bg-green-400 animate-pulse mr-2"></span>Connected';
            console.log('Status set to Connected');
        } else {
            indicator.innerHTML = '<span class="h-2 w-2 rounded-full bg-red-400 mr-2"></span>Disconnected';
            console.log('Status set to Disconnected');
        }
    } catch (error) {
        console.error('Health check failed:', error);
        const indicator = document.getElementById('statusIndicator');
        if (indicator) {
            indicator.innerHTML = '<span class="h-2 w-2 rounded-full bg-red-400 mr-2"></span>Disconnected';
        }
    }
}

/**
 * Handle Enter key (send on Enter, new line on Shift+Enter)
 */
function handleEnterKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        document.getElementById('chatForm').dispatchEvent(new Event('submit'));
    }
}

/**
 * Auto-resize textarea
 */
function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    
    // Enable/disable send button based on content
    const button = document.getElementById('sendButton');
    const hasContent = textarea.value.trim().length > 0;
    button.disabled = !hasContent;
}

/**
 * Toggle send button
 */
function toggleSendButton(enabled) {
    const button = document.getElementById('sendButton');
    const input = document.getElementById('messageInput');
    const hasContent = input.value.trim().length > 0;
    button.disabled = !(enabled && hasContent);
}

/**
 * Scroll to bottom
 */
function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    setTimeout(() => {
        container.scrollTop = container.scrollHeight;
    }, 100);
}

/**
 * File upload
 */
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const statusDiv = document.getElementById('uploadStatus');
    const viewBtn = document.getElementById('viewDatasetBtn');
    
    statusDiv.className = 'text-xs text-blue-600';
    statusDiv.textContent = '📤 Uploading...';
    statusDiv.classList.remove('hidden');
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE}/upload-csv`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        const result = await response.json();
        uploadedSessionId = result.session_id;
        
        // Read locally for preview
        const text = await file.text();
        const rows = parseCSV(text);
        
        uploadedDataset = {
            filename: file.name,
            rows: rows,
            rowCount: rows.length - 1,
            columns: rows[0]
        };
        
        currentPage = 1;
        
        statusDiv.className = 'text-xs text-green-600';
        statusDiv.textContent = `✅ ${file.name} (${uploadedDataset.rowCount.toLocaleString()} rows)`;
        viewBtn.classList.remove('hidden');
        
        // Add system message
        const container = document.getElementById('messagesContainer');
        const msgDiv = document.createElement('div');
        msgDiv.className = 'flex justify-center animate-fadeIn';
        msgDiv.innerHTML = `
            <div class="bg-green-50 border border-green-200 rounded-full px-4 py-2">
                <p class="text-xs text-green-800">✅ Dataset uploaded: <strong>${file.name}</strong> (${uploadedDataset.rowCount.toLocaleString()} rows)</p>
            </div>
        `;
        container.appendChild(msgDiv);
        updateChatLayout();
        scrollToBottom();
        
    } catch (error) {
        console.error('Upload error:', error);
        statusDiv.className = 'text-xs text-red-600';
        statusDiv.textContent = `❌ ${error.message}`;
        viewBtn.classList.add('hidden');
        uploadedSessionId = null;
    }
}

// CSV parsing
function parseCSV(text) {
    const lines = text.split('\n').filter(line => line.trim());
    return lines.map(line => {
        const values = [];
        let currentValue = '';
        let insideQuotes = false;
        
        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') {
                insideQuotes = !insideQuotes;
            } else if (char === ',' && !insideQuotes) {
                values.push(currentValue.trim());
                currentValue = '';
            } else {
                currentValue += char;
            }
        }
        values.push(currentValue.trim());
        return values;
    });
}

// Dataset modal functions
async function toggleDatasetView() {
    const modal = document.getElementById('datasetModal');
    if (modal.classList.contains('hidden')) {
        // Load data from backend if viewing a pre-loaded dataset
        if (!uploadedDataset && activeDataset) {
            await loadDatasetPreview();
        }
        
        if (!uploadedDataset) return; // Still no data after trying to load
        
        currentPage = 1;
        modal.classList.remove('hidden');
        
        // Adjust modal position based on sidebar state
        const sidebar = document.getElementById('sidebar');
        const modalContent = document.getElementById('datasetModalContent');
        if (sidebar && !sidebar.classList.contains('collapsed')) {
            // Sidebar is visible - shift modal content to account for 260px sidebar
            modalContent.style.marginLeft = '130px'; // Half of sidebar width for better centering
            modalContent.style.marginRight = '0';
        } else {
            // Sidebar is collapsed - center normally
            modalContent.style.marginLeft = 'auto';
            modalContent.style.marginRight = 'auto';
        }
        
        displayDatasetTable();
    } else {
        modal.classList.add('hidden');
    }
}

/**
 * Load dataset preview from backend
 */
async function loadDatasetPreview() {
    try {
        const response = await fetch(`${API_BASE}/dataset/${activeDataset}/preview?limit=1000`);
        if (!response.ok) throw new Error('Failed to load dataset');
        
        const data = await response.json();
        
        // Convert to the same format as uploaded CSV
        const columns = data.columns;
        const rows = [columns, ...data.rows];
        
        uploadedDataset = {
            filename: activeDataset,
            rows: rows,
            rowCount: data.total_rows,
            columns: columns
        };
        
    } catch (error) {
        console.error('Error loading dataset preview:', error);
        alert('Failed to load dataset preview. Please try again.');
    }
}

function displayDatasetTable() {
    if (!uploadedDataset) return;
    
    document.getElementById('datasetInfo').innerHTML = `
        <strong>File:</strong> ${uploadedDataset.filename} | 
        <strong>Total Rows:</strong> ${uploadedDataset.rowCount.toLocaleString()} | 
        <strong>Columns:</strong> ${uploadedDataset.columns.length}
    `;
    
    const thead = document.getElementById('datasetTableHead');
    const tbody = document.getElementById('datasetTableBody');
    
    const headerRow = document.createElement('tr');
    uploadedDataset.columns.forEach(col => {
        const th = document.createElement('th');
        th.className = 'px-6 py-3 text-left text-xs font-medium text-blue-800 uppercase tracking-wider bg-gradient-to-r from-blue-50 to-blue-100';
        th.textContent = col;
        headerRow.appendChild(th);
    });
    thead.innerHTML = '';
    thead.appendChild(headerRow);
    
    const totalPages = Math.ceil(uploadedDataset.rowCount / rowsPerPage);
    const startRow = (currentPage - 1) * rowsPerPage + 1;
    const endRow = Math.min(currentPage * rowsPerPage, uploadedDataset.rowCount);
    
    document.getElementById('rowRangeStart').textContent = startRow.toLocaleString();
    document.getElementById('rowRangeEnd').textContent = endRow.toLocaleString();
    document.getElementById('totalRows').textContent = uploadedDataset.rowCount.toLocaleString();
    
    renderPaginationButtons(totalPages);
    
    tbody.innerHTML = '';
    for (let i = startRow; i <= endRow; i++) {
        const row = uploadedDataset.rows[i];
        const tr = document.createElement('tr');
        tr.className = i % 2 === 0 ? 'bg-gray-50' : 'bg-white';
        
        row.forEach(cell => {
            const td = document.createElement('td');
            td.className = 'px-6 py-4 whitespace-nowrap text-sm text-gray-900';
            td.textContent = cell;
            tr.appendChild(td);
        });
        
        tbody.appendChild(tr);
    }
}

function renderPaginationButtons(totalPages) {
    const container = document.getElementById('paginationButtons');
    container.innerHTML = '';
    
    const createButton = (text, page, isActive = false, isDisabled = false) => {
        const btn = document.createElement('button');
        btn.textContent = text;
        btn.onclick = () => !isDisabled && goToPage(page);
        
        if (isActive) {
            btn.className = 'px-3 py-1 text-sm font-medium text-white bg-blue-600 rounded';
        } else if (isDisabled) {
            btn.className = 'px-3 py-1 text-sm text-gray-400 cursor-not-allowed';
        } else {
            btn.className = 'px-3 py-1 text-sm text-gray-700 bg-white border border-gray-300 rounded hover:bg-blue-50';
        }
        
        return btn;
    };
    
    container.appendChild(createButton('«', 1, false, currentPage === 1));
    
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, currentPage + 2);
    
    if (startPage > 1) {
        container.appendChild(createButton('1', 1));
        if (startPage > 2) {
            const ellipsis = document.createElement('span');
            ellipsis.textContent = '...';
            ellipsis.className = 'px-2 text-gray-500';
            container.appendChild(ellipsis);
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        container.appendChild(createButton(i.toString(), i, i === currentPage));
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            const ellipsis = document.createElement('span');
            ellipsis.textContent = '...';
            ellipsis.className = 'px-2 text-gray-500';
            container.appendChild(ellipsis);
        }
        container.appendChild(createButton(totalPages.toString(), totalPages));
    }
    
    container.appendChild(createButton('»', totalPages, false, currentPage === totalPages));
}

function goToPage(page) {
    if (!uploadedDataset) return;
    const totalPages = Math.ceil(uploadedDataset.rowCount / rowsPerPage);
    if (page >= 1 && page <= totalPages) {
        currentPage = page;
        displayDatasetTable();
    }
}

function changeRowsPerPage() {
    rowsPerPage = parseInt(document.getElementById('rowsPerPageSelect').value);
    currentPage = 1;
    displayDatasetTable();
}

// Utility functions
function formatValue(value) {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'number') {
        if (value >= 100) return value.toLocaleString('en-US', { maximumFractionDigits: 2 });
        return value.toFixed(2);
    }
    return String(value);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    const toggleBtn = document.getElementById('sidebarToggle');
    
    sidebar.classList.toggle('collapsed');
    mainContent.classList.toggle('expanded');
    toggleBtn.classList.toggle('collapsed');
}

// Make modal draggable
let isDragging = false;
let currentX;
let currentY;
let initialX;
let initialY;
let xOffset = 0;
let yOffset = 0;

document.addEventListener('DOMContentLoaded', () => {
    const modalHeader = document.getElementById('modalHeader');
    const modalContent = document.getElementById('datasetModalContent');
    
    if (modalHeader && modalContent) {
        modalHeader.addEventListener('mousedown', dragStart);
        document.addEventListener('mousemove', drag);
        document.addEventListener('mouseup', dragEnd);
    }
});

function dragStart(e) {
    if (e.target.closest('button')) return; // Don't drag when clicking close button
    
    const modalContent = document.getElementById('datasetModalContent');
    initialX = e.clientX - xOffset;
    initialY = e.clientY - yOffset;
    
    if (e.target === document.getElementById('modalHeader') || e.target.closest('#modalHeader')) {
        isDragging = true;
    }
}

function drag(e) {
    if (isDragging) {
        e.preventDefault();
        currentX = e.clientX - initialX;
        currentY = e.clientY - initialY;
        
        xOffset = currentX;
        yOffset = currentY;
        
        const modalContent = document.getElementById('datasetModalContent');
        modalContent.style.transform = `translate(${currentX}px, ${currentY}px)`;
    }
}

function dragEnd(e) {
    initialX = currentX;
    initialY = currentY;
    isDragging = false;
}

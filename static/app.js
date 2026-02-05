/**
 * Frontend JavaScript for Conversational Analytics System
 * Vanilla JavaScript + Chart.js
 */

// Global state
let sessionId = null;
let currentChart = null;

// API Configuration
const API_BASE = window.location.origin;

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Initializing Analytics Assistant...');
    
    // Load suggested questions
    await loadSuggestions();
    
    // Setup event listeners
    setupEventListeners();
    
    // Check system health
    await checkHealth();
    
    console.log('✓ Application ready');
});

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Query form submission
    document.getElementById('queryForm').addEventListener('submit', handleQuerySubmit);
    
    // SQL toggle
    document.getElementById('sqlToggle').addEventListener('click', toggleSQL);
}

/**
 * Handle query submission
 */
async function handleQuerySubmit(e) {
    e.preventDefault();
    
    const input = document.getElementById('questionInput');
    const question = input.value.trim();
    
    if (!question) {
        return;
    }
    
    // Show loading, hide previous results/errors
    showLoading();
    hideResults();
    hideError();
    hideWelcome();
    
    try {
        const response = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question,
                session_id: sessionId
            })
        });
        
        const result = await response.json();
        
        hideLoading();
        
        if (result.success) {
            // Store session ID
            sessionId = result.data.session_id;
            
            // Update context indicator
            updateContextIndicator(result.data.used_context);
            
            // Display results
            displayResults(result.data);
            
            // Update recent questions
            updateRecentQuestions();
            
        } else {
            displayError(result.error);
        }
        
    } catch (error) {
        hideLoading();
        displayError({
            message: 'Network error. Please check your connection and try again.',
            suggestions: []
        });
        console.error('Query error:', error);
    }
}

/**
 * Display query results
 */
function displayResults(data) {
    // Show results section
    document.getElementById('resultsSection').classList.remove('hidden');
    
    // Display summary and insights
    displaySummary(data.summary, data.insights, data.confidence);
    
    // Display visualization
    displayChart(data.chart, data.data);
    
    // Display data table
    displayTable(data.data, data.metadata);
    
    // Display SQL
    displaySQL(data.sql, data.sql_source);
    
    // Scroll to results
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Typewriter effect for text
 */
function typewriterEffect(element, text, speed = 15) {
    element.textContent = '';
    let i = 0;
    
    return new Promise((resolve) => {
        const timer = setInterval(() => {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i++;
            } else {
                clearInterval(timer);
                resolve();
            }
        }, speed);
    });
}

/**
 * Display summary and insights
 */
async function displaySummary(summary, insights, confidence) {
    // Summary text with typewriter effect
    const summaryElement = document.getElementById('summaryText');
    await typewriterEffect(summaryElement, summary, 8);
    
    // Confidence badge
    const badge = document.getElementById('confidenceBadge');
    if (confidence === 'high') {
        badge.className = 'px-3 py-1 text-sm rounded-full bg-green-100 text-green-800';
        badge.textContent = '✓ High Confidence';
    } else if (confidence === 'medium') {
        badge.className = 'px-3 py-1 text-sm rounded-full bg-yellow-100 text-yellow-800';
        badge.textContent = '⚠ Medium Confidence';
    } else {
        badge.className = 'px-3 py-1 text-sm rounded-full bg-gray-100 text-gray-800';
        badge.textContent = 'ℹ Low Confidence';
    }
    
    // Insights
    const container = document.getElementById('insightsContainer');
    container.innerHTML = '';
    
    if (insights && insights.length > 0) {
        const title = document.createElement('h4');
        title.className = 'text-sm font-semibold text-gray-700 mb-2 mt-4';
        title.textContent = 'Key Insights:';
        container.appendChild(title);
        
        // Add insights one by one with delay
        for (let i = 0; i < insights.length; i++) {
            await new Promise(resolve => setTimeout(resolve, 150));
            
            const div = document.createElement('div');
            div.className = 'flex items-start text-sm text-gray-600 animate-fadeIn';
            div.innerHTML = `
                <svg class="w-4 h-4 text-blue-500 mt-0.5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span>${escapeHtml(insights[i])}</span>
            `;
            container.appendChild(div);
        }
    }
}

/**
 * Display chart visualization
 */
function displayChart(chartConfig, data) {
    const canvas = document.getElementById('resultChart');
    const section = document.getElementById('chartSection');
    
    // Destroy previous chart
    if (currentChart) {
        currentChart.destroy();
        currentChart = null;
    }
    
    // Hide if no data or table-only
    if (!data || data.length === 0 || chartConfig.chart_type === 'table') {
        section.classList.add('hidden');
        return;
    }
    
    section.classList.remove('hidden');
    
    const ctx = canvas.getContext('2d');
    
    try {
        if (chartConfig.chart_type === 'bar') {
            currentChart = createBarChart(ctx, chartConfig, data);
        } else if (chartConfig.chart_type === 'line') {
            currentChart = createLineChart(ctx, chartConfig, data);
        } else if (chartConfig.chart_type === 'pie') {
            currentChart = createPieChart(ctx, chartConfig, data);
        } else {
            section.classList.add('hidden');
        }
    } catch (error) {
        console.error('Chart creation error:', error);
        section.classList.add('hidden');
    }
}

/**
 * Create bar chart
 */
function createBarChart(ctx, config, data) {
    const labels = data.map(row => row[config.x_axis] || 'Unknown');
    const values = data.map(row => parseFloat(row[config.y_axis]) || 0);
    
    return new Chart(ctx, {
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
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatNumber(value);
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create line chart
 */
function createLineChart(ctx, config, data) {
    const labels = data.map(row => row[config.x_axis] || 'Unknown');
    const values = data.map(row => parseFloat(row[config.y_axis]) || 0);
    
    return new Chart(ctx, {
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
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatNumber(value);
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create pie chart
 */
function createPieChart(ctx, config, data) {
    const labels = data.map(row => row[config.x_axis] || 'Unknown');
    const values = data.map(row => parseFloat(row[config.y_axis]) || 0);
    
    const colors = [
        'rgba(37, 99, 235, 0.8)',
        'rgba(16, 185, 129, 0.8)',
        'rgba(245, 158, 11, 0.8)',
        'rgba(239, 68, 68, 0.8)',
        'rgba(139, 92, 246, 0.8)',
        'rgba(236, 72, 153, 0.8)'
    ];
    
    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderColor: 'white',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

/**
 * Display data table
 */
function displayTable(data, metadata) {
    const tableHead = document.getElementById('tableHead');
    const tableBody = document.getElementById('tableBody');
    const rowCount = document.getElementById('rowCount');
    
    // Clear previous content
    tableHead.innerHTML = '';
    tableBody.innerHTML = '';
    
    if (!data || data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="100" class="px-6 py-4 text-center text-gray-500">No data available</td></tr>';
        rowCount.textContent = '0 rows';
        return;
    }
    
    // Create header
    const headers = Object.keys(data[0]);
    const headerRow = document.createElement('tr');
    headers.forEach(header => {
        const th = document.createElement('th');
        th.className = 'px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider';
        th.textContent = header;
        headerRow.appendChild(th);
    });
    tableHead.appendChild(headerRow);
    
    // Create rows (limit to first 100 for display)
    const displayData = data.slice(0, 100);
    displayData.forEach(row => {
        const tr = document.createElement('tr');
        headers.forEach(header => {
            const td = document.createElement('td');
            td.className = 'px-6 py-4 whitespace-nowrap text-sm text-gray-900';
            const value = row[header];
            td.textContent = formatValue(value);
            tr.appendChild(td);
        });
        tableBody.appendChild(tr);
    });
    
    // Update row count
    const countText = `${data.length} row${data.length !== 1 ? 's' : ''}`;
    const limitedText = displayData.length < data.length ? ` (showing first ${displayData.length})` : '';
    rowCount.textContent = countText + limitedText;
}

/**
 * Display SQL query
 */
function displaySQL(sql, source) {
    document.getElementById('sqlQuery').textContent = sql;
    
    // Map source to display name
    const sourceMap = {
        'sqlcoder-7b': 'Generated by SQLCoder-7B',
        'gpt-oss-120b': 'Generated by GPT-OSS-120B',
        'llama-3.3-70b': 'Generated by LLaMA-3.3-70B',
        'groq-llama3': 'Generated by LLaMA-3.3-70B'
    };
    
    const sourceText = sourceMap[source] || `Generated by ${source}`;
    document.getElementById('sqlSource').textContent = sourceText;
}

/**
 * Toggle SQL section
 */
function toggleSQL() {
    const content = document.getElementById('sqlContent');
    const icon = document.getElementById('sqlToggleIcon');
    
    if (content.classList.contains('hidden')) {
        content.classList.remove('hidden');
        icon.classList.add('rotate-180');
    } else {
        content.classList.add('hidden');
        icon.classList.remove('rotate-180');
    }
}

/**
 * Display error
 */
function displayError(error) {
    const section = document.getElementById('errorSection');
    const message = document.getElementById('errorMessage');
    const suggestions = document.getElementById('errorSuggestions');
    
    message.textContent = error.message || 'An unexpected error occurred.';
    
    // Display suggestions if available
    suggestions.innerHTML = '';
    if (error.suggestions && error.suggestions.length > 0) {
        const title = document.createElement('h4');
        title.className = 'text-sm font-semibold text-red-800 mb-2';
        title.textContent = 'Try asking:';
        suggestions.appendChild(title);
        
        const list = document.createElement('div');
        list.className = 'space-y-1';
        error.suggestions.forEach(suggestion => {
            const btn = document.createElement('button');
            btn.className = 'block text-sm text-red-700 hover:text-red-900 underline';
            btn.textContent = suggestion;
            btn.onclick = () => fillQuestion(suggestion);
            list.appendChild(btn);
        });
        suggestions.appendChild(list);
    }
    
    section.classList.remove('hidden');
    section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Load suggested questions
 */
async function loadSuggestions() {
    try {
        const response = await fetch(`${API_BASE}/suggestions`);
        const data = await response.json();
        
        // Trending questions
        const trendingContainer = document.getElementById('trendingQuestions');
        trendingContainer.innerHTML = '';
        data.trending.forEach(q => {
            trendingContainer.appendChild(createQuestionButton(q, 'orange'));
        });
        
        // Suggested questions
        const suggestedContainer = document.getElementById('suggestedQuestions');
        suggestedContainer.innerHTML = '';
        data.suggested.forEach(q => {
            suggestedContainer.appendChild(createQuestionButton(q, 'blue'));
        });
        
    } catch (error) {
        console.error('Failed to load suggestions:', error);
    }
}

/**
 * Update recent questions
 */
async function updateRecentQuestions() {
    if (!sessionId) return;
    
    try {
        const response = await fetch(`${API_BASE}/session/${sessionId}/recent`);
        const data = await response.json();
        
        if (data.recent_questions && data.recent_questions.length > 0) {
            const section = document.getElementById('recentQuestionsSection');
            const container = document.getElementById('recentQuestions');
            
            container.innerHTML = '';
            data.recent_questions.forEach(q => {
                container.appendChild(createQuestionButton(q, 'gray'));
            });
            
            section.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Failed to load recent questions:', error);
    }
}

/**
 * Create question button
 */
function createQuestionButton(text, color) {
    const button = document.createElement('button');
    button.className = `w-full text-left px-3 py-2 text-sm rounded-lg border hover:bg-${color}-50 transition-colors`;
    button.textContent = text;
    button.onclick = () => fillQuestion(text);
    return button;
}

/**
 * Fill question in input and submit
 */
function fillQuestion(text) {
    const input = document.getElementById('questionInput');
    input.value = text;
    input.focus();
    
    // Auto-submit
    document.getElementById('queryForm').dispatchEvent(new Event('submit'));
}

/**
 * Update context indicator
 */
function updateContextIndicator(usedContext) {
    const indicator = document.getElementById('contextIndicator');
    if (usedContext) {
        indicator.classList.remove('hidden');
    } else {
        indicator.classList.add('hidden');
    }
}

/**
 * Check system health
 */
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        
        const indicator = document.getElementById('statusIndicator');
        if (data.status === 'healthy') {
            indicator.innerHTML = `
                <span class="h-3 w-3 rounded-full bg-green-400 animate-pulse mr-2"></span>
                <span class="text-sm">Connected</span>
            `;
        } else {
            indicator.innerHTML = `
                <span class="h-3 w-3 rounded-full bg-yellow-400 mr-2"></span>
                <span class="text-sm">Limited</span>
            `;
        }
    } catch (error) {
        const indicator = document.getElementById('statusIndicator');
        indicator.innerHTML = `
            <span class="h-3 w-3 rounded-full bg-red-400 mr-2"></span>
            <span class="text-sm">Offline</span>
        `;
    }
}

/**
 * UI helper functions
 */
function showLoading() {
    document.getElementById('loadingIndicator').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loadingIndicator').classList.add('hidden');
}

function showResults() {
    document.getElementById('resultsSection').classList.remove('hidden');
}

function hideResults() {
    document.getElementById('resultsSection').classList.add('hidden');
}

function showError() {
    document.getElementById('errorSection').classList.remove('hidden');
}

function hideError() {
    document.getElementById('errorSection').classList.add('hidden');
}

function hideWelcome() {
    document.getElementById('welcomeSection').classList.add('hidden');
}

/**
 * Utility functions
 */
function formatNumber(value) {
    if (value >= 1000000) {
        return '$' + (value / 1000000).toFixed(1) + 'M';
    } else if (value >= 1000) {
        return '$' + (value / 1000).toFixed(1) + 'K';
    } else {
        return '$' + value.toFixed(0);
    }
}

function formatValue(value) {
    if (value === null || value === undefined) {
        return '-';
    }
    if (typeof value === 'number') {
        if (value >= 100) {
            return value.toLocaleString('en-US', { maximumFractionDigits: 2 });
        }
        return value.toFixed(2);
    }
    return String(value);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * File Upload and Dataset Management
 */
let uploadedDataset = null;
let currentPage = 1;
let rowsPerPage = 100;

async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const statusDiv = document.getElementById('uploadStatus');
    const viewBtn = document.getElementById('viewDatasetBtn');
    
    statusDiv.className = 'text-sm text-blue-600';
    statusDiv.textContent = '📤 Uploading...';
    statusDiv.classList.remove('hidden');
    
    try {
        // Read CSV file
        const text = await file.text();
        const rows = parseCSV(text);
        
        if (rows.length === 0) {
            throw new Error('Empty CSV file');
        }
        
        uploadedDataset = {
            filename: file.name,
            rows: rows,
            rowCount: rows.length - 1, // Exclude header
            columns: rows[0]
        };
        
        currentPage = 1; // Reset pagination
        
        statusDiv.className = 'text-sm text-green-600';
        statusDiv.textContent = `✅ Uploaded: ${file.name} (${uploadedDataset.rowCount.toLocaleString()} rows)`;
        viewBtn.classList.remove('hidden');
        
        console.log('Dataset uploaded:', uploadedDataset);
        
    } catch (error) {
        console.error('Upload error:', error);
        statusDiv.className = 'text-sm text-red-600';
        statusDiv.textContent = `❌ Error: ${error.message}`;
        viewBtn.classList.add('hidden');
    }
}

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

function toggleDatasetView() {
    const modal = document.getElementById('datasetModal');
    
    if (modal.classList.contains('hidden')) {
        if (!uploadedDataset) return;
        
        // Reset to first page
        currentPage = 1;
        
        // Show modal
        modal.classList.remove('hidden');
        displayDatasetTable();
    } else {
        // Hide modal
        modal.classList.add('hidden');
    }
}

function displayDatasetTable() {
    if (!uploadedDataset) return;
    
    const infoDiv = document.getElementById('datasetInfo');
    const thead = document.getElementById('datasetTableHead');
    const tbody = document.getElementById('datasetTableBody');
    
    // Display info
    infoDiv.innerHTML = `
        <strong>File:</strong> ${uploadedDataset.filename} | 
        <strong>Total Rows:</strong> ${uploadedDataset.rowCount.toLocaleString()} | 
        <strong>Columns:</strong> ${uploadedDataset.columns.length}
    `;
    
    // Display headers
    const headerRow = document.createElement('tr');
    uploadedDataset.columns.forEach(col => {
        const th = document.createElement('th');
        th.className = 'px-6 py-3 text-left text-xs font-medium text-blue-800 uppercase tracking-wider bg-gradient-to-r from-blue-50 to-blue-100';
        th.textContent = col;
        headerRow.appendChild(th);
    });
    thead.innerHTML = '';
    thead.appendChild(headerRow);
    
    // Calculate pagination
    const totalPages = Math.ceil(uploadedDataset.rowCount / rowsPerPage);
    const startRow = (currentPage - 1) * rowsPerPage + 1;
    const endRow = Math.min(currentPage * rowsPerPage, uploadedDataset.rowCount);
    
    // Update pagination info
    document.getElementById('rowRangeStart').textContent = startRow.toLocaleString();
    document.getElementById('rowRangeEnd').textContent = endRow.toLocaleString();
    document.getElementById('totalRows').textContent = uploadedDataset.rowCount.toLocaleString();
    
    // Render pagination buttons
    renderPaginationButtons(totalPages);
    
    // Display rows for current page
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
    
    // Helper function to create button
    const createButton = (text, page, isActive = false, isDisabled = false) => {
        const btn = document.createElement('button');
        btn.textContent = text;
        btn.onclick = () => !isDisabled && goToPage(page);
        
        if (isActive) {
            btn.className = 'px-3 py-1 text-sm font-medium text-white bg-blue-600 rounded';
        } else if (isDisabled) {
            btn.className = 'px-3 py-1 text-sm text-gray-400 cursor-not-allowed';
        } else {
            btn.className = 'px-3 py-1 text-sm text-gray-700 bg-white border border-gray-300 rounded hover:bg-blue-50 hover:border-blue-500 hover:text-blue-600';
        }
        
        return btn;
    };
    
    // First page button
    container.appendChild(createButton('«', 1, false, currentPage === 1));
    
    // Calculate page range to show
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, currentPage + 2);
    
    // Adjust if near start or end
    if (currentPage <= 3) {
        endPage = Math.min(5, totalPages);
    }
    if (currentPage >= totalPages - 2) {
        startPage = Math.max(1, totalPages - 4);
    }
    
    // Show first page if not in range
    if (startPage > 1) {
        container.appendChild(createButton('1', 1));
        if (startPage > 2) {
            const ellipsis = document.createElement('span');
            ellipsis.textContent = '...';
            ellipsis.className = 'px-2 text-gray-500';
            container.appendChild(ellipsis);
        }
    }
    
    // Page number buttons
    for (let i = startPage; i <= endPage; i++) {
        container.appendChild(createButton(i.toString(), i, i === currentPage));
    }
    
    // Show last page if not in range
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            const ellipsis = document.createElement('span');
            ellipsis.textContent = '...';
            ellipsis.className = 'px-2 text-gray-500';
            container.appendChild(ellipsis);
        }
        container.appendChild(createButton(totalPages.toString(), totalPages));
    }
    
    // Last page button
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
    const select = document.getElementById('rowsPerPageSelect');
    rowsPerPage = parseInt(select.value);
    currentPage = 1; // Reset to first page
    displayDatasetTable();
}

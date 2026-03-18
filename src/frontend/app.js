/* global document, fetch, FileReader, Image */

const API_BASE = '';

// State
let selectedFile = null;
let currentImageId = null;
let conversationHistory = [];
let analysisContext = null;

// DOM elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const previewContainer = document.getElementById('preview-container');
const imagePreview = document.getElementById('image-preview');
const analyzeBtn = document.getElementById('analyze-btn');
const loadingEl = document.getElementById('loading');
const resultsSection = document.getElementById('results-section');
const descriptionText = document.getElementById('description-text');
const issuesList = document.getElementById('issues-list');
const bboxCanvas = document.getElementById('bbox-canvas');
const bboxCount = document.getElementById('bbox-count');
const chatSection = document.getElementById('chat-section');
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const chatSend = document.getElementById('chat-send');

// Drop zone events
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

function handleFile(file) {
    if (!file.type.startsWith('image/')) {
        showError('Please select an image file.');
        return;
    }
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        imagePreview.src = e.target.result;
        previewContainer.classList.remove('hidden');
        dropZone.classList.add('hidden');
    };
    reader.readAsDataURL(file);
}

// Analyze button
analyzeBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    analyzeBtn.disabled = true;
    loadingEl.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    chatSection.classList.add('hidden');

    try {
        const formData = new FormData();
        formData.append('file', selectedFile);

        const response = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Analysis failed');
        }

        const result = await response.json();
        currentImageId = result.image_id;
        analysisContext = JSON.stringify(result);
        conversationHistory = [];

        displayResults(result);
    } catch (error) {
        showError(`Analysis failed: ${error.message}`);
    } finally {
        analyzeBtn.disabled = false;
        loadingEl.classList.add('hidden');
    }
});

function displayResults(result) {
    // Description
    descriptionText.textContent = result.description;

    // Issues
    issuesList.innerHTML = '';
    if (result.issues_found.length === 0) {
        const li = document.createElement('li');
        li.className = 'info';
        li.textContent = 'No issues detected';
        issuesList.appendChild(li);
    } else {
        result.issues_found.forEach((issue) => {
            const li = document.createElement('li');
            if (issue.includes('[ERROR]') || issue.includes('[HIGH]')) {
                li.className = 'error';
            } else if (issue.includes('[WARNING]') || issue.includes('[MEDIUM]')) {
                li.className = 'warning';
            } else {
                li.className = 'info';
            }
            li.textContent = issue;
            issuesList.appendChild(li);
        });
    }

    // Bounding boxes on canvas
    drawBoundingBoxes(result.bounding_boxes);

    // Show results and chat
    resultsSection.classList.remove('hidden');
    chatSection.classList.remove('hidden');
    chatMessages.innerHTML = '';

    // Add welcome message
    addChatMessage(
        'assistant',
        "I've analyzed your electrical schema. You can ask me questions about the issues found, " +
            'or request me to produce an updated schema to fix the problems. What would you like to know?'
    );
}

function drawBoundingBoxes(boxes) {
    const img = new Image();
    img.onload = () => {
        const canvas = bboxCanvas;
        const scale = Math.min(800 / img.width, 600 / img.height, 1);
        canvas.width = img.width * scale;
        canvas.height = img.height * scale;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        const colors = {
            text: 'rgba(0, 120, 212, 0.5)',
            table: 'rgba(56, 142, 60, 0.5)',
            selection_mark: 'rgba(245, 124, 0, 0.5)',
            issue: 'rgba(211, 47, 47, 0.7)',
        };

        let drawnCount = 0;
        boxes.forEach((box) => {
            if (box.polygon && box.polygon.length >= 4) {
                ctx.strokeStyle = colors[box.type] || 'rgba(0, 120, 212, 0.5)';
                ctx.lineWidth = 2;
                ctx.beginPath();

                // Polygon points are in normalized coordinates (0-1) from Doc Intelligence
                const points = [];
                for (let i = 0; i < box.polygon.length; i += 2) {
                    points.push({
                        x: box.polygon[i] * canvas.width,
                        y: box.polygon[i + 1] * canvas.height,
                    });
                }

                if (points.length > 0) {
                    ctx.moveTo(points[0].x, points[0].y);
                    for (let i = 1; i < points.length; i++) {
                        ctx.lineTo(points[i].x, points[i].y);
                    }
                    ctx.closePath();
                    ctx.stroke();
                    drawnCount++;
                }
            }
        });

        bboxCount.textContent = `${drawnCount} regions detected, ${boxes.filter((b) => b.type === 'issue').length} issues highlighted`;
    };
    img.src = imagePreview.src;
}

// Chat functionality
chatSend.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message || !currentImageId) return;

    addChatMessage('user', message);
    chatInput.value = '';
    chatSend.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                image_id: currentImageId,
                analysis_context: analysisContext,
                conversation_history: conversationHistory,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Chat failed');
        }

        const result = await response.json();
        conversationHistory.push({ role: 'user', content: message });
        conversationHistory.push({ role: 'assistant', content: result.reply });

        addChatMessage('assistant', result.reply);
    } catch (error) {
        addChatMessage('assistant', `Error: ${error.message}`);
    } finally {
        chatSend.disabled = false;
    }
}

function addChatMessage(role, content) {
    const div = document.createElement('div');
    div.className = `chat-message ${role}`;

    // Simple markdown-like formatting for code blocks
    const formatted = content.replace(/```([\s\S]*?)```/g, '<pre>$1</pre>');
    div.innerHTML = formatted;

    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showError(message) {
    const div = document.createElement('div');
    div.style.cssText =
        'background:#fce4ec;color:#d32f2f;padding:1rem;border-radius:4px;margin:1rem 0;';
    div.textContent = message;
    document.querySelector('main').prepend(div);
    setTimeout(() => div.remove(), 5000);
}

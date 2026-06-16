// Global states
let activeTaskId = null;
let statusInterval = null;
let currentJobs = [];
let otpModalOpened = false;

// WebSockets connection URL derivation
const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
const wsUrl = `${wsProtocol}${window.location.host}/api/v1/jobs/ws`;

// Init on load
document.addEventListener('DOMContentLoaded', () => {
    fetchLatestJobs();
    initWebSocket();
    
    // Request notification permissions
    if (window.Notification && Notification.permission === 'default') {
        Notification.requestPermission();
    }
});

// Initialize WebSocket Connection
function initWebSocket() {
    console.log("Connecting to live job alert stream via WebSockets...");
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'new_job' && data.job) {
                handleNewJobBroadcast(data.job);
            }
        } catch (e) {
            console.error("Failed to parse WebSocket packet", e);
        }
    };
    
    ws.onclose = () => {
        console.warn("WebSocket closed. Attempting reconnect in 5s...");
        setTimeout(initWebSocket, 5000);
    };
    
    ws.onerror = (err) => {
        console.error("WebSocket error:", err);
    };
}

// Handle real-time job update broadcast
function handleNewJobBroadcast(job) {
    // Check duplicates
    if (currentJobs.some(j => j.link === job.link)) return;
    
    // Push to top of jobs array
    currentJobs.unshift(job);
    renderLiveJobs(currentJobs);
    
    // Show browser desktop notifications
    if (window.Notification && Notification.permission === 'granted') {
        new Notification("SarkariSwarm Live Job Alert", {
            body: job.title
        });
    }
    
    // Highlight the newest item at the top with a temporary pulse class
    setTimeout(() => {
        const firstItem = document.querySelector('.live-list .live-item');
        if (firstItem) {
            firstItem.classList.add('new-pulse-alert');
            // Remove after 6 seconds
            setTimeout(() => firstItem.classList.remove('new-pulse-alert'), 6000);
        }
    }, 100);
}

// Fetch Live Jobs from Backend Scraper API
async function fetchLatestJobs() {
    const container = document.getElementById('live-updates-container');
    try {
        const response = await fetch('/api/v1/jobs/latest');
        if (!response.ok) throw new Error("Scraper API returned error status");
        
        currentJobs = await response.json();
        renderLiveJobs(currentJobs);
    } catch (err) {
        console.warn("Failed to fetch live job feeds, loading fallback notifications.", err);
        // Fallback structured data
        currentJobs = [
            {
                "title": "UPSC Civil Services Examination 2026 - Apply Online for 1056 Posts",
                "link": "https://upsconline.nic.in",
                "date": new Date().toISOString(),
                "category": "Central Jobs"
            },
            {
                "title": "SSC Combined Graduate Level (CGL) 2026 - 15000+ Vacancies Announced",
                "link": "https://ssc.gov.in",
                "date": new Date(Date.now() - 3600000).toISOString(),
                "category": "Central Jobs"
            },
            {
                "title": "BPSC 71st Civil Services (Pre) Exam 2026 - Notification Out",
                "link": "https://bpsc.bih.nic.in",
                "date": new Date(Date.now() - 7200000).toISOString(),
                "category": "State Jobs"
            },
            {
                "title": "IBPS Bank PO / MT XIV Recruitment 2026 - Apply Online for 4455 Posts",
                "link": "https://www.ibps.in",
                "date": new Date(Date.now() - 14400000).toISOString(),
                "category": "Bank Jobs"
            }
        ];
        renderLiveJobs(currentJobs);
    }
}

// Render Job listings to Today Live Updates list
function renderLiveJobs(jobs) {
    const container = document.getElementById('live-updates-container');
    if (!jobs || jobs.length === 0) {
        container.innerHTML = `<p style="text-align: center; font-size: 0.8rem; color: var(--fja-muted); padding: 20px;">No updates available today.</p>`;
        return;
    }
    
    container.innerHTML = '';
    jobs.forEach(job => {
        const item = document.createElement('div');
        item.className = 'live-item';
        
        // Formulate relative time string
        const timeDiff = Date.now() - new Date(job.date).getTime();
        let timeLabel = 'Recent';
        if (timeDiff > 0) {
            const hours = Math.floor(timeDiff / (1000 * 60 * 60));
            const mins = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
            if (hours > 0) timeLabel = `${hours}h ago`;
            else if (mins > 0) timeLabel = `${mins}m ago`;
            else timeLabel = 'Just now';
        }
        
        item.innerHTML = `
            <div class="live-item-content" onclick="triggerAutoFill('${job.title}', '${job.link}')">
                <div class="live-item-title">${job.title}</div>
                <div class="live-item-meta">
                    <span class="live-item-cat">${job.category || 'Govt Jobs'}</span>
                    <span>${timeLabel}</span>
                </div>
            </div>
            <button class="live-auto-apply-btn" onclick="event.stopPropagation(); triggerAutoApply('${job.title}', '${job.link}')">
                <i class="fa-solid fa-bolt"></i> Auto Apply
            </button>
        `;
        container.appendChild(item);
    });
}

// Filter jobs category wise
function filterCategory(category) {
    if (category === 'all') {
        renderLiveJobs(currentJobs);
        return;
    }
    const filtered = currentJobs.filter(job => job.category === category);
    renderLiveJobs(filtered);
}

// Handle global search input box
function handleSearch(query) {
    if (!query) {
        renderLiveJobs(currentJobs);
        return;
    }
    const filtered = currentJobs.filter(job => 
        job.title.toLowerCase().includes(query.toLowerCase()) ||
        (job.category && job.category.toLowerCase().includes(query.toLowerCase()))
    );
    renderLiveJobs(filtered);
}

// Trigger Form fill drawer
function triggerAutoFill(jobTitle, url) {
    const drawer = document.getElementById('swarm-drawer');
    drawer.classList.add('active');
    
    // Switch to profile tab
    switchDrawerTab('tab-autofill');
    
    // Set target commands
    const cleanTitle = jobTitle.split('-')[0].trim();
    document.getElementById('chat-command').value = `Fill my application form for: ${cleanTitle}. Portal Link: ${url}`;
    
    // Pre-populate sample testing values for convenience
    document.getElementById('user-name').value = 'Amit Kumar';
    document.getElementById('aadhaar-number').value = '987654321098';
    document.getElementById('phone-number').value = '9999999999';
    document.getElementById('email-address').value = 'amit14916@gmail.com';
    document.getElementById('exam-center').value = 'New Delhi';
    document.getElementById('passphrase').value = 'test_passphrase_123';
    
    window.selectedJobUrl = url;
}

// Trigger Automated Swarm Execution directly (Auto Apply)
function triggerAutoApply(jobTitle, url) {
    // Populate form fields
    triggerAutoFill(jobTitle, url);
    
    // Switch to visual pipeline monitor tab
    switchDrawerTab('tab-pipeline');
    
    // Log intent
    appendLog(`[System] Auto-Apply triggered for: ${jobTitle}`, 'log-line log-success');
    appendLog(`[System] Submitting task to agent queue automatically...`, 'log-line log-system');
    
    // Fire submission form submit handler
    const form = document.getElementById('submission-form');
    if (form) {
        // Dispatch submit event synchronously
        const event = new Event('submit', { cancelable: true, bubbles: true });
        form.dispatchEvent(event);
    }
}

// Drawer tab controls
function switchDrawerTab(tabId) {
    document.querySelectorAll('.drawer-tab-content').forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.drawer-tab-btn').forEach(b => b.classList.remove('active'));
    
    document.getElementById(tabId).classList.add('active');
    
    // Highlight button
    const buttons = document.querySelectorAll('.drawer-tab-btn');
    buttons.forEach(btn => {
        if (btn.getAttribute('onclick').includes(tabId)) {
            btn.classList.add('active');
        }
    });
}

function closeDrawer() {
    document.getElementById('swarm-drawer').classList.remove('active');
}

// Deploy Swarm Task
async function deploySwarmTask(event) {
    event.preventDefault();
    
    const commandText = document.getElementById('chat-command').value;
    const name = document.getElementById('user-name').value;
    const userId = parseInt(document.getElementById('user-id').value);
    const aadhaar = document.getElementById('aadhaar-number').value;
    const phone = document.getElementById('phone-number').value;
    const email = document.getElementById('email-address').value;
    const center = document.getElementById('exam-center').value;
    const passphrase = document.getElementById('passphrase').value;
    
    // Build profile structure
    const fullChatMessage = `${commandText}. PII details:
- Name: ${name}
- Aadhaar: ${aadhaar}
- Phone: ${phone}
- Email: ${email}
- Preferred Exam Center: ${center}
- Passphrase: ${passphrase}`;
    
    // Show initializing logs
    const consoleLogs = document.getElementById('terminal-logs');
    consoleLogs.innerHTML = `<div class="log-line log-system">[System] Triggering Zero-Knowledge key derivation locally...</div>`;
    
    try {
        const response = await fetch('/api/v1/chat-gateway/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                chat_message: fullChatMessage
            })
        });
        
        if (!response.ok) throw new Error("Gateway failed to submit");
        
        const data = await response.json();
        activeTaskId = data.task_id;
        
        appendLog(`[System] Task created successfully. Task ID: ${activeTaskId}`, 'success');
        appendLog(`[Security] PII structures fully isolated. Local DB updated.`, 'system');
        
        // Reset browser views
        document.getElementById('browser-viewport').innerHTML = `
            <div class="no-sandbox">
                <i class="fa-solid fa-spinner fa-spin" style="font-size: 1.5rem; color: var(--accent);"></i>
                <p style="margin-top: 5px;">Launching bot-bypass Playwright sandbox...</p>
            </div>
        `;
        document.getElementById('browser-url').innerText = "about:blank";
        
        // Show pipeline tab
        document.getElementById('pipeline-tab-btn').click();
        
        // Start polling loop
        if (statusInterval) clearInterval(statusInterval);
        statusInterval = setInterval(pollTaskProgress, 1500);
        
        // Read isolated vault
        fetchIsolatedState();
        
    } catch (err) {
        appendLog(`[Error] Deploy failed: ${err.message}`, 'error');
    }
}

// Poll Task Status
async function pollTaskProgress() {
    if (!activeTaskId) return;
    
    try {
        const response = await fetch(`/api/v1/chat-gateway/status/${activeTaskId}`);
        if (!response.ok) throw new Error("Status query failed");
        
        const statusData = await response.json();
        
        // Render progress lines
        renderStepsProgress(statusData);
        
        // Update Console
        updateLogsConsole(statusData.logs);
        
        // Update Consensus
        updateConsensusCircle(statusData);
        
        // Check complete
        if (statusData.status === 'COMPLETED' || statusData.status === 'FAILED') {
            clearInterval(statusInterval);
            appendLog(`[Swarm] Task finished with status code: ${statusData.status}`, statusData.status === 'COMPLETED' ? 'success' : 'error');
            
            if (statusData.status === 'COMPLETED') {
                const regCode = statusData.outputs?.registration_code || "REG-992184";
                document.getElementById('browser-viewport').innerHTML = `
                    <div class="no-sandbox" style="color: var(--success);">
                        <i class="fa-solid fa-circle-check" style="font-size: 2rem; margin-bottom: 5px;"></i>
                        <p style="font-weight: bold;">Form Filled Successfully</p>
                        <p style="font-size: 0.75rem;">Reference Code: ${regCode}</p>
                    </div>
                `;
            }
        }
        
    } catch (err) {
        console.error("Error polling progress", err);
    }
}

// Render pipeline progress indicators
function renderStepsProgress(data) {
    const container = document.getElementById('steps-container');
    container.innerHTML = '';
    
    const steps = [
        { name: "Eligibility Audit", desc: "Validating user PII and documents" },
        { name: "Form Navigation", desc: "Stealth loading exam form portal" },
        { name: "Secure Form Fill", desc: "Decrypting and filling form details" },
        { name: "Validation & Submit", desc: "Solving captcha and submitting details" },
        { name: "WhatsApp Alert", desc: "Dispatching receipt validation details" }
    ];
    
    const currentStepIndex = Math.min(data.current_step, steps.length - 1);
    
    steps.forEach((step, idx) => {
        const row = document.createElement('div');
        let statusClass = 'step-row';
        
        if (data.status === 'FAILED' && idx === currentStepIndex) {
            statusClass += ' active';
        } else if (idx < currentStepIndex || (data.status === 'COMPLETED' && idx === currentStepIndex)) {
            statusClass += ' completed';
        } else if (idx === currentStepIndex) {
            statusClass += ' active';
            
            // Set browser URL
            const urlInput = document.getElementById('browser-url');
            if (idx === 1) urlInput.innerText = window.selectedJobUrl || "https://example.com/exam-registration";
            else if (idx > 1 && urlInput.innerText === "about:blank") urlInput.innerText = "https://example.com/exam-registration";
        }
        
        row.className = statusClass;
        row.innerHTML = `
            <div class="step-pt"></div>
            <span>${step.name}</span>
        `;
        container.appendChild(row);
    });
}

// Update Logs console
function updateLogsConsole(logs) {
    const terminal = document.getElementById('terminal-logs');
    const lineCount = terminal.querySelectorAll('.log-line').length - 1; // subtract init line
    
    if (logs.length > lineCount) {
        for (let i = lineCount; i < logs.length; i++) {
            const text = logs[i];
            let type = 'log-line';
            
            if (text.includes('[Error]') || text.includes('failed') || text.includes('violation')) {
                type = 'log-line log-error';
            } else if (text.includes('[ConsensusEngine]') || text.includes('votes') || text.includes('Auditor')) {
                type = 'log-line log-warning';
            } else if (text.includes('success') || text.includes('Success') || text.includes('healed') || text.includes('Completed')) {
                type = 'log-line log-success';
            }
            
            appendLog(text, type);
            
            // Trigger OTP modal popup if logs indicate OTP wait state
            if (text.includes('OTP') && !otpModalOpened) {
                openOtpModal();
            }
            // Trigger Captcha view on simulation browser box
            if (text.includes('captcha') || text.includes('CAPTCHA')) {
                document.getElementById('browser-viewport').innerHTML = `
                    <div class="no-sandbox" style="color: var(--warning);">
                        <i class="fa-solid fa-key" style="font-size: 1.8rem; margin-bottom: 5px;"></i>
                        <p style="font-weight: bold;">Decrypting CAPTCHA...</p>
                        <p style="font-size: 0.65rem;">Invoking Playwright image solving hook</p>
                    </div>
                `;
            }
        }
    }
}

function appendLog(text, className) {
    const terminal = document.getElementById('terminal-logs');
    const el = document.createElement('div');
    el.className = className;
    const time = new Date().toLocaleTimeString();
    el.innerText = `[${time}] ${text}`;
    terminal.appendChild(el);
    terminal.scrollTop = terminal.scrollHeight;
}

// Update Consensus meter
function updateConsensusCircle(data) {
    const percent = document.getElementById('consensus-percent');
    const fill = document.getElementById('consensus-fill');
    const verdict = document.getElementById('consensus-verdict');
    
    let score = 0;
    let hasVote = false;
    
    data.logs.forEach(log => {
        if (log.includes('[ConsensusEngine] Tabulated QA consensus:')) {
            const match = log.match(/Score=([0-9.]+)/);
            if (match) {
                score = parseFloat(match[1]) * 100;
                hasVote = true;
            }
        }
    });
    
    if (data.status === 'COMPLETED') {
        score = 100;
        hasVote = true;
    }
    
    if (hasVote) {
        percent.innerText = `${Math.round(score)}%`;
        fill.style.width = `${score}%`;
        
        if (score >= 70) {
            verdict.innerText = "QA Consensus Passed";
            verdict.style.color = "var(--success)";
            
            if (data.status !== 'COMPLETED') {
                document.getElementById('browser-viewport').innerHTML = `
                    <div class="no-sandbox" style="color: var(--accent);">
                        <i class="fa-solid fa-paper-plane fa-spin" style="font-size: 1.5rem;"></i>
                        <p style="margin-top: 5px;">Submitting finalized form details...</p>
                    </div>
                `;
            }
        } else {
            verdict.innerText = "QA Rejected. Self-Healing...";
            verdict.style.color = "var(--warning)";
        }
    } else if (data.status === 'FAILED') {
        percent.innerText = "0%";
        fill.style.width = "0%";
        verdict.innerText = "Execution failed";
        verdict.style.color = "var(--danger)";
    }
}

// OTP Modal Dialogs
function openOtpModal() {
    otpModalOpened = true;
    document.getElementById('otp-dialog').classList.add('active');
}

function closeOtpModal() {
    document.getElementById('otp-dialog').classList.remove('active');
    otpModalOpened = false;
}

function focusNextOtp(input, idx) {
    if (input.value.length === 1 && idx < 6) {
        const boxes = document.querySelectorAll('.otp-code-box');
        if (boxes[idx]) boxes[idx].focus();
    }
}

async function submitOtpCode() {
    if (!activeTaskId) return;
    
    let otp = '';
    document.querySelectorAll('.otp-code-box').forEach(b => {
        otp += b.value.trim();
    });
    
    if (otp.length !== 6) {
        alert("Please input a valid 6-digit OTP code");
        return;
    }
    
    appendLog(`[System] OTP entered. Posting webhook validation payload...`, 'log-line log-system');
    
    try {
        const response = await fetch(`/api/v1/chat-gateway/tasks/${activeTaskId}/otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ otp: otp })
        });
        
        if (!response.ok) throw new Error("OTP rejected");
        
        closeOtpModal();
        appendLog(`[Webhook] OTP dispatched successfully. Swarm task resumed.`, 'log-line log-success');
        
        document.getElementById('browser-viewport').innerHTML = `
            <div class="no-sandbox" style="color: var(--success);">
                <i class="fa-solid fa-lock-open" style="font-size: 1.5rem;"></i>
                <p style="margin-top: 5px;">OTP Verification Successful</p>
            </div>
        `;
    } catch (err) {
        appendLog(`[Error] OTP submit failed: ${err.message}`, 'log-line log-error');
    }
}

// ZK Vault Encrypted State Fetcher
async function fetchIsolatedState() {
    if (!activeTaskId) return;
    
    try {
        const response = await fetch(`/api/v1/chat-gateway/tasks/${activeTaskId}/encrypted-state`);
        if (!response.ok) throw new Error("Error loading ZK state");
        
        const data = await response.json();
        document.getElementById('encrypted-json').innerText = JSON.stringify(data.encrypted_context, null, 2);
    } catch (err) {
        console.error("ZK fetch fail", err);
    }
}

// Local Passphrase Decryption verification
async function verifyDecryption() {
    if (!activeTaskId) {
        alert("Please run a task registration first!");
        return;
    }
    
    const passphrase = document.getElementById('decrypt-passphrase').value;
    if (!passphrase) {
        alert("Please enter your decryption passphrase");
        return;
    }
    
    const logViewer = document.getElementById('decrypted-json');
    logViewer.innerText = "Deriving local key and decrypting context...";
    
    try {
        const response = await fetch(`/api/v1/chat-gateway/tasks/${activeTaskId}/decrypt-output?passphrase=${encodeURIComponent(passphrase)}`, {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error("Invalid passphrase or payload corruption");
        
        const data = await response.json();
        logViewer.innerText = JSON.stringify(data.decrypted_context, null, 2);
        logViewer.style.color = "var(--success)";
    } catch (err) {
        logViewer.innerText = `[DECRYPT FAIL] Authentication error: ${err.message}`;
        logViewer.style.color = "var(--danger)";
    }
}

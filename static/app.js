// SarkariSwarm - Core Javascript Application Coordinator

let authToken = null;
let activeTaskId = null;
let activeEventSource = null;
let selectedCategory = "";
let activePortalUrl = "https://upsconline.nic.in";

// Global Fetch Interceptor for 401 Unauthorized
const originalFetch = window.fetch;
window.fetch = async function (url, options) {
    const response = await originalFetch(url, options);
    if (response.status === 401) {
        const urlStr = String(url);
        if (!urlStr.includes('/auth/login') && !urlStr.includes('/auth/register')) {
            handleLogout();
            showToast("Session expired. Please sign in again.", "error");
        }
    }
    return response;
};

// Initialize App on DOM Load
document.addEventListener('DOMContentLoaded', () => {
    initApp();
    setupCategoryChips();
});

// Helper: Toast Notifications
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast-notification');
    toast.className = `toast ${type} active`;
    toast.innerText = message;
    
    setTimeout(() => {
        toast.classList.remove('active');
    }, 4000);
}

// Helper: Parse email from JWT token payload
function parseJwtEmail(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        const payload = JSON.parse(jsonPayload);
        return payload.sub; // sub holds the user email
    } catch (e) {
        return null;
    }
}

// Initialize application state
function initApp() {
    const token = localStorage.getItem('auth_token');
    if (token) {
        authToken = token;
        showMainApp();
    } else {
        showAuthScreen();
    }
}

function showAuthScreen() {
    document.getElementById('auth-screen').style.display = 'flex';
    document.getElementById('app-screen').style.display = 'none';
}

function showMainApp() {
    document.getElementById('auth-screen').style.display = 'none';
    document.getElementById('app-screen').style.display = 'grid';
    
    // Set user email in sidebar display
    const email = parseJwtEmail(authToken);
    document.getElementById('user-email-display').innerText = email || "candidate@sarkariswarm.in";
    
    // Switch to default panel: Dashboard
    switchPanel('panel-dashboard');
}

// Switching Auth Tabs (Login / Register)
function switchAuthTab(tab) {
    document.querySelectorAll('.auth-tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.auth-form').forEach(form => form.classList.remove('active'));
    
    if (tab === 'login') {
        document.getElementById('tab-login-btn').classList.add('active');
        document.getElementById('login-form').classList.add('active');
    } else {
        document.getElementById('tab-register-btn').classList.add('active');
        document.getElementById('register-form').classList.add('active');
    }
}

// 1. SIGN IN API CALL
async function handleLoginSubmit(event) {
    event.preventDefault();
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    
    try {
        const response = await fetch('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Authentication credentials failed");
        }
        
        authToken = data.access_token;
        localStorage.setItem('auth_token', authToken);
        showToast("Signed in successfully!");
        showMainApp();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// 2. REGISTER API CALL
async function handleRegisterSubmit(event) {
    event.preventDefault();
    const email = document.getElementById('register-email').value.trim();
    const phone = document.getElementById('register-phone').value.trim();
    const password = document.getElementById('register-password').value;
    
    try {
        const response = await fetch('/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, phone })
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Registration failed");
        }
        
        showToast("Registration successful! Please login.");
        switchAuthTab('login');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// SIGN OUT
function handleLogout() {
    authToken = null;
    localStorage.removeItem('auth_token');
    sessionStorage.removeItem('zk_passphrase');
    showToast("Signed out successfully.");
    showAuthScreen();
}

// 3. SIDEBAR NAVIGATION CONTROLLER
function switchPanel(panelId) {
    document.querySelectorAll('.dashboard-panel').forEach(panel => panel.classList.remove('active'));
    document.querySelectorAll('.sidebar-menu .menu-item').forEach(menu => menu.classList.remove('active'));
    
    document.getElementById(panelId).classList.add('active');
    
    const menuItem = document.getElementById(`nav-${panelId}`);
    if (menuItem) {
        menuItem.classList.add('active');
    }
    
    // Trigger panel-specific loaders
    if (panelId === 'panel-dashboard') {
        loadDashboard();
    } else if (panelId === 'panel-profile') {
        loadProfile();
    } else if (panelId === 'panel-documents') {
        loadDocuments();
    } else if (panelId === 'panel-applied') {
        loadApplied();
    }
}

// 4. PROFILE CONTROLLER & INTERACTIVE CHIPS
function setupCategoryChips() {
    const chipWrapper = document.getElementById('category-chips-wrapper');
    if (!chipWrapper) return;
    
    chipWrapper.addEventListener('click', (e) => {
        const chip = e.target.closest('.chip');
        if (!chip) return;
        
        // Remove active class from all sibling chips
        chipWrapper.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
        
        // Mark selected chip active
        chip.classList.add('active');
        selectedCategory = chip.getAttribute('data-category');
        document.getElementById('profile-category').value = selectedCategory;
    });
}

async function loadProfile() {
    try {
        const response = await fetch('/profile', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const profile = await response.json();
            document.getElementById('profile-full-name').value = profile.full_name || '';
            document.getElementById('profile-dob').value = profile.dob || '';
            document.getElementById('profile-gender').value = profile.gender || '';
            document.getElementById('profile-state').value = profile.state || '';
            document.getElementById('profile-district').value = profile.district || '';
            document.getElementById('profile-qualification').value = profile.qualification || '';
            document.getElementById('profile-phone').value = profile.phone || '';
            document.getElementById('profile-email').value = profile.email || '';
            document.getElementById('profile-aadhaar').value = profile.aadhaar_decrypted || '';
            document.getElementById('profile-pan').value = profile.pan || '';
            
            // Set category chips active selection
            selectedCategory = profile.category || '';
            document.getElementById('profile-category').value = selectedCategory;
            
            const chipWrapper = document.getElementById('category-chips-wrapper');
            chipWrapper.querySelectorAll('.chip').forEach(chip => {
                if (chip.getAttribute('data-category') === selectedCategory) {
                    chip.classList.add('active');
                } else {
                    chip.classList.remove('active');
                }
            });
            
            // Retrieve passphrase from session storage to fill the password box temporarily
            const localPass = sessionStorage.getItem('zk_passphrase');
            if (localPass) {
                document.getElementById('profile-passphrase').value = localPass;
            }
        }
    } catch (err) {
        console.error("Failed to load user profile:", err);
    }
}

async function handleProfileSubmit(event) {
    event.preventDefault();
    const passphrase = document.getElementById('profile-passphrase').value;
    sessionStorage.setItem('zk_passphrase', passphrase); // Save passphrase to memory
    
    const payload = {
        full_name: document.getElementById('profile-full-name').value.trim(),
        dob: document.getElementById('profile-dob').value,
        gender: document.getElementById('profile-gender').value,
        category: document.getElementById('profile-category').value,
        state: document.getElementById('profile-state').value.trim(),
        district: document.getElementById('profile-district').value.trim(),
        qualification: document.getElementById('profile-qualification').value,
        phone: document.getElementById('profile-phone').value.trim(),
        email: document.getElementById('profile-email').value.trim(),
        aadhaar: document.getElementById('profile-aadhaar').value.trim(),
        pan: document.getElementById('profile-pan').value.trim() || null
    };
    
    try {
        const response = await fetch('/profile', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Profile update failed");
        }
        
        showToast("Profile vault encrypted and saved successfully!");
        loadProfile();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// 5. DOCUMENTS CONTROLLER & MULTIPART UPLOADS
async function loadDocuments() {
    try {
        const response = await fetch('/profile/documents', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!response.ok) throw new Error("Could not load documents list");
        
        const docs = await response.json();
        
        // Reset slot indicators
        const slots = ['photo', 'signature', 'aadhaar', 'caste_cert', 'marksheet', 'degree'];
        slots.forEach(slot => {
            const badge = document.getElementById(`badge-${slot}`);
            if (badge) {
                badge.className = "doc-badge pending";
                badge.innerText = "Missing";
            }
            const link = document.getElementById(`view-${slot}`);
            if (link) {
                link.innerHTML = "";
            }
        });
        
        // Update loaded uploads
        docs.forEach(doc => {
            let uiSlot = doc.doc_type;
            
            // Map file types to UI display slots
            const badge = document.getElementById(`badge-${uiSlot}`);
            if (badge) {
                badge.className = "doc-badge uploaded";
                badge.innerText = "Uploaded";
            }
            
            const link = document.getElementById(`view-${uiSlot}`);
            if (link) {
                // Ensure file paths are relative to base host context
                const cleanPath = doc.file_path.startsWith('/') ? doc.file_path : `/${doc.file_path}`;
                link.innerHTML = `<a href="${cleanPath}" target="_blank"><i class="fa-solid fa-arrow-up-right-from-square"></i> Open File</a>`;
            }
        });
    } catch (err) {
        console.error("Failed to list uploaded documents:", err);
    }
}

async function triggerDirectUpload(inputElement) {
    const docType = inputElement.id.split('-')[1]; // e.g., photo
    await uploadDocumentFile(inputElement.files[0], docType);
}

async function triggerDirectUploadMapped(inputElement, backendType, uiLabel) {
    // Allows degree slots to act as marksheet uploads
    await uploadDocumentFile(inputElement.files[0], backendType, uiLabel);
}

async function uploadDocumentFile(file, docType, uiLabel = null) {
    if (!file) return;
    
    const formData = new FormData();
    formData.append("doc_type", docType);
    formData.append("file", file);
    
    showToast(`Uploading ${uiLabel || docType}...`, 'success');
    
    try {
        const response = await fetch('/profile/documents', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` },
            body: formData
        });
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Document upload failed");
        
        showToast("File uploaded successfully!");
        loadDocuments();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function parseDate(val) {
  if (!val) return null;
  const s = String(val).replace(/\//g, '-').trim();
  const d = new Date(s + 'T00:00:00');
  return isNaN(d) ? null : d;
}

function getDaysLeft(dateStr) {
  const d = parseDate(dateStr);
  if (!d) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.ceil((d - today) / (1000 * 60 * 60 * 24));
}

function formatDate(dateStr) {
  const d = parseDate(dateStr);
  if (!d) return 'TBA';
  return d.toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric'
  });
}

// 6. DASHBOARD & ELIGIBILITY LOADER
async function loadDashboard() {
    try {
        // Fetch Stats
        const statsResponse = await fetch('/dashboard/stats', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (statsResponse.ok) {
            const stats = await statsResponse.json();
            document.getElementById('stat-eligible-count').innerText = stats.eligible_count !== undefined ? stats.eligible_count : (stats.eligible_exams_count || 0);
            document.getElementById('stat-applied-count').innerText = stats.applied_count !== undefined ? stats.applied_count : (stats.total_applications || 0);
            document.getElementById('stat-free-count').innerText = stats.free_count !== undefined ? stats.free_count : 0;
        }
        
        // Fetch Eligible Exams
        const container = document.getElementById('exams-list-container');
        container.innerHTML = `
            <div class="list-empty">
                <i class="fa-solid fa-circle-notch fa-spin"></i>
                <p>Checking your profile parameters...</p>
            </div>
        `;
        
        const examsResponse = await fetch('/eligibility/check', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!examsResponse.ok) {
            if (examsResponse.status === 400) {
                container.innerHTML = `
                    <div class="list-empty">
                        <i class="fa-solid fa-user-gear"></i>
                        <p>Please complete your profile details to view eligible government examinations.</p>
                        <button class="btn btn-primary btn-sm" onclick="switchPanel('panel-profile')" style="margin-top: 10px;">
                            <i class="fa-solid fa-id-card"></i> Fill Profile Vault
                        </button>
                    </div>
                `;
                return;
            }
            const errData = await examsResponse.json();
            throw new Error(errData.detail || "Failed to parse eligibility checklist");
        }
        
        const eligibleExams = await examsResponse.json();
        
        // Console log full exam objects as requested
        eligibleExams.forEach(exam => {
            console.log("Full exam object:", exam);
        });

        const today = new Date(); today.setHours(0,0,0,0);
        const validExams = eligibleExams.filter(e => {
          const d = parseDate(e.last_date);
          return d && d >= today;
        });

        if (validExams.length === 0) {
            container.innerHTML = `
                <div class="list-empty">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <p>No examinations currently match your eligibility parameters. Double check qualifications or domicile state in your profile.</p>
                </div>
            `;
            return;
        }
        
        // Build cards
        container.innerHTML = validExams.map(exam => {
            const isFree = exam.fee === 0;
            const feeDisplay = isFree 
                ? '<span class="fee-waiver-badge"><i class="fa-solid fa-tag"></i> FREE</span>' 
                : `<span class="fee-charged">₹${exam.fee} Exam Fee</span>`;
            
            // Calculate days left dynamically
            const daysLeft = getDaysLeft(exam.last_date);
            
            let badgeBg = '#22c55e'; // green
            let badgeText = daysLeft !== null ? `${daysLeft} days left` : 'TBA';
            if (daysLeft !== null) {
                if (daysLeft <= 0) {
                    badgeBg = '#ef4444'; // red
                    badgeText = 'CLOSED';
                } else if (daysLeft <= 7) {
                    badgeBg = '#ef4444'; // red
                } else if (daysLeft <= 15) {
                    badgeBg = '#eab308'; // yellow
                }
            }

            const formattedDeadline = formatDate(exam.last_date);
            
            const dateDisplay = `
                <div style="display: flex; flex-direction: column; gap: 4px;">
                    <span style="font-size: 0.9rem; font-weight: 500;">${formattedDeadline}</span>
                    <span class="days-left-badge" style="background-color: ${badgeBg}; color: #fff; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 600; width: fit-content; text-transform: uppercase; display: inline-flex; align-items: center; gap: 4px;">
                        <i class="fa-regular fa-clock" style="font-size: 0.65rem;"></i> ${badgeText}
                    </span>
                </div>
            `;

            const applyButton = (daysLeft !== null && daysLeft <= 0)
                ? ''
                : `<button class="btn btn-primary" onclick="triggerAutoApply('${exam.exam_name}', '${exam.portal_url}')">
                       <i class="fa-solid fa-bolt"></i> Auto Apply
                   </button>`;
            
            return `
                <div class="exam-card">
                    <div class="exam-card-header">
                        <span class="conducting-body">${exam.conducting_body}</span>
                        <h4 class="exam-name">${exam.exam_name}</h4>
                    </div>
                    
                    <div class="exam-card-meta">
                        <div class="meta-item">
                            <span class="meta-label">Fee Amount</span>
                            <span class="meta-value">${feeDisplay}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Last Date</span>
                            <span class="meta-value">${dateDisplay}</span>
                        </div>
                    </div>
                    
                    ${applyButton}
                </div>
            `;
        }).join('');
        
    } catch (err) {
        console.error("Dashboard load failed:", err);
    }
}

// 7. AUTO-APPLY MODAL & SSE REAL-TIME TRACKING
function triggerAutoApply(examId, portalUrl) {
    activePortalUrl = portalUrl || "https://upsconline.nic.in";
    let passphrase = sessionStorage.getItem('zk_passphrase');
    if (!passphrase) {
        passphrase = prompt("Your profile details vault is encrypted. Input your local cryptographic passphrase to release credentials to application worker:");
        if (!passphrase) {
            showToast("Application cancelled: decryption passphrase required to autofill form.", "error");
            return;
        }
        sessionStorage.setItem('zk_passphrase', passphrase);
    }
    
    // Show modal overlay
    document.getElementById('apply-monitor-modal').classList.add('active');
    document.getElementById('monitor-exam-title').innerText = `${examId} Auto Apply pipeline`;
    
    resetApplyMonitor();
    appendLogLine("[System] Submitting apply instruction to CEO Orchestrator...", "system");
    
    // Call POST /apply/{exam_id}
    startApplyTask(examId, passphrase);
}

function resetApplyMonitor() {
    // Reset steps rows
    document.querySelectorAll('.pipeline-steps-list .step-row').forEach(row => {
        row.className = "step-row";
    });
    
    // Reset consensus meter
    document.getElementById('monitor-consensus-fill').style.width = "0%";
    document.getElementById('monitor-qa-verdict').innerText = "Starting task...";
    document.getElementById('monitor-qa-verdict').style.color = "var(--text-secondary)";
    
    // Reset emulator viewport
    document.getElementById('monitor-emulator-url').innerText = "about:blank";
    document.getElementById('monitor-emulator-viewport').innerHTML = `
        <div class="emulator-inactive" id="emulator-status-box">
            <i class="fa-solid fa-circle-notch fa-spin"></i>
            <p>Spawning headless browser environment...</p>
        </div>
    `;
    
    // Clear terminal logs
    document.getElementById('monitor-terminal-logs').innerHTML = "";
}

function appendLogLine(message, styleClass = '') {
    const terminal = document.getElementById('monitor-terminal-logs');
    if (!terminal) return;
    
    const line = document.createElement('div');
    line.className = `terminal-line ${styleClass}`;
    
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    line.innerText = `[${time}] ${message}`;
    
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
}

async function startApplyTask(examId, passphrase) {
    try {
        const response = await fetch(`/apply/${encodeURIComponent(examId)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ passphrase: passphrase })
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "CEO Orchestrator rejected application schedule request");
        }
        
        activeTaskId = data.task_id;
        appendLogLine(`[Scheduled] Swarm pipeline active. Task ID: ${activeTaskId}`, 'success');
        
        // Spawn SSE progress event stream listener
        connectProgressSSE(activeTaskId);
    } catch (err) {
        appendLogLine(`[Error] Orchestration startup rejected: ${err.message}`, 'error');
        document.getElementById('emulator-status-box').innerHTML = `
            <i class="fa-solid fa-circle-xmark" style="color:var(--danger);"></i>
            <p style="color:var(--danger); font-weight:bold; margin-top:8px;">Failed to start: ${err.message}</p>
        `;
    }
}

function connectProgressSSE(taskId) {
    if (activeEventSource) {
        activeEventSource.close();
    }
    
    // Establish connection to GET /apply/status/{task_id} SSE
    activeEventSource = new EventSource(`/apply/status/${taskId}`);
    
    activeEventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleProgressEvent(data);
        } catch (err) {
            console.error("Failed to parse SSE streaming packet:", err);
        }
    };
    
    activeEventSource.onerror = (err) => {
        console.warn("SSE stream closed or disconnected:", err);
        activeEventSource.close();
        activeEventSource = null;
        appendLogLine("[System] Event stream connection closed.", "system");
    };
}

function handleProgressEvent(data) {
    const status = data.status;
    const message = data.message;
    
    let style = '';
    if (status === 'failed') style = 'error';
    else if (status === 'submitted') style = 'success';
    else if (status === 'payment_pending') style = 'warning';
    
    appendLogLine(`[${status.toUpperCase()}] ${message}`, style);
    
    // Update stepper visual indicators
    updateStepUI(status);
    
    // Specific handlers based on execution progress code
    if (status === 'payment_pending' && data.phonepay_url) {
        document.getElementById('monitor-emulator-url').innerText = "https://merchantsandbox.phonepe.com/pg";
        document.getElementById('monitor-emulator-viewport').innerHTML = `
            <div class="emulator-inactive" style="color:var(--warning); padding:20px;">
                <i class="fa-solid fa-credit-card" style="font-size:2rem; margin-bottom:12px;"></i>
                <p style="font-weight:bold; font-size:1.05rem; margin-bottom:12px;">PhonePe Payment Verification Needed</p>
                <a href="${data.phonepay_url}" target="_blank" class="btn btn-primary btn-sm">
                    <i class="fa-solid fa-external-link"></i> Complete Payment
                </a>
            </div>
        `;
    } else if (status === 'submitted') {
        const confNumber = data.confirmation_number || "CONF-SUCCESS";
        document.getElementById('monitor-emulator-viewport').innerHTML = `
            <div class="emulator-inactive" style="color:var(--success); padding:20px;">
                <i class="fa-solid fa-circle-check" style="font-size:2.4rem; margin-bottom:12px;"></i>
                <p style="font-weight:bold; font-size:1.15rem; margin-bottom:4px;">Application Submitted Successfully!</p>
                <p style="font-size:0.75rem; opacity:0.8;">Confirmation Reference: <strong>${confNumber}</strong></p>
            </div>
        `;
        if (activeEventSource) {
            activeEventSource.close();
        }
    } else if (status === 'failed') {
        document.getElementById('monitor-emulator-viewport').innerHTML = `
            <div class="emulator-inactive" style="color:var(--danger); padding:20px;">
                <i class="fa-solid fa-triangle-exclamation" style="font-size:2.4rem; margin-bottom:12px;"></i>
                <p style="font-weight:bold; font-size:1.15rem; margin-bottom:4px;">Submission Execution Failed</p>
                <p style="font-size:0.75rem; opacity:0.8;">${message}</p>
            </div>
        `;
        if (activeEventSource) {
            activeEventSource.close();
        }
    } else {
        // Map progressive status keys to portal pages to simulate web browsing using activePortalUrl
        const domain = activePortalUrl || "https://upsconline.nic.in";
        const baseDomain = domain.endsWith('/') ? domain.slice(0, -1) : domain;
        const urlMap = {
            initializing: "about:blank",
            creating_account: `${baseDomain}/otr/registration`,
            filling_profile: `${baseDomain}/otr/profile`,
            uploading_documents: `${baseDomain}/otr/documents`,
            processing_payment: `${baseDomain}/otr/payment`
        };
        if (urlMap[status]) {
            document.getElementById('monitor-emulator-url').innerText = urlMap[status];
            document.getElementById('monitor-emulator-viewport').innerHTML = `
                <div class="emulator-inactive" style="color:var(--accent);">
                    <i class="fa-solid fa-spinner fa-spin" style="font-size:2rem; margin-bottom:12px;"></i>
                    <p style="font-weight:500;">Stealth browser filling: <strong>${status.replace('_', ' ')}</strong></p>
                </div>
            `;
        }
    }
}

function updateStepUI(status) {
    const steps = ['initializing', 'creating_account', 'filling_profile', 'uploading_documents', 'processing_payment'];
    let currentIndex = steps.indexOf(status);
    
    if (status === 'submitted') currentIndex = 5;
    if (status === 'payment_pending') currentIndex = 4;
    
    // Update step rows classes
    steps.forEach((step, idx) => {
        const row = document.getElementById(`step-${step}`);
        if (!row) return;
        
        row.className = "step-row";
        
        if (status === 'failed' && idx === currentIndex) {
            row.classList.add('failed');
        } else if (idx < currentIndex || status === 'submitted') {
            row.classList.add('completed');
        } else if (idx === currentIndex) {
            row.classList.add('active');
        }
    });
    
    // Update progress consensus score fills
    const progressFill = document.getElementById('monitor-consensus-fill');
    const verdict = document.getElementById('monitor-qa-verdict');
    
    if (currentIndex >= 0) {
        const fillPercent = Math.min(100, (currentIndex + 1) * 20);
        progressFill.style.width = `${fillPercent}%`;
        
        if (status === 'failed') {
            verdict.innerText = "Audit Failure";
            verdict.style.color = "var(--danger)";
        } else if (status === 'submitted') {
            verdict.innerText = "Audit Passed";
            verdict.style.color = "var(--success)";
        } else {
            verdict.innerText = "Scanning page elements...";
            verdict.style.color = "var(--warning)";
        }
    }
}

function closeApplyMonitor() {
    document.getElementById('apply-monitor-modal').classList.remove('active');
    if (activeEventSource) {
        activeEventSource.close();
        activeEventSource = null;
    }
    loadDashboard();
}

// 8. APPLIED HISTORY CONTROLLER
async function loadApplied() {
    const tbody = document.getElementById('applied-table-body');
    tbody.innerHTML = `<tr><td colspan="5" class="table-empty">Loading applications list...</td></tr>`;
    
    try {
        const response = await fetch('/exams/applications', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!response.ok) throw new Error("Could not fetch submitted applications history list");
        
        const apps = await response.json();
        if (apps.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="table-empty">No active applications created yet.</td></tr>`;
            return;
        }
        
        tbody.innerHTML = apps.map(app => {
            const cleanDate = new Date(app.applied_at).toLocaleString('en-IN', {
                day: '2-digit', month: '2-digit', year: 'numeric',
                hour: '2-digit', minute: '2-digit'
            });
            
            return `
                <tr>
                    <td><strong>#${app.id}</strong></td>
                    <td>${app.exam_name}</td>
                    <td><a href="${app.portal_url}" target="_blank" style="color:var(--accent); text-decoration:none;"><i class="fa-solid fa-up-right-from-square"></i> Visit Site</a></td>
                    <td>${cleanDate}</td>
                    <td><span class="status-badge ${app.status}">${app.status}</span></td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="table-empty" style="color:var(--danger);">Error: ${err.message}</td></tr>`;
    }
}

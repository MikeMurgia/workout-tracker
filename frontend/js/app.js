// ============================================
// Workout Tracker Frontend Application
// ============================================

// API Base URL - change this if your API runs on a different port
const API_URL = 'http://localhost:3000';

// ============================================
// State Management
// ============================================
// Keep track of the current application state
const state = {
    exercises: [],           // All available exercises
    muscleGroups: [],        // List of muscle groups for filtering
    currentWorkout: null,    // The workout being logged (null if none)
    currentExercise: null,   // Currently selected exercise
    currentSets: [],         // Sets being entered for current exercise
    loggedExercises: []      // Exercises already logged in current workout
};

// ============================================
// Initialization
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    initializeEventListeners();
    loadExercises();
    setDefaultDate();
});

// Set today's date as default
function setDefaultDate() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('workout-date').value = today;
}

// ============================================
// Tab Navigation
// ============================================
function initializeTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active from all tabs
            tabs.forEach(t => t.classList.remove('active'));
            // Add active to clicked tab
            tab.classList.add('active');
            
            // Hide all tab content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Show selected tab content
            const tabId = tab.dataset.tab + '-tab';
            document.getElementById(tabId).classList.add('active');
            
            // Load data for the tab if needed
            if (tab.dataset.tab === 'history') {
                loadWorkoutHistory();
            } else if (tab.dataset.tab === 'stats') {
                loadStats();
            } else if (tab.dataset.tab === 'progress') {
                populateProgressExerciseSelect();
            }
        });
    });
}

// ============================================
// Event Listeners
// ============================================
function initializeEventListeners() {
    // New workout form
    document.getElementById('new-workout-form').addEventListener('submit', handleStartWorkout);
    
    // Exercise selection
    document.getElementById('exercise-select').addEventListener('change', handleExerciseSelect);
    document.getElementById('muscle-filter').addEventListener('change', handleMuscleFilter);
    
    // Set management
    document.getElementById('add-set-btn').addEventListener('click', addSetRow);
    document.getElementById('done-exercise-btn').addEventListener('click', handleDoneWithExercise);
    
    // Workout actions
    document.getElementById('finish-workout-btn').addEventListener('click', handleFinishWorkout);
    document.getElementById('cancel-workout-btn').addEventListener('click', handleCancelWorkout);
    
    // Exertion slider
    document.getElementById('perceived-exertion').addEventListener('input', (e) => {
        document.getElementById('exertion-value').textContent = e.target.value;
    });
    
    // History filters
    document.getElementById('filter-history-btn').addEventListener('click', loadWorkoutHistory);
    
    // Progress
    document.getElementById('load-progress-btn').addEventListener('click', loadExerciseProgress);
    
    // Stats
    document.getElementById('load-stats-btn').addEventListener('click', loadStats);
}

// ============================================
// API Helper Functions
// ============================================
async function apiGet(endpoint) {
    try {
        const response = await fetch(`${API_URL}${endpoint}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`API GET ${endpoint} failed:`, error);
        showToast('Failed to load data. Is the API running?', 'error');
        throw error;
    }
}

async function apiPost(endpoint, data) {
    try {
        const response = await fetch(`${API_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`API POST ${endpoint} failed:`, error);
        showToast('Failed to save data', 'error');
        throw error;
    }
}

async function apiPut(endpoint, data) {
    try {
        const response = await fetch(`${API_URL}${endpoint}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`API PUT ${endpoint} failed:`, error);
        showToast('Failed to update data', 'error');
        throw error;
    }
}

// ============================================
// Load Exercises
// ============================================
async function loadExercises() {
    try {
        const data = await apiGet('/exercises');
        state.exercises = data.exercises;
        
        // Get unique muscle groups
        const groups = await apiGet('/exercises/groups');
        state.muscleGroups = groups.groups;
        
        populateExerciseSelect();
        populateMuscleFilter();
    } catch (error) {
        console.error('Failed to load exercises:', error);
    }
}

function populateExerciseSelect(muscleGroup = '') {
    const select = document.getElementById('exercise-select');
    select.innerHTML = '<option value="">Select an exercise...</option>';
    
    let exercises = state.exercises;
    if (muscleGroup) {
        exercises = exercises.filter(e => e.muscle_group === muscleGroup);
    }
    
    exercises.forEach(exercise => {
        const option = document.createElement('option');
        option.value = exercise.id;
        option.textContent = `${exercise.name} (${exercise.muscle_group})`;
        option.dataset.name = exercise.name;
        select.appendChild(option);
    });
}

function populateMuscleFilter() {
    const select = document.getElementById('muscle-filter');
    select.innerHTML = '<option value="">All Muscles</option>';
    
    state.muscleGroups.forEach(group => {
        const option = document.createElement('option');
        option.value = group;
        option.textContent = group.charAt(0).toUpperCase() + group.slice(1);
        select.appendChild(option);
    });
}

function handleMuscleFilter(e) {
    populateExerciseSelect(e.target.value);
}

// ============================================
// Start Workout
// ============================================
async function handleStartWorkout(e) {
    e.preventDefault();
    
    const name = document.getElementById('workout-name').value;
    const date = document.getElementById('workout-date').value;
    
    try {
        const workout = await apiPost('/workouts', {
            name: name || null,
            workout_date: date
        });
        
        state.currentWorkout = workout;
        state.loggedExercises = [];
        
        // Update UI
        document.getElementById('active-workout-title').textContent = 
            workout.name || 'Workout';
        document.getElementById('active-workout-date').textContent = 
            new Date(workout.workout_date).toLocaleDateString();
        
        // Hide form, show workout logger
        document.querySelector('#log-tab .card').style.display = 'none';
        document.getElementById('active-workout').style.display = 'block';
        document.getElementById('logged-exercises-list').innerHTML = '';
        
        showToast('Workout started!', 'success');
    } catch (error) {
        console.error('Failed to start workout:', error);
    }
}

// ============================================
// Exercise Selection & Sets
// ============================================
function handleExerciseSelect(e) {
    const exerciseId = e.target.value;
    if (!exerciseId) {
        document.getElementById('current-exercise').style.display = 'none';
        return;
    }
    
    const exercise = state.exercises.find(ex => ex.id === exerciseId);
    state.currentExercise = exercise;
    state.currentSets = [];
    
    document.getElementById('current-exercise-name').textContent = exercise.name;
    document.getElementById('current-exercise').style.display = 'block';
    document.getElementById('sets-list').innerHTML = '';
    
    // Add first set row automatically
    addSetRow();
}

function addSetRow() {
    const setsList = document.getElementById('sets-list');
    const setNumber = setsList.children.length + 1;
    
    const row = document.createElement('div');
    row.className = 'set-row';
    row.innerHTML = `
        <span class="set-number">${setNumber}</span>
        <input type="number" class="set-weight" placeholder="lbs" step="2.5" min="0">
        <input type="number" class="set-reps" placeholder="reps" min="1" required>
        <select class="set-type">
            <option value="working">Working</option>
            <option value="warmup">Warmup</option>
            <option value="dropset">Dropset</option>
            <option value="failure">Failure</option>
        </select>
        <button type="button" class="remove-set-btn" onclick="removeSetRow(this)">×</button>
    `;
    
    setsList.appendChild(row);
}

function removeSetRow(btn) {
    const row = btn.closest('.set-row');
    row.remove();
    
    // Renumber remaining sets
    const rows = document.querySelectorAll('.set-row');
    rows.forEach((r, index) => {
        r.querySelector('.set-number').textContent = index + 1;
    });
}

async function handleDoneWithExercise() {
    const setRows = document.querySelectorAll('.set-row');
    const sets = [];
    
    setRows.forEach((row, index) => {
        const weight = row.querySelector('.set-weight').value;
        const reps = row.querySelector('.set-reps').value;
        const type = row.querySelector('.set-type').value;
        
        if (reps) {  // Only include sets with reps entered
            sets.push({
                exercise_id: state.currentExercise.id,
                set_number: index + 1,
                weight: weight ? parseFloat(weight) : null,
                reps: parseInt(reps),
                set_type: type
            });
        }
    });
    
    if (sets.length === 0) {
        showToast('Add at least one set with reps', 'error');
        return;
    }
    
    try {
        await apiPost(`/workouts/${state.currentWorkout.id}/sets`, { sets });
        
        // Add to logged exercises
        state.loggedExercises.push({
            name: state.currentExercise.name,
            sets: sets
        });
        
        updateLoggedExercisesList();
        
        // Reset for next exercise
        document.getElementById('exercise-select').value = '';
        document.getElementById('current-exercise').style.display = 'none';
        state.currentExercise = null;
        state.currentSets = [];
        
        showToast(`${sets.length} sets logged!`, 'success');
    } catch (error) {
        console.error('Failed to save sets:', error);
    }
}

function updateLoggedExercisesList() {
    const list = document.getElementById('logged-exercises-list');
    list.innerHTML = '';
    
    state.loggedExercises.forEach(exercise => {
        const div = document.createElement('div');
        div.className = 'logged-exercise';
        
        const setsText = exercise.sets.map(s => 
            `${s.weight || 'BW'}×${s.reps}`
        ).join(', ');
        
        div.innerHTML = `
            <div class="logged-exercise-header">
                <span class="logged-exercise-name">${exercise.name}</span>
            </div>
            <div class="logged-exercise-sets">${setsText}</div>
        `;
        
        list.appendChild(div);
    });
}

// ============================================
// Finish/Cancel Workout
// ============================================
async function handleFinishWorkout() {
    if (state.loggedExercises.length === 0) {
        showToast('Log at least one exercise first', 'error');
        return;
    }
    
    const exertion = document.getElementById('perceived-exertion').value;
    const notes = document.getElementById('workout-notes').value;
    
    try {
        await apiPut(`/workouts/${state.currentWorkout.id}`, {
            perceived_exertion: parseInt(exertion),
            notes: notes || null
        });
        
        showToast('Workout saved!', 'success');
        resetWorkoutLogger();
    } catch (error) {
        console.error('Failed to finish workout:', error);
    }
}

function handleCancelWorkout() {
    if (confirm('Are you sure you want to cancel this workout? All logged sets will be lost.')) {
        // In a real app, you might want to delete the workout from the database
        resetWorkoutLogger();
        showToast('Workout cancelled', 'info');
    }
}

function resetWorkoutLogger() {
    state.currentWorkout = null;
    state.currentExercise = null;
    state.currentSets = [];
    state.loggedExercises = [];
    
    document.getElementById('active-workout').style.display = 'none';
    document.querySelector('#log-tab .card').style.display = 'block';
    document.getElementById('new-workout-form').reset();
    document.getElementById('perceived-exertion').value = 5;
    document.getElementById('exertion-value').textContent = '5';
    setDefaultDate();
}

// ============================================
// Workout History
// ============================================
async function loadWorkoutHistory() {
    const fromDate = document.getElementById('history-from').value;
    const toDate = document.getElementById('history-to').value;
    
    let endpoint = '/workouts?limit=50';
    if (fromDate) endpoint += `&from=${fromDate}`;
    if (toDate) endpoint += `&to=${toDate}`;
    
    try {
        const data = await apiGet(endpoint);
        renderWorkoutHistory(data.workouts);
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

function renderWorkoutHistory(workouts) {
    const list = document.getElementById('workout-history-list');
    
    if (workouts.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <p>No workouts found</p>
            </div>
        `;
        return;
    }
    
    list.innerHTML = workouts.map(workout => `
        <div class="workout-history-item" onclick="toggleWorkoutDetail('${workout.id}', this)">
            <div class="workout-history-header">
                <span class="workout-history-name">${workout.name || 'Workout'}</span>
                <span class="workout-history-date">${new Date(workout.workout_date).toLocaleDateString()}</span>
            </div>
            <div class="workout-history-stats">
                <span>🏋️ ${workout.exercise_count || 0} exercises</span>
                <span>📊 ${workout.set_count || 0} sets</span>
                <span>💪 ${Math.round(workout.total_volume || 0).toLocaleString()} lbs volume</span>
            </div>
            <div class="workout-detail" id="detail-${workout.id}"></div>
        </div>
    `).join('');
}

async function toggleWorkoutDetail(workoutId, element) {
    const detailDiv = document.getElementById(`detail-${workoutId}`);
    
    if (detailDiv.classList.contains('expanded')) {
        detailDiv.classList.remove('expanded');
        return;
    }
    
    try {
        const workout = await apiGet(`/workouts/${workoutId}`);
        
        let html = '';
        workout.exercises.forEach(exercise => {
            const setsHtml = exercise.sets.map(s => 
                `<span>${s.weight || 'BW'}×${s.reps} (${s.set_type})</span>`
            ).join(' | ');
            
            html += `
                <div style="margin-bottom: 12px;">
                    <strong>${exercise.exercise_name}</strong>
                    <div style="color: var(--text-light); font-size: 0.9rem; margin-top: 4px;">
                        ${setsHtml}
                    </div>
                </div>
            `;
        });
        
        if (workout.notes) {
            html += `<div style="margin-top: 12px; font-style: italic;">Notes: ${workout.notes}</div>`;
        }
        
        detailDiv.innerHTML = html;
        detailDiv.classList.add('expanded');
    } catch (error) {
        console.error('Failed to load workout detail:', error);
    }
}

// ============================================
// Progress Tracking
// ============================================
function populateProgressExerciseSelect() {
    const select = document.getElementById('progress-exercise-select');
    select.innerHTML = '<option value="">Choose an exercise...</option>';
    
    state.exercises.forEach(exercise => {
        const option = document.createElement('option');
        option.value = exercise.id;
        option.textContent = `${exercise.name} (${exercise.muscle_group})`;
        select.appendChild(option);
    });
}

async function loadExerciseProgress() {
    const exerciseId = document.getElementById('progress-exercise-select').value;
    const days = document.getElementById('progress-days').value;
    
    if (!exerciseId) {
        showToast('Select an exercise first', 'error');
        return;
    }
    
    try {
        const data = await apiGet(`/stats/progress/${exerciseId}?days=${days}`);
        renderProgress(data);
    } catch (error) {
        console.error('Failed to load progress:', error);
    }
}

function renderProgress(data) {
    const container = document.getElementById('progress-chart-container');
    container.style.display = 'block';
    
    document.getElementById('progress-exercise-title').textContent = data.exercise_name;
    
    // Render stats
    const statsHtml = data.progress.length > 0 ? `
        <div class="stat-card">
            <div class="stat-value">${data.progress.length}</div>
            <div class="stat-label">Sessions</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${Math.max(...data.progress.map(p => p.max_weight || 0))}</div>
            <div class="stat-label">Max Weight</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${Math.max(...data.progress.map(p => p.estimated_1rm || 0))}</div>
            <div class="stat-label">Est. 1RM</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${Math.round(data.progress.reduce((sum, p) => sum + (parseFloat(p.total_volume) || 0), 0)).toLocaleString()}</div>
            <div class="stat-label">Total Volume</div>
        </div>
    ` : '<p>No data available for this period</p>';
    
    document.getElementById('progress-stats').innerHTML = statsHtml;
    
    // Render chart
    if (data.progress.length > 0) {
        renderProgressChart(data.progress);
    }
    
    // Render data table
    const tableHtml = data.progress.length > 0 ? `
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead>
                <tr style="border-bottom: 2px solid var(--border-color);">
                    <th style="text-align: left; padding: 8px;">Date</th>
                    <th style="text-align: right; padding: 8px;">Max Weight</th>
                    <th style="text-align: right; padding: 8px;">Reps</th>
                    <th style="text-align: right; padding: 8px;">Est. 1RM</th>
                    <th style="text-align: right; padding: 8px;">Volume</th>
                </tr>
            </thead>
            <tbody>
                ${data.progress.map(p => `
                    <tr style="border-bottom: 1px solid var(--border-color);">
                        <td style="padding: 8px;">${new Date(p.workout_date).toLocaleDateString()}</td>
                        <td style="text-align: right; padding: 8px;">${p.max_weight || '-'}</td>
                        <td style="text-align: right; padding: 8px;">${p.reps_at_max_weight || '-'}</td>
                        <td style="text-align: right; padding: 8px;">${p.estimated_1rm || '-'}</td>
                        <td style="text-align: right; padding: 8px;">${Math.round(p.total_volume || 0).toLocaleString()}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    ` : '';
    
    document.getElementById('progress-data-table').innerHTML = tableHtml;
}

let progressChart = null;

function renderProgressChart(progress) {
    const ctx = document.getElementById('progress-chart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (progressChart) {
        progressChart.destroy();
    }
    
    progressChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: progress.map(p => new Date(p.workout_date).toLocaleDateString()),
            datasets: [
                {
                    label: 'Max Weight',
                    data: progress.map(p => p.max_weight),
                    borderColor: '#4f46e5',
                    backgroundColor: 'rgba(79, 70, 229, 0.1)',
                    tension: 0.1,
                    yAxisID: 'y'
                },
                {
                    label: 'Estimated 1RM',
                    data: progress.map(p => p.estimated_1rm),
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.1,
                    yAxisID: 'y'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Weight (lbs)'
                    }
                }
            }
        }
    });
}

// ============================================
// Stats
// ============================================
async function loadStats() {
    const days = document.getElementById('stats-days').value;
    
    try {
        const [summary, prs] = await Promise.all([
            apiGet(`/stats/summary?days=${days}`),
            apiGet('/stats/prs')
        ]);
        
        renderStatsSummary(summary);
        renderPersonalRecords(prs);
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

function renderStatsSummary(data) {
    document.getElementById('stats-summary').innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${data.workouts}</div>
            <div class="stat-label">Workouts</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.total_sets}</div>
            <div class="stat-label">Total Sets</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.total_reps}</div>
            <div class="stat-label">Total Reps</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${Math.round(data.total_volume).toLocaleString()}</div>
            <div class="stat-label">Total Volume (lbs)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.unique_exercises}</div>
            <div class="stat-label">Exercises Used</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.avg_rpe || '-'}</div>
            <div class="stat-label">Avg RPE</div>
        </div>
    `;
    
    // Muscle group breakdown
    document.getElementById('muscle-group-stats').innerHTML = data.muscle_group_breakdown
        .map(mg => `
            <div class="muscle-stat">
                <span class="muscle-name">${mg.muscle_group}</span>
                <span class="muscle-volume">${mg.sets} sets | ${Math.round(mg.volume).toLocaleString()} lbs</span>
            </div>
        `).join('');
}

function renderPersonalRecords(data) {
    const container = document.getElementById('personal-records');
    
    if (data.personal_records.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No personal records yet. Start logging workouts!</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = data.personal_records.map(pr => {
        const records = Object.entries(pr.records).map(([type, record]) => 
            `<span class="pr-record">${type}: ${record.value}</span>`
        ).join('');
        
        return `
            <div class="pr-item">
                <div class="pr-exercise">${pr.exercise_name}</div>
                <div class="pr-records">${records}</div>
            </div>
        `;
    }).join('');
}

// ============================================
// Toast Notifications
// ============================================
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
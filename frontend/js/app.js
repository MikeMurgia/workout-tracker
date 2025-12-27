// ============================================
// Workout Tracker Frontend Application
// ============================================

// API Base URLs
const API_URL = 'http://localhost:3000';
const ANALYTICS_URL = 'http://localhost:8000';

// ============================================
// State Management
// ============================================
const state = {
    exercises: [],
    muscleGroups: [],
    currentWorkout: null,
    currentExercise: null,
    currentSets: [],
    loggedExercises: [],
    selectedProgressExercise: null,
    confirmCallback: null
};

// ============================================
// Initialization
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    initializeEventListeners();
    loadExercises();
    setDefaultDate();
    loadWorkoutRecommendation();
});

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
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            const tabId = tab.dataset.tab + '-tab';
            document.getElementById(tabId).classList.add('active');
            
            if (tab.dataset.tab === 'history') {
                loadWorkoutHistory();
            } else if (tab.dataset.tab === 'stats') {
                loadStats();
            } else if (tab.dataset.tab === 'progress') {
                populateProgressExerciseSelect();
            } else if (tab.dataset.tab === 'exercises') {
                loadExerciseList();
            }
        });
    });
}

// ============================================
// Event Listeners
// ============================================
function initializeEventListeners() {
    // Workout logging
    document.getElementById('new-workout-form').addEventListener('submit', handleStartWorkout);
    document.getElementById('exercise-select').addEventListener('change', handleExerciseSelect);
    document.getElementById('muscle-filter').addEventListener('change', handleMuscleFilter);
    document.getElementById('add-set-btn').addEventListener('click', addSetRow);
    document.getElementById('done-exercise-btn').addEventListener('click', handleDoneWithExercise);
    document.getElementById('finish-workout-btn').addEventListener('click', handleFinishWorkout);
    document.getElementById('cancel-workout-btn').addEventListener('click', handleCancelWorkout);
    document.getElementById('perceived-exertion').addEventListener('input', (e) => {
        document.getElementById('exertion-value').textContent = e.target.value;
    });
    
    // History
    document.getElementById('filter-history-btn').addEventListener('click', loadWorkoutHistory);
    
    // Progress
    document.getElementById('load-progress-btn').addEventListener('click', loadExerciseProgress);
    document.getElementById('predict-goal-btn').addEventListener('click', predictGoal);
    
    // Stats
    document.getElementById('load-stats-btn').addEventListener('click', loadStats);
    
    // Recommendation
    const dismissBtn = document.getElementById('dismiss-recommendation');
    if (dismissBtn) {
        dismissBtn.addEventListener('click', () => {
            document.getElementById('workout-recommendation-banner').style.display = 'none';
        });
    }
    
    // AI Insights
    document.getElementById('load-health-score-btn').addEventListener('click', loadHealthScore);
    document.getElementById('load-balance-btn').addEventListener('click', loadTrainingBalance);
    document.getElementById('load-anomalies-btn').addEventListener('click', loadAnomalies);
    document.getElementById('check-deload-btn').addEventListener('click', checkDeload);
    document.getElementById('calculate-1rm-btn').addEventListener('click', calculate1RM);
    
    // Exercise management
    document.getElementById('add-exercise-form').addEventListener('submit', handleAddExercise);
    document.getElementById('edit-exercise-form').addEventListener('submit', handleEditExercise);
    document.getElementById('exercise-list-filter').addEventListener('change', loadExerciseList);
}

// ============================================
// API Helpers
// ============================================
async function apiGet(endpoint, baseUrl = API_URL) {
    const response = await fetch(`${baseUrl}${endpoint}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

async function apiPost(endpoint, data, baseUrl = API_URL) {
    const response = await fetch(`${baseUrl}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

async function apiPut(endpoint, data, baseUrl = API_URL) {
    const response = await fetch(`${baseUrl}${endpoint}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

async function apiDelete(endpoint, baseUrl = API_URL) {
    const response = await fetch(`${baseUrl}${endpoint}`, { method: 'DELETE' });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || `HTTP error! status: ${response.status}`);
    }
    return await response.json();
}

// ============================================
// Load Exercises
// ============================================
async function loadExercises() {
    try {
        const data = await apiGet('/exercises');
        state.exercises = data.exercises;
        
        const groups = await apiGet('/exercises/groups');
        state.muscleGroups = groups.groups;
        
        populateExerciseSelect();
        populateMuscleFilter();
    } catch (error) {
        showToast('Failed to load exercises', 'error');
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
// Workout Recommendation
// ============================================
async function loadWorkoutRecommendation() {
    try {
        const data = await apiGet('/recommendations/next-workout', ANALYTICS_URL);
        
        if (data.recommendation && data.recommendation !== 'rest_or_light') {
            const banner = document.getElementById('workout-recommendation-banner');
            const content = document.getElementById('recommendation-content');
            
            let html = `<p>${data.reason || 'Based on your recent training'}</p>`;
            
            if (data.suggested_muscles && data.suggested_muscles.length > 0) {
                html += '<p><strong>Focus on:</strong> ' + 
                    data.suggested_muscles.map(m => m.charAt(0).toUpperCase() + m.slice(1)).join(', ') + '</p>';
            }
            
            content.innerHTML = html;
            banner.style.display = 'block';
        }
    } catch (error) {
        console.log('Could not load workout recommendation');
    }
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
        
        document.getElementById('active-workout-title').textContent = workout.name || 'Workout';
        document.getElementById('active-workout-date').textContent = new Date(workout.workout_date).toLocaleDateString();
        
        document.querySelector('#log-tab .card').style.display = 'none';
        document.getElementById('workout-recommendation-banner').style.display = 'none';
        document.getElementById('active-workout').style.display = 'block';
        document.getElementById('logged-exercises-list').innerHTML = '';
        
        showToast('Workout started!', 'success');
    } catch (error) {
        showToast('Failed to start workout', 'error');
    }
}

// ============================================
// Exercise Selection & Sets
// ============================================
async function handleExerciseSelect(e) {
    const exerciseId = e.target.value;
    if (!exerciseId) {
        document.getElementById('current-exercise').style.display = 'none';
        return;
    }
    
    const exercise = state.exercises.find(ex => ex.id === exerciseId);
    state.currentExercise = exercise;
    
    document.getElementById('current-exercise-name').textContent = exercise.name;
    document.getElementById('current-exercise').style.display = 'block';
    document.getElementById('sets-list').innerHTML = '';
    
    addSetRow();
    loadExercisePrediction(exerciseId);
}

async function loadExercisePrediction(exerciseId) {
    const predictionBox = document.getElementById('exercise-prediction');
    const predictionText = document.getElementById('exercise-prediction-text');
    
    try {
        const data = await apiGet(`/predictions/strength/${exerciseId}?days_ahead=7`, ANALYTICS_URL);
        
        if (data.predictions && data.predictions.length > 0) {
            predictionText.textContent = `Expected 1RM: ${data.predictions[0].predicted_1rm} lbs (Current: ${data.current_estimated_1rm} lbs)`;
            predictionBox.style.display = 'flex';
        } else {
            predictionBox.style.display = 'none';
        }
    } catch (error) {
        predictionBox.style.display = 'none';
    }
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
    btn.closest('.set-row').remove();
    document.querySelectorAll('.set-row').forEach((r, i) => {
        r.querySelector('.set-number').textContent = i + 1;
    });
}

async function handleDoneWithExercise() {
    const setRows = document.querySelectorAll('.set-row');
    const sets = [];
    
    setRows.forEach((row, index) => {
        const weight = row.querySelector('.set-weight').value;
        const reps = row.querySelector('.set-reps').value;
        const type = row.querySelector('.set-type').value;
        
        if (reps) {
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
        
        state.loggedExercises.push({ name: state.currentExercise.name, sets });
        updateLoggedExercisesList();
        
        document.getElementById('exercise-select').value = '';
        document.getElementById('current-exercise').style.display = 'none';
        document.getElementById('exercise-prediction').style.display = 'none';
        state.currentExercise = null;
        
        showToast(`${sets.length} sets logged!`, 'success');
    } catch (error) {
        showToast('Failed to save sets', 'error');
    }
}

function updateLoggedExercisesList() {
    const list = document.getElementById('logged-exercises-list');
    list.innerHTML = state.loggedExercises.map(exercise => `
        <div class="logged-exercise">
            <div class="logged-exercise-header">
                <span class="logged-exercise-name">${exercise.name}</span>
            </div>
            <div class="logged-exercise-sets">${exercise.sets.map(s => `${s.weight || 'BW'}×${s.reps}`).join(', ')}</div>
        </div>
    `).join('');
}

// ============================================
// Finish/Cancel Workout
// ============================================
async function handleFinishWorkout() {
    if (state.loggedExercises.length === 0) {
        showToast('Log at least one exercise first', 'error');
        return;
    }
    
    try {
        await apiPut(`/workouts/${state.currentWorkout.id}`, {
            perceived_exertion: parseInt(document.getElementById('perceived-exertion').value),
            notes: document.getElementById('workout-notes').value || null
        });
        
        showToast('Workout saved!', 'success');
        resetWorkoutLogger();
    } catch (error) {
        showToast('Failed to finish workout', 'error');
    }
}

function handleCancelWorkout() {
    if (confirm('Are you sure you want to cancel this workout?')) {
        resetWorkoutLogger();
        showToast('Workout cancelled', 'info');
    }
}

function resetWorkoutLogger() {
    state.currentWorkout = null;
    state.currentExercise = null;
    state.loggedExercises = [];
    
    document.getElementById('active-workout').style.display = 'none';
    document.querySelector('#log-tab .card').style.display = 'block';
    document.getElementById('new-workout-form').reset();
    document.getElementById('perceived-exertion').value = 5;
    document.getElementById('exertion-value').textContent = '5';
    setDefaultDate();
    loadWorkoutRecommendation();
}

// ============================================
// Workout History
// ============================================
async function loadWorkoutHistory() {
    const fromDate = document.getElementById('history-from').value;
    const toDate = document.getElementById('history-to').value;
    
    let endpoint = '/workouts?limit=100';
    if (fromDate) endpoint += `&from=${fromDate}`;
    if (toDate) endpoint += `&to=${toDate}`;
    
    try {
        const data = await apiGet(endpoint);
        renderWorkoutHistory(data.workouts);
    } catch (error) {
        showToast('Failed to load history', 'error');
    }
}

function renderWorkoutHistory(workouts) {
    const list = document.getElementById('workout-history-list');
    
    if (workouts.length === 0) {
        list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div><p>No workouts found</p></div>';
        return;
    }
    
    list.innerHTML = workouts.map(workout => `
        <div class="workout-history-item" onclick="toggleWorkoutDetail('${workout.id}', event)">
            <button class="workout-delete-btn" onclick="deleteWorkout('${workout.id}', event)">🗑️ Delete</button>
            <div class="workout-history-header">
                <span class="workout-history-name">${workout.name || 'Workout'}</span>
                <span class="workout-history-date">${new Date(workout.workout_date).toLocaleDateString()}</span>
            </div>
            <div class="workout-history-stats">
                <span>🏋️ ${workout.exercise_count || 0} exercises</span>
                <span>📊 ${workout.set_count || 0} sets</span>
                <span>💪 ${Math.round(workout.total_volume || 0).toLocaleString()} lbs</span>
            </div>
            <div class="workout-detail" id="detail-${workout.id}"></div>
        </div>
    `).join('');
}

async function deleteWorkout(workoutId, event) {
    event.stopPropagation();
    
    showConfirmModal(
        'Delete Workout',
        'Are you sure you want to delete this workout? This cannot be undone.',
        async () => {
            try {
                await apiDelete(`/workouts/${workoutId}`);
                showToast('Workout deleted', 'success');
                loadWorkoutHistory();
            } catch (error) {
                showToast('Failed to delete workout', 'error');
            }
        }
    );
}

async function toggleWorkoutDetail(workoutId, event) {
    if (event.target.classList.contains('workout-delete-btn')) return;
    
    const detailDiv = document.getElementById(`detail-${workoutId}`);
    
    if (detailDiv.classList.contains('expanded')) {
        detailDiv.classList.remove('expanded');
        return;
    }
    
    try {
        const workout = await apiGet(`/workouts/${workoutId}`);
        
        let html = workout.exercises.map(exercise => `
            <div style="margin-bottom: 12px;">
                <strong>${exercise.exercise_name}</strong>
                <div style="color: var(--text-light); font-size: 0.9rem; margin-top: 4px;">
                    ${exercise.sets.map(s => `${s.weight || 'BW'}×${s.reps}`).join(' | ')}
                </div>
            </div>
        `).join('');
        
        if (workout.notes) {
            html += `<div style="margin-top: 12px; font-style: italic;">Notes: ${workout.notes}</div>`;
        }
        
        detailDiv.innerHTML = html;
        detailDiv.classList.add('expanded');
    } catch (error) {
        showToast('Failed to load workout details', 'error');
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
    
    state.selectedProgressExercise = exerciseId;
    
    try {
        const data = await apiGet(`/stats/progress/${exerciseId}?days=${days}`);
        renderProgress(data);
        loadStrengthPrediction(exerciseId);
    } catch (error) {
        showToast('Failed to load progress', 'error');
    }
}

function renderProgress(data) {
    const container = document.getElementById('progress-chart-container');
    container.style.display = 'block';
    
    document.getElementById('progress-exercise-title').textContent = data.exercise_name;
    
    if (data.progress.length > 0) {
        document.getElementById('progress-stats').innerHTML = `
            <div class="stat-card"><div class="stat-value">${data.progress.length}</div><div class="stat-label">Sessions</div></div>
            <div class="stat-card"><div class="stat-value">${Math.max(...data.progress.map(p => p.max_weight || 0))}</div><div class="stat-label">Max Weight</div></div>
            <div class="stat-card"><div class="stat-value">${Math.max(...data.progress.map(p => p.estimated_1rm || 0))}</div><div class="stat-label">Est. 1RM</div></div>
            <div class="stat-card"><div class="stat-value">${Math.round(data.progress.reduce((sum, p) => sum + (parseFloat(p.total_volume) || 0), 0)).toLocaleString()}</div><div class="stat-label">Total Volume</div></div>
        `;
        renderProgressChart(data.progress);
    } else {
        document.getElementById('progress-stats').innerHTML = '<p class="no-data">No data available for this period</p>';
    }
}

let progressChart = null;

function renderProgressChart(progress) {
    const ctx = document.getElementById('progress-chart').getContext('2d');
    if (progressChart) progressChart.destroy();
    
    progressChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: progress.map(p => new Date(p.workout_date).toLocaleDateString()),
            datasets: [
                { label: 'Max Weight', data: progress.map(p => p.max_weight), borderColor: '#4f46e5', tension: 0.1 },
                { label: 'Estimated 1RM', data: progress.map(p => p.estimated_1rm), borderColor: '#10b981', tension: 0.1 }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

async function loadStrengthPrediction(exerciseId) {
    const container = document.getElementById('strength-prediction-content');
    container.innerHTML = '<div class="loading"><span class="loading-spinner"></span>Loading predictions...</div>';
    
    try {
        const data = await apiGet(`/predictions/strength/${exerciseId}?days_ahead=30`, ANALYTICS_URL);
        
        container.innerHTML = `
            <div class="progress-stats">
                <div class="stat-card"><div class="stat-value">${data.current_estimated_1rm}</div><div class="stat-label">Current 1RM</div></div>
                <div class="stat-card"><div class="stat-value">${data.predictions[data.predictions.length - 1]?.predicted_1rm || '-'}</div><div class="stat-label">Predicted (30 days)</div></div>
                <div class="stat-card"><div class="stat-value">${data.model_metrics.r_squared}</div><div class="stat-label">Model R²</div></div>
            </div>
        `;
        renderPredictionChart(data);
    } catch (error) {
        container.innerHTML = '<p class="no-data">Need at least 3 workout sessions for predictions</p>';
    }
}

let predictionChart = null;

function renderPredictionChart(data) {
    const container = document.getElementById('prediction-chart-container');
    container.style.display = 'block';
    
    const ctx = document.getElementById('prediction-chart').getContext('2d');
    if (predictionChart) predictionChart.destroy();
    
    predictionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.predictions.map(p => p.date),
            datasets: [{
                label: 'Predicted 1RM',
                data: data.predictions.map(p => p.predicted_1rm),
                borderColor: '#8b5cf6',
                borderDash: [5, 5],
                tension: 0.1,
                fill: true,
                backgroundColor: 'rgba(139, 92, 246, 0.1)'
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

async function predictGoal() {
    const targetWeight = document.getElementById('goal-weight').value;
    const exerciseId = state.selectedProgressExercise;
    
    if (!exerciseId) return showToast('Load progress for an exercise first', 'error');
    if (!targetWeight) return showToast('Enter a target weight', 'error');
    
    const resultDiv = document.getElementById('goal-prediction-result');
    resultDiv.innerHTML = '<div class="loading"><span class="loading-spinner"></span>Calculating...</div>';
    
    try {
        const data = await apiGet(`/predictions/goal/${exerciseId}?target_weight=${targetWeight}`, ANALYTICS_URL);
        const p = data.prediction;
        
        if (p.status === 'already_achieved') {
            resultDiv.innerHTML = `<div class="deload-result no-deload"><div class="deload-icon">🎉</div><div class="deload-title">Already Achieved!</div><div class="deload-message">${p.message}</div></div>`;
        } else if (p.status === 'achievable') {
            resultDiv.innerHTML = `<div class="deload-result no-deload"><div class="deload-icon">🎯</div><div class="deload-title">${p.predicted_date}</div><div class="deload-message">~${p.days_from_now} days (${p.sessions_needed} sessions)</div></div>`;
        } else {
            resultDiv.innerHTML = `<div class="deload-result needs-deload"><div class="deload-icon">📅</div><div class="deload-title">Long Term Goal</div><div class="deload-message">${p.message || 'Need more data'}</div></div>`;
        }
    } catch (error) {
        resultDiv.innerHTML = '<p class="no-data">Could not calculate goal prediction</p>';
    }
}

// ============================================
// Health Score
// ============================================
async function loadHealthScore() {
    const days = document.getElementById('health-days').value;
    const resultDiv = document.getElementById('health-score-result');
    const btn = document.getElementById('load-health-score-btn');
    
    btn.innerHTML = '<span class="loading-spinner"></span>Analyzing...';
    btn.disabled = true;
    
    try {
        const data = await apiGet(`/analysis/health?days=${days}`, ANALYTICS_URL);
        resultDiv.style.display = 'block';
        
        if (data.score === null) {
            document.getElementById('health-score-number').textContent = '--';
            document.getElementById('health-score-rating').textContent = data.message;
            document.getElementById('health-score-breakdown').innerHTML = '';
            document.getElementById('health-recommendations').innerHTML = `<h4>💡 Recommendation</h4><p>${data.recommendation || 'Keep training to build enough data.'}</p>`;
        } else {
            document.getElementById('health-score-circle').className = 'score-circle ' + data.rating.toLowerCase().replace(' ', '-');
            document.getElementById('health-score-number').textContent = data.score;
            document.getElementById('health-score-rating').textContent = data.rating;
            
            const b = data.breakdown;
            document.getElementById('health-score-breakdown').innerHTML = `
                <div class="breakdown-item"><div class="breakdown-label">Consistency</div><div class="breakdown-value">${b.consistency}/25</div></div>
                <div class="breakdown-item"><div class="breakdown-label">Progress</div><div class="breakdown-value">${b.progress}/25</div></div>
                <div class="breakdown-item"><div class="breakdown-label">Volume</div><div class="breakdown-value">${b.volume}/25</div></div>
                <div class="breakdown-item"><div class="breakdown-label">Recovery</div><div class="breakdown-value">${b.recovery}/25</div></div>
            `;
            
            document.getElementById('health-recommendations').innerHTML = `<h4>💡 Recommendations</h4><ul class="recommendation-list">${data.recommendations.map(r => `<li>${r}</li>`).join('')}</ul>`;
        }
    } catch (error) {
        resultDiv.innerHTML = '<p class="no-data">Failed to load health score</p>';
        resultDiv.style.display = 'block';
    } finally {
        btn.innerHTML = 'Analyze My Training';
        btn.disabled = false;
    }
}

// ============================================
// Training Balance
// ============================================
let balanceChart = null;

async function loadTrainingBalance() {
    const days = document.getElementById('balance-days').value;
    const resultDiv = document.getElementById('balance-result');
    
    resultDiv.innerHTML = '<div class="loading"><span class="loading-spinner"></span>Analyzing...</div>';
    
    try {
        const data = await apiGet(`/recommendations/balance?days=${days}`, ANALYTICS_URL);
        
        if (data.message) {
            resultDiv.innerHTML = `<p class="no-data">${data.message}</p>`;
            return;
        }
        
        let html = `<div class="balance-score"><div class="balance-score-value">${data.overall_balance.score}/100</div><div class="balance-score-label">${data.overall_balance.rating} Balance</div></div><div class="balance-grid">`;
        
        for (const [muscle, info] of Object.entries(data.muscle_groups)) {
            html += `<div class="balance-item"><div><div class="balance-muscle">${muscle}</div><div class="balance-sets">${info.sets} sets (target: ${info.target_range})</div></div><span class="balance-status ${info.status}">${info.status}</span></div>`;
        }
        
        resultDiv.innerHTML = html + '</div>';
        renderBalanceChart(data.muscle_groups);
    } catch (error) {
        resultDiv.innerHTML = '<p class="no-data">Failed to load training balance</p>';
    }
}

function renderBalanceChart(muscleGroups) {
    document.getElementById('balance-chart-container').style.display = 'block';
    const ctx = document.getElementById('balance-chart').getContext('2d');
    if (balanceChart) balanceChart.destroy();
    
    balanceChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: Object.keys(muscleGroups).map(l => l.charAt(0).toUpperCase() + l.slice(1)),
            datasets: [{
                label: 'Sets per Week',
                data: Object.values(muscleGroups).map(m => m.sets),
                backgroundColor: 'rgba(79, 70, 229, 0.2)',
                borderColor: '#4f46e5'
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { r: { beginAtZero: true } } }
    });
}

// ============================================
// Anomaly Detection
// ============================================
async function loadAnomalies() {
    const resultDiv = document.getElementById('anomalies-result');
    const btn = document.getElementById('load-anomalies-btn');
    
    btn.innerHTML = '<span class="loading-spinner"></span>Scanning...';
    btn.disabled = true;
    
    try {
        const data = await apiGet('/analysis/anomalies?days=30', ANALYTICS_URL);
        
        if (data.anomalies.length === 0) {
            resultDiv.innerHTML = '<div class="no-data"><div class="no-data-icon">✅</div><p>No anomalies detected!</p></div>';
        } else {
            resultDiv.innerHTML = `<p>${data.anomalies.length} anomalies found</p><div class="anomaly-list">${data.anomalies.map(a => `
                <div class="anomaly-item ${a.severity}">
                    <div class="anomaly-header"><span class="anomaly-type">${a.type.replace(/_/g, ' ')}</span><span class="anomaly-date">${a.date}</span></div>
                    <div class="anomaly-message">${a.message}</div>
                </div>
            `).join('')}</div>`;
        }
    } catch (error) {
        resultDiv.innerHTML = '<p class="no-data">Failed to scan for anomalies</p>';
    } finally {
        btn.innerHTML = 'Scan for Anomalies';
        btn.disabled = false;
    }
}

// ============================================
// Deload Check
// ============================================
async function checkDeload() {
    const resultDiv = document.getElementById('deload-result');
    const btn = document.getElementById('check-deload-btn');
    
    btn.innerHTML = '<span class="loading-spinner"></span>Checking...';
    btn.disabled = true;
    
    try {
        const data = await apiGet('/recommendations/deload', ANALYTICS_URL);
        
        if (data.needs_deload) {
            resultDiv.innerHTML = `<div class="deload-result needs-deload"><div class="deload-icon">😴</div><div class="deload-title">Deload Recommended</div><div class="deload-message">${data.reason}</div></div>`;
        } else {
            resultDiv.innerHTML = `<div class="deload-result no-deload"><div class="deload-icon">💪</div><div class="deload-title">Keep Training!</div><div class="deload-message">${data.reason || data.suggestion || 'No deload needed.'}</div></div>`;
        }
    } catch (error) {
        resultDiv.innerHTML = '<p class="no-data">Failed to check recovery status</p>';
    } finally {
        btn.innerHTML = 'Check Recovery Status';
        btn.disabled = false;
    }
}

// ============================================
// 1RM Calculator
// ============================================
async function calculate1RM() {
    const weight = document.getElementById('calc-weight').value;
    const reps = document.getElementById('calc-reps').value;
    
    if (!weight || !reps) return showToast('Enter weight and reps', 'error');
    
    try {
        const data = await apiGet(`/predictions/1rm/calculate?weight=${weight}&reps=${reps}`, ANALYTICS_URL);
        
        document.getElementById('orm-result').innerHTML = `
            <div class="orm-result">
                <div class="orm-main-result">${data.estimated_1rm} lbs</div>
                <div class="orm-label">Estimated 1 Rep Max</div>
                <div class="orm-formulas">${Object.entries(data.all_formulas).map(([name, value]) => `
                    <div class="orm-formula"><div class="orm-formula-value">${value}</div><div class="orm-formula-name">${name}</div></div>
                `).join('')}</div>
            </div>
        `;
    } catch (error) {
        document.getElementById('orm-result').innerHTML = '<p class="no-data">Failed to calculate 1RM</p>';
    }
}

// ============================================
// Exercise Management
// ============================================
async function loadExerciseList() {
    const filter = document.getElementById('exercise-list-filter').value;
    const list = document.getElementById('exercise-list');
    
    try {
        let endpoint = '/exercises';
        if (filter) endpoint += `?muscle_group=${filter}`;
        
        const data = await apiGet(endpoint);
        
        list.innerHTML = data.exercises.map(ex => `
            <div class="exercise-list-item">
                <div class="exercise-info">
                    <div class="exercise-info-name">${ex.name}</div>
                    <div class="exercise-info-details">${ex.muscle_group} • ${ex.equipment || 'N/A'} • ${ex.is_compound ? 'Compound' : 'Isolation'}</div>
                </div>
                <div class="exercise-actions">
                    <button class="btn-icon edit" onclick="openEditExerciseModal('${ex.id}', '${ex.name.replace(/'/g, "\\'")}', '${ex.muscle_group}', '${ex.equipment || ''}', ${ex.is_compound})">✏️</button>
                    <button class="btn-icon delete" onclick="deleteExercise('${ex.id}', '${ex.name.replace(/'/g, "\\'")}')">🗑️</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        list.innerHTML = '<p class="no-data">Failed to load exercises</p>';
    }
}

async function handleAddExercise(e) {
    e.preventDefault();
    
    const data = {
        name: document.getElementById('new-exercise-name').value,
        muscle_group: document.getElementById('new-exercise-muscle').value,
        equipment: document.getElementById('new-exercise-equipment').value || null,
        is_compound: document.getElementById('new-exercise-compound').value === 'true'
    };
    
    try {
        await apiPost('/exercises', data);
        showToast('Exercise added!', 'success');
        document.getElementById('add-exercise-form').reset();
        loadExercises();
        loadExerciseList();
    } catch (error) {
        showToast('Failed to add exercise', 'error');
    }
}

function openEditExerciseModal(id, name, muscle, equipment, compound) {
    document.getElementById('edit-exercise-id').value = id;
    document.getElementById('edit-exercise-name').value = name;
    document.getElementById('edit-exercise-muscle').value = muscle;
    document.getElementById('edit-exercise-equipment').value = equipment || '';
    document.getElementById('edit-exercise-compound').value = compound.toString();
    document.getElementById('edit-exercise-modal').style.display = 'flex';
}

function closeEditExerciseModal() {
    document.getElementById('edit-exercise-modal').style.display = 'none';
}

async function handleEditExercise(e) {
    e.preventDefault();
    
    const id = document.getElementById('edit-exercise-id').value;
    const data = {
        name: document.getElementById('edit-exercise-name').value,
        muscle_group: document.getElementById('edit-exercise-muscle').value,
        equipment: document.getElementById('edit-exercise-equipment').value || null,
        is_compound: document.getElementById('edit-exercise-compound').value === 'true'
    };
    
    try {
        await apiPut(`/exercises/${id}`, data);
        showToast('Exercise updated!', 'success');
        closeEditExerciseModal();
        loadExercises();
        loadExerciseList();
    } catch (error) {
        showToast('Failed to update exercise', 'error');
    }
}

function deleteExercise(id, name) {
    showConfirmModal(
        'Delete Exercise',
        `Are you sure you want to delete "${name}"? This will only work if no workouts use this exercise.`,
        async () => {
            try {
                await apiDelete(`/exercises/${id}`);
                showToast('Exercise deleted', 'success');
                loadExercises();
                loadExerciseList();
            } catch (error) {
                showToast(error.message, 'error');
            }
        }
    );
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
        
        document.getElementById('stats-summary').innerHTML = `
            <div class="stat-card"><div class="stat-value">${summary.workouts}</div><div class="stat-label">Workouts</div></div>
            <div class="stat-card"><div class="stat-value">${summary.total_sets}</div><div class="stat-label">Total Sets</div></div>
            <div class="stat-card"><div class="stat-value">${summary.total_reps}</div><div class="stat-label">Total Reps</div></div>
            <div class="stat-card"><div class="stat-value">${Math.round(summary.total_volume).toLocaleString()}</div><div class="stat-label">Volume (lbs)</div></div>
            <div class="stat-card"><div class="stat-value">${summary.unique_exercises}</div><div class="stat-label">Exercises</div></div>
            <div class="stat-card"><div class="stat-value">${summary.avg_rpe || '-'}</div><div class="stat-label">Avg RPE</div></div>
        `;
        
        document.getElementById('muscle-group-stats').innerHTML = summary.muscle_group_breakdown
            .map(mg => `<div class="muscle-stat"><span class="muscle-name">${mg.muscle_group}</span><span class="muscle-volume">${mg.sets} sets | ${Math.round(mg.volume).toLocaleString()} lbs</span></div>`).join('');
        
        document.getElementById('personal-records').innerHTML = prs.personal_records.length === 0 
            ? '<div class="empty-state"><p>No personal records yet</p></div>'
            : prs.personal_records.map(pr => `<div class="pr-item"><div class="pr-exercise">${pr.exercise_name}</div><div class="pr-records">${Object.entries(pr.records).map(([t, r]) => `<span class="pr-record">${t}: ${r.value}</span>`).join('')}</div></div>`).join('');
    } catch (error) {
        showToast('Failed to load stats', 'error');
    }
}

// ============================================
// Confirmation Modal
// ============================================
function showConfirmModal(title, message, callback) {
    document.getElementById('confirm-modal-title').textContent = title;
    document.getElementById('confirm-modal-message').textContent = message;
    document.getElementById('confirm-modal').style.display = 'flex';
    
    document.getElementById('confirm-modal-btn').onclick = () => {
        closeConfirmModal();
        callback();
    };
}

function closeConfirmModal() {
    document.getElementById('confirm-modal').style.display = 'none';
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
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
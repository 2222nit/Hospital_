document.addEventListener('DOMContentLoaded', () => {
    // Tab Switching
    const tabs = document.querySelectorAll('.nav-tab');
    const tabContents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            const target = tab.getAttribute('data-tab');
            document.getElementById(target).classList.add('active');
        });
    });

    // Modal Handlers
    const modal = document.getElementById('prediction-modal');
    document.getElementById('btn-open-modal').addEventListener('click', () => modal.classList.add('active'));
    document.getElementById('btn-close-modal').addEventListener('click', () => modal.classList.remove('active'));
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('active');
    });

    // Chart Global Defaults
    Chart.defaults.color = '#9ca3af';
    Chart.defaults.font.family = "'Inter', sans-serif";

    let chartOccupancyTrend = null;
    let chartDeptRisk = null;
    let chartCapacityBar = null;
    let chartDeptAlos = null;
    let chartFeatureImp = null;
    let chartRocCurve = null;

    // Load All Dashboard Data
    async function loadDashboardData() {
        try {
            await Promise.all([
                fetchOverview(),
                fetchUtilization(),
                fetchPatients(),
                fetchModelStats()
            ]);
        } catch (err) {
            console.error('Error loading dashboard data:', err);
        }
    }

    // 1. Overview API
    async function fetchOverview() {
        const res = await fetch('/api/overview');
        const data = await res.json();

        document.getElementById('kpi-readmission-rate').textContent = `${data.readmission_rate}%`;
        document.getElementById('kpi-readmission-sub').textContent = `${data.readmitted_count} of ${data.total_patients} Patients Readmitted`;
        
        document.getElementById('kpi-occupancy').textContent = `${data.occupancy_pct}%`;
        document.getElementById('kpi-occupancy-sub').textContent = `${data.occupied_beds} of ${data.total_beds} Total Beds Occupied`;
        
        document.getElementById('kpi-alos').textContent = `${data.avg_length_of_stay} Days`;
        document.getElementById('kpi-high-risk').textContent = data.high_risk_patients_count;
    }

    // 2. Utilization API & Charts
    async function fetchUtilization() {
        const res = await fetch('/api/utilization');
        const data = await res.json();

        const depts = data.departments.map(d => d.department);
        const occupancyPcts = data.departments.map(d => d.occupancy_pct);
        const readmRates = data.departments.map(d => d.readmission_rate);
        const capacities = data.departments.map(d => d.capacity);
        const occupied = data.departments.map(d => d.occupied);
        const alosList = data.departments.map(d => d.avg_los);

        // Chart 1: Occupancy Trend Line Chart
        const ctxTrend = document.getElementById('chart-occupancy-trend').getContext('2d');
        if (chartOccupancyTrend) chartOccupancyTrend.destroy();
        chartOccupancyTrend = new Chart(ctxTrend, {
            type: 'line',
            data: {
                labels: data.timeline.days,
                datasets: [
                    {
                        label: 'ICU Occupancy %',
                        data: data.timeline.icu,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.3,
                        fill: true
                    },
                    {
                        label: 'General Ward Occupancy %',
                        data: data.timeline.general_ward,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.3,
                        fill: true
                    },
                    {
                        label: 'Emergency Occupancy %',
                        data: data.timeline.emergency,
                        borderColor: '#06b6d4',
                        backgroundColor: 'rgba(6, 182, 212, 0.1)',
                        tension: 0.3,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top' } },
                scales: { y: { min: 40, max: 100, ticks: { callback: v => v + '%' } } }
            }
        });

        // Chart 2: Dept Risk Bar Chart
        const ctxRisk = document.getElementById('chart-dept-risk').getContext('2d');
        if (chartDeptRisk) chartDeptRisk.destroy();
        chartDeptRisk = new Chart(ctxRisk, {
            type: 'bar',
            data: {
                labels: depts,
                datasets: [{
                    label: '30-Day Readmission Rate %',
                    data: readmRates,
                    backgroundColor: ['#3b82f6', '#ef4444', '#06b6d4', '#8b5cf6', '#14b8a6'],
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { ticks: { callback: v => v + '%' } } }
            }
        });

        // Chart 3: Capacity vs Occupied Grouped Bar Chart
        const ctxCap = document.getElementById('chart-capacity-bar').getContext('2d');
        if (chartCapacityBar) chartCapacityBar.destroy();
        chartCapacityBar = new Chart(ctxCap, {
            type: 'bar',
            data: {
                labels: depts,
                datasets: [
                    { label: 'Occupied Beds', data: occupied, backgroundColor: '#3b82f6', borderRadius: 6 },
                    { label: 'Total Capacity', data: capacities, backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: 6 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top' } }
            }
        });

        // Chart 4: Dept ALOS Bar Chart
        const ctxAlos = document.getElementById('chart-dept-alos').getContext('2d');
        if (chartDeptAlos) chartDeptAlos.destroy();
        chartDeptAlos = new Chart(ctxAlos, {
            type: 'bar',
            data: {
                labels: depts,
                datasets: [{
                    label: 'Average Length of Stay (Days)',
                    data: alosList,
                    backgroundColor: '#06b6d4',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } }
            }
        });
    }

    // 3. Patient Register API & Filtering
    async function fetchPatients() {
        const search = document.getElementById('patient-search').value;
        const dept = document.getElementById('filter-dept').value;
        const risk = document.getElementById('filter-risk').value;

        const res = await fetch(`/api/patients?search=${encodeURIComponent(search)}&department=${encodeURIComponent(dept)}&risk_level=${encodeURIComponent(risk)}`);
        const data = await res.json();

        document.getElementById('patient-count').textContent = data.patients.length;
        const tbody = document.getElementById('patient-table-body');
        tbody.innerHTML = '';

        data.patients.forEach(p => {
            const tr = document.createElement('tr');
            let badgeClass = 'badge-low';
            if (p.risk_level === 'High') badgeClass = 'badge-high';
            else if (p.risk_level === 'Moderate') badgeClass = 'badge-moderate';

            tr.innerHTML = `
                <td><strong>${p.patient_id}</strong></td>
                <td>${p.age} yrs / ${p.gender}</td>
                <td>${p.department}</td>
                <td>${p.length_of_stay} days</td>
                <td>${p.prior_admissions_12m}</td>
                <td>${p.emergency_visits_6m}</td>
                <td><strong>${p.readmission_pct}%</strong></td>
                <td><span class="badge ${badgeClass}">${p.risk_level} Risk</span></td>
                <td>${p.discharge_destination}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    // Attach Event Listeners for Filtering
    document.getElementById('patient-search').addEventListener('input', fetchPatients);
    document.getElementById('filter-dept').addEventListener('change', fetchPatients);
    document.getElementById('filter-risk').addEventListener('change', fetchPatients);

    // 4. Model Performance API & Feature Importance Charts
    async function fetchModelStats() {
        const res = await fetch('/api/model-stats');
        const data = await res.json();

        const m = data.metrics;
        document.getElementById('metric-accuracy').textContent = `${(m.accuracy * 100).toFixed(1)}%`;
        document.getElementById('metric-roc').textContent = m.roc_auc;
        document.getElementById('metric-precision').textContent = `${(m.precision * 100).toFixed(1)}%`;
        document.getElementById('metric-recall').textContent = `${(m.recall * 100).toFixed(1)}%`;

        // Feature Importance Horizontal Bar Chart
        const featNames = Object.keys(data.feature_importances).slice(0, 8);
        const featVals = Object.values(data.feature_importances).slice(0, 8);

        const ctxFeat = document.getElementById('chart-feature-importance').getContext('2d');
        if (chartFeatureImp) chartFeatureImp.destroy();
        chartFeatureImp = new Chart(ctxFeat, {
            type: 'bar',
            data: {
                labels: featNames.map(f => f.replace(/_/g, ' ')),
                datasets: [{
                    label: 'Feature Importance Score',
                    data: featVals,
                    backgroundColor: '#8b5cf6',
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } }
            }
        });

        // ROC Curve Line Chart
        const ctxRoc = document.getElementById('chart-roc-curve').getContext('2d');
        if (chartRocCurve) chartRocCurve.destroy();
        
        const rocPoints = data.roc_curve.fpr.map((fpr, i) => ({ x: fpr, y: data.roc_curve.tpr[i] }));
        
        chartRocCurve = new Chart(ctxRoc, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: `Random Forest Model (AUC = ${m.roc_auc})`,
                        data: rocPoints,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.15)',
                        fill: true,
                        tension: 0.2
                    },
                    {
                        label: 'Random Baseline (AUC = 0.50)',
                        data: [{ x: 0, y: 0 }, { x: 1, y: 1 }],
                        borderColor: 'rgba(255, 255, 255, 0.3)',
                        borderDash: [5, 5],
                        pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { type: 'linear', min: 0, max: 1, title: { display: true, text: 'False Positive Rate' } },
                    y: { min: 0, max: 1, title: { display: true, text: 'True Positive Rate (Recall)' } }
                }
            }
        });
    }

    // 5. Predict Risk Form Handler
    document.getElementById('predict-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const payload = {
            age: document.getElementById('input-age').value,
            gender: document.getElementById('input-gender').value,
            department: document.getElementById('input-dept').value,
            length_of_stay: document.getElementById('input-los').value,
            prior_admissions_12m: document.getElementById('input-prior-adm').value,
            emergency_visits_6m: document.getElementById('input-er-visits').value,
            has_diabetes: document.getElementById('input-diabetes').checked ? 1 : 0,
            has_hypertension: document.getElementById('input-hypertension').checked ? 1 : 0,
            has_heart_disease: document.getElementById('input-heart-disease').checked ? 1 : 0,
            has_ckd: document.getElementById('input-ckd').checked ? 1 : 0,
            abnormal_labs: document.getElementById('input-abnormal-labs').checked ? 1 : 0
        };

        const res = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await res.json();
        
        // Render output
        const outputDiv = document.getElementById('prediction-output');
        outputDiv.classList.add('active');

        document.getElementById('result-probability').textContent = `${result.probability_pct}%`;
        const badge = document.getElementById('result-badge');
        badge.textContent = result.risk_level;
        badge.className = 'badge';
        if (result.risk_color === 'red') badge.classList.add('badge-high');
        else if (result.risk_color === 'amber') badge.classList.add('badge-moderate');
        else badge.classList.add('badge-low');

        // Factors list
        const factorsUl = document.getElementById('result-factors');
        factorsUl.innerHTML = result.contributing_factors.map(f => `<li>${f}</li>`).join('');

        // Recommendations list
        const recsUl = document.getElementById('result-recommendations');
        recsUl.innerHTML = result.recommendations.map(r => `<li>${r}</li>`).join('');
    });

    // 6. Reset / Regenerate Dataset Handler
    document.getElementById('btn-regenerate').addEventListener('click', async () => {
        const btn = document.getElementById('btn-regenerate');
        btn.disabled = true;
        btn.innerHTML = '<i data-lucide="loader-2" class="spin"></i> Regenerating...';

        try {
            await fetch('/api/regenerate', { method: 'POST' });
            await loadDashboardData();
            alert('Dataset regenerated and Machine Learning model successfully retrained!');
        } catch (err) {
            console.error('Failed to regenerate data:', err);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="refresh-cw"></i> Reset Data';
            lucide.createIcons();
        }
    });

    // Initial load
    loadDashboardData();
});

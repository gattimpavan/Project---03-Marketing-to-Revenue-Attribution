/**
 * Project - 03: Marketing-to-Revenue Attribution
 * Executive Intelligence Dashboard Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    // App State
    let dashboardData = null;
    let chartInstances = {};
    let activeChannelSpend = {};

    // Theme Toggle Initialization
    initTheme();

    // Load initial dashboard data from API
    fetchDashboardData();

    // Setup Event Listeners
    setupTabNavigation();
    setupLeadScorerForm();
    setupSimulatorPresets();

    /* ==========================================================================
       Data Ingestion & Initialization
       ========================================================================== */
    async function fetchDashboardData() {
        try {
            const response = await fetch('/api/summary');
            if (!response.ok) throw new Error('Network error loading dashboard summary');
            dashboardData = await response.json();
            
            // Populate all dashboard sections
            renderExecutiveKPIs();
            renderFunnelVisualizer();
            renderFunnelLeakageChart();
            renderChannelFunnelTable();
            
            renderAttributionCharts('markov_chain');
            renderAttributionMatrixTable();
            setupAttributionModelSelector();

            renderDiscrepancyMatrixChart();
            renderMLFeatureImportanceChart();
            renderFailurePatterns();

            renderLeadTiersTable();

            initBudgetSimulator();
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
        }
    }

    /* ==========================================================================
       Theme Toggle Logic
       ========================================================================== */
    function initTheme() {
        const themeBtn = document.getElementById('themeToggleBtn');
        const currentTheme = localStorage.getItem('amz_theme') || 'dark';
        document.documentElement.setAttribute('data-theme', currentTheme);
        themeBtn.querySelector('.theme-icon').textContent = currentTheme === 'dark' ? '🌙' : '☀️';

        themeBtn.addEventListener('click', () => {
            const active = document.documentElement.getAttribute('data-theme');
            const next = active === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('amz_theme', next);
            themeBtn.querySelector('.theme-icon').textContent = next === 'dark' ? '🌙' : '☀️';
            
            // Re-render charts with updated theme palette
            refreshAllCharts();
        });
    }

    /* ==========================================================================
       Tab Navigation
       ========================================================================== */
    function setupTabNavigation() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabPanes = document.querySelectorAll('.tab-pane');

        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetId = btn.getAttribute('data-tab');
                tabBtns.forEach(b => b.classList.remove('active'));
                tabPanes.forEach(p => p.classList.remove('active'));

                btn.classList.add('active');
                const targetPane = document.getElementById(targetId);
                if (targetPane) {
                    targetPane.classList.add('active');
                    // Resize charts in newly visible tab
                    window.dispatchEvent(new Event('resize'));
                }
            });
        });
    }

    /* ==========================================================================
       Executive Scorecard KPIs
       ========================================================================== */
    function renderExecutiveKPIs() {
        const attr = dashboardData.attribution;
        const funnel = dashboardData.funnel;

        document.getElementById('kpiTotalSpend').textContent = `$${(attr.total_spend).toLocaleString()}`;
        document.getElementById('kpiTotalLeads').textContent = funnel.total_leads.toLocaleString();
        document.getElementById('kpiTotalConverted').textContent = funnel.total_converted.toLocaleString();
        document.getElementById('kpiTotalRevenue').textContent = `$${Math.round(funnel.total_revenue).toLocaleString()}`;
        document.getElementById('kpiDollarLeakage').textContent = `$${Math.round(funnel.total_dollar_leakage).toLocaleString()}`;
        
        document.getElementById('kpiConversionRate').textContent = `${funnel.lead_to_conversion_rate}%`;
        document.getElementById('kpiBlendedRoas').textContent = `${attr.overall_roas}x`;
        document.getElementById('bannerLeakageVal').textContent = `$${(funnel.total_dollar_leakage / 1e6).toFixed(2)}M`;
        
        // Vanity lead share from tier summary
        const vanityTier = dashboardData.lead_scorer.tier_summary.find(t => t.tier.includes('Tier 3'));
        if (vanityTier) {
            document.getElementById('kpiVanityLeadShare').textContent = `${vanityTier.share}%`;
        }
    }

    /* ==========================================================================
       Tab 1: Funnel Progression & Dollar Leakage Visualizer
       ========================================================================== */
    function renderFunnelVisualizer() {
        const container = document.getElementById('funnelVisualContainer');
        container.innerHTML = '';
        const stages = dashboardData.funnel.stages;
        const maxCount = stages[0].count;

        stages.forEach(stage => {
            const widthPct = Math.max(12, Math.round((stage.count / maxCount) * 100));
            const isChasm = stage.stage_id === 4 || stage.stage_id === 5;
            
            let barColor = '#232F3E';
            if (stage.stage_id === 3) barColor = '#00A8E1';
            else if (stage.stage_id === 4) barColor = '#FF9900';
            else if (stage.stage_id >= 5) barColor = '#10B981';

            const stepEl = document.createElement('div');
            stepEl.className = 'funnel-step';
            stepEl.innerHTML = `
                <div class="funnel-step-header">
                    <span class="step-name">Stage ${stage.stage_id}: ${stage.stage_name}</span>
                    <span class="step-count" style="color: ${barColor}">${stage.count.toLocaleString()}</span>
                </div>
                <div class="funnel-bar-track">
                    <div class="funnel-bar-fill" style="width: ${widthPct}%; background: ${barColor}"></div>
                </div>
                <div class="funnel-step-footer">
                    <span>${stage.conversion_from_prev}% from prev stage</span>
                    <span>Drop-off: <strong class="${stage.drop_off_rate > 35 ? 'text-danger' : ''}">${stage.drop_off_rate}%</strong> (${stage.drop_off_count.toLocaleString()} drop)</span>
                    <span>Dollar Leakage: <strong class="text-danger">${stage.estimated_dollar_loss > 0 ? '$' + Math.round(stage.estimated_dollar_loss).toLocaleString() : '$0'}</strong></span>
                </div>
            `;
            container.appendChild(stepEl);
        });
    }

    function renderFunnelLeakageChart() {
        const ctx = document.getElementById('funnelLeakageChart').getContext('2d');
        const stages = dashboardData.funnel.stages.slice(2, 5); // Stages 3, 4, 5
        
        const labels = ['Lead Form Abandonment', 'Stage 4: Product Activation Chasm', 'Stage 5: Trial-to-Paid Friction'];
        const values = stages.map(s => s.estimated_dollar_loss);

        if (chartInstances.funnelLeakage) chartInstances.funnelLeakage.destroy();

        chartInstances.funnelLeakage = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Pipeline Dollar Leakage ($ USD)',
                    data: values,
                    backgroundColor: ['#64748B', '#EF4444', '#F59E0B'],
                    borderRadius: 6,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `Unrealized Loss: $${ctx.raw.toLocaleString()}`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (v) => `$${(v / 1e6).toFixed(1)}M`,
                            color: '#94A3B8'
                        },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    x: {
                        ticks: { color: '#94A3B8', font: { size: 10 } },
                        grid: { display: false }
                    }
                }
            }
        });
    }

    function renderChannelFunnelTable() {
        const tbody = document.getElementById('channelFunnelTableBody');
        tbody.innerHTML = '';
        const channels = dashboardData.channel_funnel;

        channels.forEach(ch => {
            const tr = document.createElement('tr');
            const statusClass = ch.funnel_health === 'Critical Leakage' ? 'badge-danger' : (ch.funnel_health === 'High Yield' ? 'badge-success' : 'badge-amazon');
            
            tr.innerHTML = `
                <td><strong>${ch.channel}</strong></td>
                <td>$${ch.spend.toLocaleString()}</td>
                <td>${ch.leads_generated.toLocaleString()}</td>
                <td>$${ch.cpl.toFixed(2)}</td>
                <td>${ch.activated_users.toLocaleString()}</td>
                <td>${ch.activation_rate}%</td>
                <td class="text-success"><strong>${ch.paid_conversions.toLocaleString()}</strong></td>
                <td>$${ch.cac.toFixed(0)}</td>
                <td class="text-amazon"><strong>$${ch.realized_revenue.toLocaleString()}</strong></td>
                <td><strong>${ch.roas.toFixed(2)}x</strong></td>
                <td class="${ch.vanity_lead_pct > 75 ? 'text-danger font-bold' : ''}">${ch.vanity_lead_pct}%</td>
                <td><span class="card-badge ${statusClass}">${ch.funnel_health}</span></td>
            `;
            tbody.appendChild(tr);
        });
    }

    /* ==========================================================================
       Tab 2: Multi-Touch Attribution Engine
       ========================================================================== */
    function setupAttributionModelSelector() {
        const select = document.getElementById('attributionModelSelect');
        select.addEventListener('change', (e) => {
            renderAttributionCharts(e.target.value);
        });
    }

    function renderAttributionCharts(activeModel) {
        const comp = dashboardData.attribution.channel_comparison;
        const labels = comp.map(c => c.channel.replace(' (High Intent)', '').replace(' / Display', '').replace(' / Enterprise', '').replace(' & Partners', ''));
        
        // 1. Revenue Comparison Chart
        const ctxRev = document.getElementById('attributionRevenueChart').getContext('2d');
        const ltaData = comp.map(c => c.last_touch.revenue);
        const activeData = comp.map(c => c[activeModel].revenue);
        const ftaData = comp.map(c => c.first_touch.revenue);

        if (chartInstances.attrRev) chartInstances.attrRev.destroy();

        chartInstances.attrRev = new Chart(ctxRev, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Last-Touch Attribution (LTA)',
                        data: ltaData,
                        backgroundColor: '#64748B',
                        borderRadius: 4
                    },
                    {
                        label: getModelDisplayName(activeModel),
                        data: activeData,
                        backgroundColor: '#FF9900',
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { color: '#94A3B8', font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: $${ctx.raw.toLocaleString()}`
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            callback: (v) => `$${(v / 1e3).toFixed(0)}K`,
                            color: '#94A3B8'
                        },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    x: {
                        ticks: { color: '#94A3B8', font: { size: 10 } },
                        grid: { display: false }
                    }
                }
            }
        });

        // 2. ROAS Comparison Chart
        const ctxRoas = document.getElementById('attributionRoasChart').getContext('2d');
        const ltaRoas = comp.map(c => c.last_touch.roas);
        const activeRoas = comp.map(c => c[activeModel].roas);

        if (chartInstances.attrRoas) chartInstances.attrRoas.destroy();

        chartInstances.attrRoas = new Chart(ctxRoas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'LTA ROAS (Legacy)',
                        data: ltaRoas,
                        backgroundColor: 'rgba(100, 116, 139, 0.7)',
                        borderRadius: 4
                    },
                    {
                        label: `${getModelDisplayName(activeModel)} ROAS`,
                        data: activeRoas,
                        backgroundColor: '#00A8E1',
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { color: '#94A3B8', font: { size: 11 } } }
                },
                scales: {
                    y: {
                        ticks: {
                            callback: (v) => `${v.toFixed(1)}x`,
                            color: '#94A3B8'
                        },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    x: {
                        ticks: { color: '#94A3B8', font: { size: 10 } },
                        grid: { display: false }
                    }
                }
            }
        });
    }

    function getModelDisplayName(key) {
        switch (key) {
            case 'markov_chain': return 'Markov Chain AI (Data-Driven)';
            case 'last_touch': return 'Last-Touch Attribution';
            case 'first_touch': return 'First-Touch Attribution';
            case 'linear': return 'Linear Attribution';
            case 'position_based': return 'Position-Based (U-Shape)';
            case 'time_decay': return 'Time-Decay Attribution';
            default: return key;
        }
    }

    function renderAttributionMatrixTable() {
        const tbody = document.getElementById('attributionMatrixBody');
        tbody.innerHTML = '';
        const comp = dashboardData.attribution.channel_comparison;

        comp.forEach(c => {
            const tr = document.createElement('tr');
            const biasClass = c.lta_distortion_status.includes('Over-Valued') ? 'text-danger' : (c.lta_distortion_status.includes('Under-Valued') ? 'text-success' : 'text-muted');
            
            tr.innerHTML = `
                <td><strong>${c.channel}</strong></td>
                <td>$${c.spend.toLocaleString()}</td>
                <td>$${c.first_touch.revenue.toLocaleString()}</td>
                <td>$${c.last_touch.revenue.toLocaleString()}</td>
                <td>${c.last_touch.roas.toFixed(2)}x</td>
                <td class="text-amazon"><strong>$${c.markov_chain.revenue.toLocaleString()}</strong></td>
                <td class="text-cyan"><strong>${c.markov_chain.roas.toFixed(2)}x</strong></td>
                <td>${c.markov_chain.markov_weight}%</td>
                <td>${c.markov_chain.removal_effect}</td>
                <td class="${biasClass}"><strong>${c.distortion_pct > 0 ? '+' : ''}${c.distortion_pct}%</strong> (${c.lta_distortion_status.split(' ')[0]})</td>
            `;
            tbody.appendChild(tr);
        });
    }

    /* ==========================================================================
       Tab 3: AI Leakage & Root-Cause Explorer
       ========================================================================== */
    function renderDiscrepancyMatrixChart() {
        const ctx = document.getElementById('discrepancyMatrixChart').getContext('2d');
        const disc = dashboardData.leakage.discrepancies;

        const dataPoints = disc.map(d => ({
            x: d.lead_share,
            y: d.revenue_share,
            channel: d.channel,
            index: d.discrepancy_index
        }));

        if (chartInstances.discrepancy) chartInstances.discrepancy.destroy();

        chartInstances.discrepancy = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Channels',
                    data: dataPoints,
                    backgroundColor: dataPoints.map(p => p.index > 5 ? '#EF4444' : (p.index < -4 ? '#10B981' : '#00A8E1')),
                    pointRadius: 9,
                    pointHoverRadius: 12
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const pt = ctx.raw;
                                return `${pt.channel}: Lead Share ${pt.x}%, Rev Share ${pt.y}% (Index: ${pt.index > 0 ? '+' : ''}${pt.index}%)`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Lead Share % (Share of all Ingested Leads)', color: '#94A3B8', font: { size: 11 } },
                        ticks: { color: '#94A3B8' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        min: 0,
                        max: 42
                    },
                    y: {
                        title: { display: true, text: 'Realized Revenue Share %', color: '#94A3B8', font: { size: 11 } },
                        ticks: { color: '#94A3B8' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        min: 0,
                        max: 36
                    }
                }
            }
        });
    }

    function renderMLFeatureImportanceChart() {
        const ctx = document.getElementById('mlFeatureImportanceChart').getContext('2d');
        const topFeatures = dashboardData.lead_scorer.metrics.top_features.slice(0, 6);

        const labels = topFeatures.map(f => f.feature.replace('first_touch_channel_', 'Channel: ').replace('segment_', 'Segment: '));
        const weights = topFeatures.map(f => f.weight);

        if (chartInstances.features) chartInstances.features.destroy();

        chartInstances.features = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Predictive Feature Importance %',
                    data: weights,
                    backgroundColor: '#00A8E1',
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        ticks: { color: '#94A3B8', callback: (v) => `${v}%` },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    y: {
                        ticks: { color: '#94A3B8', font: { size: 10 } },
                        grid: { display: false }
                    }
                }
            }
        });
    }

    function renderFailurePatterns() {
        const container = document.getElementById('failurePatternsGrid');
        container.innerHTML = '';
        const patterns = dashboardData.leakage.ml_insights.failure_patterns;

        patterns.forEach(pat => {
            const card = document.createElement('div');
            card.className = 'pattern-card';
            card.innerHTML = `
                <div class="pattern-title">${pat.pattern_name}</div>
                <div class="pattern-cohort">${pat.affected_cohort}</div>
                <div class="pattern-leakage">Leakage: ${pat.revenue_leakage}</div>
                <div class="pattern-desc">${pat.root_cause}</div>
                <div class="funnel-step-footer mt-3">
                    <span>Activation Rate: <strong>${pat.activation_rate}%</strong></span>
                    <span>Paid Win Rate: <strong>${pat.paid_conversion_rate}%</strong></span>
                </div>
            `;
            container.appendChild(card);
        });
    }

    /* ==========================================================================
       Tab 4: Interactive AI Lead Scorer
       ========================================================================= */
    function setupLeadScorerForm() {
        const form = document.getElementById('leadScorerForm');
        const touchesInput = document.getElementById('leadTouches');
        const touchesVal = document.getElementById('leadTouchesVal');
        const channelsInput = document.getElementById('leadUniqueChannels');
        const channelsVal = document.getElementById('leadUniqueChannelsVal');

        touchesInput.addEventListener('input', (e) => {
            touchesVal.textContent = `${e.target.value} Touchpoints`;
        });

        channelsInput.addEventListener('input', (e) => {
            channelsVal.textContent = `${e.target.value} Channels`;
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                segment: document.getElementById('leadSegment').value,
                first_touch_channel: document.getElementById('leadChannel').value,
                device: document.getElementById('leadDevice').value,
                touchpoints_count: parseInt(touchesInput.value),
                unique_channels_count: parseInt(channelsInput.value)
            };

            const submitBtn = document.getElementById('scoreLeadBtn');
            submitBtn.textContent = 'Computing ML Probability...';

            try {
                const res = await fetch('/api/score-lead', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await res.json();
                
                // Update Result Card
                document.getElementById('aiVerdictBadge').textContent = 'Prediction Complete';
                document.getElementById('verdictTierText').textContent = result.lead_tier;
                document.getElementById('verdictProbVal').textContent = `${result.conversion_probability}%`;
                document.getElementById('verdictLtvVal').textContent = `$${result.expected_12m_ltv.toLocaleString()}`;
                document.getElementById('verdictActionText').textContent = result.recommended_action;

                // Color classes
                const tierEl = document.getElementById('verdictTierText');
                if (result.tier_class === 'danger') {
                    tierEl.style.color = '#EF4444';
                    tierEl.style.borderColor = 'rgba(239, 68, 68, 0.4)';
                    tierEl.style.background = 'rgba(239, 68, 68, 0.12)';
                } else if (result.tier_class === 'warning') {
                    tierEl.style.color = '#F59E0B';
                    tierEl.style.borderColor = 'rgba(245, 158, 11, 0.4)';
                    tierEl.style.background = 'rgba(245, 158, 11, 0.12)';
                } else {
                    tierEl.style.color = '#10B981';
                    tierEl.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                    tierEl.style.background = 'rgba(16, 185, 129, 0.12)';
                }
            } catch (err) {
                console.error('Lead scoring failed:', err);
            } finally {
                submitBtn.textContent = 'Run AI Lead Evaluation';
            }
        });
    }

    function renderLeadTiersTable() {
        const tbody = document.getElementById('leadTiersTableBody');
        tbody.innerHTML = '';
        const tiers = dashboardData.lead_scorer.tier_summary;

        tiers.forEach(t => {
            const tr = document.createElement('tr');
            let policy = '';
            if (t.tier.includes('Tier 1')) policy = 'Direct Enterprise AE routing within 15 mins';
            else if (t.tier.includes('Tier 2')) policy = 'Automated interactive product tour & demo email';
            else policy = 'Self-serve credit card gate; eliminate human SDR hours';

            tr.innerHTML = `
                <td><strong>${t.tier}</strong></td>
                <td>${t.count.toLocaleString()}</td>
                <td>${t.share}%</td>
                <td class="${t.actual_conversion_rate > 50 ? 'text-success font-bold' : (t.actual_conversion_rate < 15 ? 'text-danger' : '')}">${t.actual_conversion_rate}%</td>
                <td>$${t.avg_realized_revenue.toLocaleString()}</td>
                <td class="text-amazon"><strong>$${t.avg_predicted_ltv.toLocaleString()}</strong></td>
                <td><small>${policy}</small></td>
            `;
            tbody.appendChild(tr);
        });
    }

    /* ==========================================================================
       Tab 5: What-If Marketing Budget Simulator
       ========================================================================== */
    function initBudgetSimulator() {
        activeChannelSpend = { ...dashboardData.channel_spend };
        renderSimulatorSliders();
        runSimulation();
    }

    function renderSimulatorSliders() {
        const container = document.getElementById('simSlidersList');
        container.innerHTML = '';

        for (const [ch, spend] of Object.entries(activeChannelSpend)) {
            const row = document.createElement('div');
            row.className = 'sim-slider-row';
            
            const minSpend = Math.round(spend * 0.2);
            const maxSpend = Math.round(spend * 2.2);

            row.innerHTML = `
                <div class="sim-slider-label">
                    <span>${ch}</span>
                    <span id="sliderVal_${ch.replace(/[^a-zA-Z0-9]/g, '')}">$${spend.toLocaleString()}</span>
                </div>
                <input type="range" class="form-range" 
                    id="slider_${ch.replace(/[^a-zA-Z0-9]/g, '')}"
                    min="${minSpend}" max="${maxSpend}" step="10000" value="${spend}">
            `;
            container.appendChild(row);

            // Listener
            const slider = row.querySelector('input');
            slider.addEventListener('input', (e) => {
                const val = parseFloat(e.target.value);
                activeChannelSpend[ch] = val;
                document.getElementById(`sliderVal_${ch.replace(/[^a-zA-Z0-9]/g, '')}`).textContent = `$${val.toLocaleString()}`;
                runSimulation();
            });
        }

        document.getElementById('resetSlidersBtn').addEventListener('click', () => {
            activeChannelSpend = { ...dashboardData.channel_spend };
            renderSimulatorSliders();
            runSimulation();
        });
    }

    function setupSimulatorPresets() {
        const presetBtns = document.querySelectorAll('.preset-btn-group button');
        
        presetBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                presetBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const scKey = btn.id.replace('preset', '').toLowerCase();
                let targetKey = 'baseline';
                if (scKey.includes('recommended')) targetKey = 'attribution_optimized';
                else if (scKey.includes('enterprise')) targetKey = 'enterprise_growth';
                else if (scKey.includes('margin')) targetKey = 'margin_preservation';

                const targetScenario = dashboardData.scenarios[targetKey];
                if (targetScenario) {
                    activeChannelSpend = {};
                    targetScenario.metrics.channel_details.forEach(c => {
                        activeChannelSpend[c.channel] = c.simulated_spend;
                    });
                    renderSimulatorSliders();
                    runSimulation();
                }
            });
        });
    }

    async function runSimulation() {
        try {
            const res = await fetch('/api/simulate-budget', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(activeChannelSpend)
            });
            const sim = await res.json();
            
            // Update KPIs
            document.getElementById('simSpendVal').textContent = `$${Math.round(sim.simulated_spend).toLocaleString()}`;
            document.getElementById('simSpendDelta').textContent = `${sim.spend_difference >= 0 ? '+' : ''}$${Math.round(sim.spend_difference / 1000)}K (${((sim.simulated_spend - sim.baseline_spend)/sim.baseline_spend * 100).toFixed(1)}%)`;

            document.getElementById('simRevVal').textContent = `$${Math.round(sim.simulated_revenue).toLocaleString()}`;
            document.getElementById('simRevDelta').textContent = `${sim.net_revenue_lift >= 0 ? '+' : ''}$${Math.round(sim.net_revenue_lift).toLocaleString()} (${sim.revenue_lift_pct}%)`;

            document.getElementById('simRoasVal').textContent = `${sim.simulated_roas.toFixed(2)}x`;
            document.getElementById('simRoasDelta').textContent = `Baseline: ${sim.baseline_roas.toFixed(2)}x (${sim.roas_improvement >= 0 ? '+' : ''}${sim.roas_improvement.toFixed(2)}x)`;

            document.getElementById('simLiftBadge').textContent = `${sim.net_revenue_lift >= 0 ? '+' : ''}$${(sim.net_revenue_lift / 1000).toFixed(1)}K Net Lift`;

            // Chart
            renderSimComparisonChart(sim);
        } catch (err) {
            console.error('Simulation request failed:', err);
        }
    }

    function renderSimComparisonChart(sim) {
        const ctx = document.getElementById('simComparisonChart').getContext('2d');
        const channels = sim.channel_details.map(c => c.channel.replace(' (High Intent)', '').replace(' / Display', '').replace(' / Enterprise', ''));
        const baselineRev = sim.channel_details.map(c => c.current_revenue);
        const simRev = sim.channel_details.map(c => c.simulated_revenue);

        if (chartInstances.simComp) chartInstances.simComp.destroy();

        chartInstances.simComp = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: channels,
                datasets: [
                    {
                        label: 'Baseline Revenue ($)',
                        data: baselineRev,
                        backgroundColor: '#64748B',
                        borderRadius: 4
                    },
                    {
                        label: 'Simulated Projected Revenue ($)',
                        data: simRev,
                        backgroundColor: '#FF9900',
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { color: '#94A3B8', font: { size: 10 } } }
                },
                scales: {
                    y: {
                        ticks: {
                            callback: (v) => `$${(v / 1e3).toFixed(0)}K`,
                            color: '#94A3B8'
                        },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    x: {
                        ticks: { color: '#94A3B8', font: { size: 9 } },
                        grid: { display: false }
                    }
                }
            }
        });
    }

    function refreshAllCharts() {
        if (dashboardData) {
            renderFunnelLeakageChart();
            renderAttributionCharts(document.getElementById('attributionModelSelect').value);
            renderDiscrepancyMatrixChart();
            renderMLFeatureImportanceChart();
            runSimulation();
        }
    }
});

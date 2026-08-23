/**
 * BlueByte AI — Telemetry Charts
 * Rolling time-series charts for SST, Salinity, and Dissolved Oxygen.
 * Features: gradient fills, sparse X-axis labels, dark-themed tooltips.
 */
class TelemetryCharts {
    constructor() {
        this.maxDataPoints = 40;

        // Global Chart.js defaults for dark marine theme
        Chart.defaults.color = '#8e9bb0';
        Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.06)';
        Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";

        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 350
            },
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                x: {
                    display: true,
                    ticks: {
                        maxTicksLimit: 6,
                        font: { size: 9 },
                        color: 'rgba(142, 155, 176, 0.6)',
                        maxRotation: 0
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: false,
                    ticks: {
                        font: { size: 9 },
                        color: 'rgba(142, 155, 176, 0.6)',
                        maxTicksLimit: 4
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.04)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: false  // Using HTML headings instead
                },
                tooltip: {
                    backgroundColor: 'rgba(13, 19, 51, 0.95)',
                    borderColor: 'rgba(0, 229, 255, 0.3)',
                    borderWidth: 1,
                    titleColor: '#ffffff',
                    bodyColor: '#8e9bb0',
                    titleFont: { size: 11, weight: '600' },
                    bodyFont: { size: 11 },
                    padding: 10,
                    cornerRadius: 6,
                    displayColors: true,
                    boxPadding: 4
                }
            },
            elements: {
                point: {
                    radius: 0,
                    hoverRadius: 4,
                    hoverBorderWidth: 2
                },
                line: {
                    tension: 0.4,
                    borderWidth: 2
                }
            }
        };

        // --- SST Chart ---
        const ctxSST = document.getElementById('sstChart').getContext('2d');
        const sstGradient = ctxSST.createLinearGradient(0, 0, 0, 120);
        sstGradient.addColorStop(0, 'rgba(0, 229, 255, 0.3)');
        sstGradient.addColorStop(1, 'rgba(0, 229, 255, 0.0)');

        this.sstChart = new Chart(ctxSST, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'SST (°C)',
                    data: [],
                    borderColor: '#00e5ff',
                    backgroundColor: sstGradient,
                    fill: true,
                    pointBackgroundColor: '#00e5ff'
                }]
            },
            options: { ...commonOptions }
        });

        // --- Salinity Chart ---
        const ctxSal = document.getElementById('salinityChart').getContext('2d');
        const salGradient = ctxSal.createLinearGradient(0, 0, 0, 120);
        salGradient.addColorStop(0, 'rgba(0, 230, 118, 0.3)');
        salGradient.addColorStop(1, 'rgba(0, 230, 118, 0.0)');

        this.salinityChart = new Chart(ctxSal, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Salinity (PSU)',
                    data: [],
                    borderColor: '#00e676',
                    backgroundColor: salGradient,
                    fill: true,
                    pointBackgroundColor: '#00e676'
                }]
            },
            options: { ...commonOptions }
        });

        // --- Dissolved Oxygen Chart ---
        const ctxDO = document.getElementById('doChart').getContext('2d');
        const doGradient = ctxDO.createLinearGradient(0, 0, 0, 120);
        doGradient.addColorStop(0, 'rgba(255, 111, 0, 0.3)');
        doGradient.addColorStop(1, 'rgba(255, 111, 0, 0.0)');

        this.doChart = new Chart(ctxDO, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'DO (mg/L)',
                    data: [],
                    borderColor: '#ff6f00',
                    backgroundColor: doGradient,
                    fill: true,
                    pointBackgroundColor: '#ff6f00'
                }]
            },
            options: { ...commonOptions }
        });
    }

    /**
     * Update all three charts with new telemetry data.
     */
    updateCharts(data) {
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        if (data.sea_surface_temp_c != null) {
            this._addData(this.sstChart, time, data.sea_surface_temp_c);
        }
        if (data.salinity_psu != null) {
            this._addData(this.salinityChart, time, data.salinity_psu);
        }
        if (data.dissolved_oxygen_mg_l != null) {
            this._addData(this.doChart, time, data.dissolved_oxygen_mg_l);
        }
    }

    /**
     * Append a data point to a chart, trimming old points to maxDataPoints.
     */
    _addData(chart, label, data) {
        chart.data.labels.push(label);
        chart.data.datasets[0].data.push(data);

        if (chart.data.labels.length > this.maxDataPoints) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }

        chart.update('none'); // Skip full animation for perf
    }
}

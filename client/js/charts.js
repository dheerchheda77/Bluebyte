class TelemetryCharts {
    constructor() {
        this.maxDataPoints = 30;
        
        Chart.defaults.color = '#8e9bb0';
        Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';

        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 400
            },
            scales: {
                x: {
                    display: false // Hide X axis labels for sparkline effect
                },
                y: {
                    beginAtZero: false
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    color: '#ffffff',
                    font: { size: 14 }
                }
            },
            elements: {
                point: { radius: 0 },
                line: { tension: 0.4 } // Smooth curves
            }
        };

        // SST Chart
        const ctxSST = document.getElementById('sstChart').getContext('2d');
        this.sstChart = new Chart(ctxSST, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'SST (°C)', data: [], borderColor: '#00e5ff', borderWidth: 2 }] },
            options: { ...commonOptions, plugins: { ...commonOptions.plugins, title: { display: true, text: 'SST (°C)', color: '#00e5ff' } } }
        });

        // Salinity Chart
        const ctxSal = document.getElementById('salinityChart').getContext('2d');
        this.salinityChart = new Chart(ctxSal, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'Salinity (PSU)', data: [], borderColor: '#00e676', borderWidth: 2 }] },
            options: { ...commonOptions, plugins: { ...commonOptions.plugins, title: { display: true, text: 'Salinity (PSU)', color: '#00e676' } } }
        });

        // DO Chart
        const ctxDO = document.getElementById('doChart').getContext('2d');
        this.doChart = new Chart(ctxDO, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'DO (mg/L)', data: [], borderColor: '#ff6f00', borderWidth: 2 }] },
            options: { ...commonOptions, plugins: { ...commonOptions.plugins, title: { display: true, text: 'Dissolved Oxygen (mg/L)', color: '#ff6f00' } } }
        });
    }

    updateCharts(data) {
        const time = new Date().toLocaleTimeString();

        if (data.sea_surface_temp_c) {
            this._addData(this.sstChart, time, data.sea_surface_temp_c);
        }
        if (data.salinity_psu) {
            this._addData(this.salinityChart, time, data.salinity_psu);
        }
        if (data.dissolved_oxygen_mg_l) {
            this._addData(this.doChart, time, data.dissolved_oxygen_mg_l);
        }
    }

    _addData(chart, label, data) {
        chart.data.labels.push(label);
        chart.data.datasets[0].data.push(data);
        
        if (chart.data.labels.length > this.maxDataPoints) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }
        
        chart.update('none'); // Update without full animation for better performance
    }
}

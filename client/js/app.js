document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Map
    const oceanMap = new OceanMap('map');

    // 2. Initialize Charts
    const charts = new TelemetryCharts();

    // 3. Clock Update
    setInterval(() => {
        document.getElementById('clock').innerText = new Date().toLocaleTimeString();
    }, 1000);

    // 4. Layer Toggles
    const toggleIds = ['heatmap', 'buoys', 'vessels', 'pfz', 'anomalies'];
    toggleIds.forEach(id => {
        const el = document.getElementById(`toggle-${id}`);
        if (el) {
            el.addEventListener('change', (e) => {
                oceanMap.toggleLayer(id, e.target.checked);
            });
        }
    });

    // 5. Update Alerts UI
    function addAlertToUI(data) {
        const list = document.getElementById('alerts-list');
        const reason = data.anomaly_reason || 'Unknown anomaly detected';
        
        // Remove info placeholder if present
        const infoEl = list.querySelector('.alert-item.info');
        if (infoEl) infoEl.remove();

        const el = document.createElement('div');
        el.className = `alert-item critical`;
        el.innerHTML = `
            <strong>${data.sensor_id || 'System'}</strong><br>
            ${reason}<br>
            <small style="color: #8e9bb0">${new Date().toLocaleTimeString()}</small>
        `;
        
        list.insertBefore(el, list.firstChild);
        
        // Keep max 20
        if (list.children.length > 20) {
            list.removeChild(list.lastChild);
        }
    }

    // 6. Species Predictions fetch
    function loadSpeciesPredictions() {
        const list = document.getElementById('species-list');
        // Try fetch, fallback to mock if API down
        fetch('/api/v1/predictions/species/GRID-01')
            .then(res => {
                if (!res.ok) throw new Error('API unavailable');
                return res.json();
            })
            .then(data => renderSpecies(data))
            .catch(err => {
                console.log("Using mock species data");
                const mock = [
                    { species: "Indian Mackerel", confidence: 0.85 },
                    { species: "Yellowfin Tuna", confidence: 0.62 },
                    { species: "Oil Sardine", confidence: 0.45 },
                    { species: "Hilsa", confidence: 0.30 }
                ];
                renderSpecies(mock);
            });

        function renderSpecies(data) {
            list.innerHTML = '';
            data.sort((a,b) => b.confidence - a.confidence).forEach(item => {
                const perc = (item.confidence * 100).toFixed(0);
                list.innerHTML += `
                    <div class="species-item">
                        <div class="species-name">
                            <span>${item.species}</span>
                            <span>${perc}%</span>
                        </div>
                        <div class="species-bar-bg">
                            <div class="species-bar-fill" style="width: ${perc}%"></div>
                        </div>
                    </div>
                `;
            });
        }
    }

    // 7. PFZ fetch
    function loadPFZ() {
        fetch('/api/v1/predictions/pfz')
            .then(res => {
                if(!res.ok) throw new Error('API unavailable');
                return res.json();
            })
            .then(data => {
                if(data.zones) data.zones.forEach(z => oceanMap.addPFZZone(z));
            })
            .catch(err => {
                console.log("Using mock PFZ data");
                oceanMap.addPFZZone({ lat: 15.5, lon: 72.0, confidence: 0.88, species: "Indian Mackerel", radius_km: 15 });
                oceanMap.addPFZZone({ lat: 10.0, lon: 75.5, confidence: 0.76, species: "Yellowfin Tuna", radius_km: 25 });
                oceanMap.addPFZZone({ lat: 12.2, lon: 81.0, confidence: 0.91, species: "Mixed", radius_km: 10 });
            });
    }

    // 8. WebSocket Setup
    const ws = new TelemetryWebSocket('ws://localhost:8000/ws/live-telemetry');
    
    ws.onConnectionChange((status) => {
        const dot = document.getElementById('connection-status-dot');
        const text = document.getElementById('connection-status-text');
        if (status === 'connected') {
            dot.classList.add('connected');
            text.innerText = 'Live Data Connected';
            demoModeActive = false;
        } else {
            dot.classList.remove('connected');
            text.innerText = 'Reconnecting... (Demo Mode)';
            if (!demoModeActive) startDemoMode();
        }
    });

    ws.onTelemetry((data) => {
        oceanMap.addBuoyReading(data);
        charts.updateCharts(data);
    });

    ws.onAnomaly((data) => {
        oceanMap.addAnomalyMarker(data);
        addAlertToUI(data);
    });

    // Start UI Data Loading
    loadSpeciesPredictions();
    loadPFZ();
    ws.connect();

    // 9. Demo Mode (Fallback for Hackathon Presentation)
    let demoModeActive = false;
    let demoInterval = null;

    function startDemoMode() {
        demoModeActive = true;
        console.log("Starting Demo Mode");
        
        // Add some static buoys
        const mockBuoys = [
            { id: "BUOY-IO-01", lat: 15.0, lon: 70.0, sst: 28.5, sal: 34.2, do: 5.1 },
            { id: "BUOY-IO-02", lat: 11.5, lon: 74.0, sst: 29.1, sal: 33.8, do: 4.8 },
            { id: "BUOY-BOB-01", lat: 13.0, lon: 82.0, sst: 30.2, sal: 32.5, do: 4.2 }
        ];

        // Vessel simulation
        let vessel = { id: "VESSEL-001", lat: 8.0, lon: 77.0, heading: 45 };

        if (demoInterval) clearInterval(demoInterval);
        
        demoInterval = setInterval(() => {
            if (!demoModeActive) {
                clearInterval(demoInterval);
                return;
            }

            // Update a random buoy
            const buoy = mockBuoys[Math.floor(Math.random() * mockBuoys.length)];
            const sstFuzz = (Math.random() - 0.5) * 0.2;
            buoy.sst += sstFuzz;
            
            const data = {
                sensor_id: buoy.id,
                sensor_name: buoy.id,
                lat: buoy.lat,
                lon: buoy.lon,
                sea_surface_temp_c: buoy.sst,
                salinity_psu: buoy.sal,
                dissolved_oxygen_mg_l: buoy.do
            };

            oceanMap.addBuoyReading(data);
            charts.updateCharts(data);

            // Move vessel
            vessel.lat += 0.05;
            vessel.lon += 0.05;
            oceanMap.addVesselPosition({
                vessel_id: vessel.id,
                lat: vessel.lat,
                lon: vessel.lon,
                heading: vessel.heading,
                speed: 12.5
            });

            // Random Anomaly (5% chance per tick)
            if (Math.random() > 0.95) {
                const anomalyData = {
                    sensor_id: buoy.id,
                    lat: buoy.lat,
                    lon: buoy.lon,
                    anomaly_flag: true,
                    anomaly_reason: "Rapid SST drop detected",
                    z_score_sst: -3.2
                };
                oceanMap.addAnomalyMarker(anomalyData);
                addAlertToUI(anomalyData);
            }
        }, 2000);
    }
});

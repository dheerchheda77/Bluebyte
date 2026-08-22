/**
 * BlueByte AI — Application Controller
 * Initializes all dashboard components, handles WebSocket events,
 * persists user preferences, manages demo mode, and provides audio alerts.
 */
document.addEventListener('DOMContentLoaded', () => {

    // =========================================================
    //  1. INITIALIZE CORE COMPONENTS
    // =========================================================
    const oceanMap = new OceanMap('map');
    const charts = new TelemetryCharts();

    // =========================================================
    //  2. LIVE CLOCK (monospace, cyan — §3.2)
    // =========================================================
    const clockEl = document.getElementById('clock');
    function updateClock() {
        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
    updateClock();
    setInterval(updateClock, 1000);

    // =========================================================
    //  3. PERSISTED PREFERENCES (§6 — localStorage)
    // =========================================================
    const PREFS_KEY = 'bluebyte_ui_prefs';

    function loadPreferences() {
        try {
            const raw = localStorage.getItem(PREFS_KEY);
            if (!raw) return null;
            return JSON.parse(raw);
        } catch (e) {
            return null;
        }
    }

    window.savePreferences = function savePreferences() {
        const prefs = {
            layers: {},
            panels: {},
            muted: isMuted
        };

        // Layer toggles
        toggleIds.forEach(id => {
            const el = document.getElementById(`toggle-${id}`);
            if (el) prefs.layers[id] = el.checked;
        });

        // Panel collapsed states
        panelIds.forEach(id => {
            const panel = document.getElementById(id);
            if (panel) prefs.panels[id] = panel.classList.contains('collapsed');
        });

        localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
    };

    function applyPreferences(prefs) {
        if (!prefs) return;

        // Restore layer toggles
        if (prefs.layers) {
            Object.entries(prefs.layers).forEach(([id, checked]) => {
                const el = document.getElementById(`toggle-${id}`);
                if (el) {
                    el.checked = checked;
                    oceanMap.toggleLayer(id, checked);
                }
            });
        }

        // Restore panel collapsed states
        if (prefs.panels) {
            Object.entries(prefs.panels).forEach(([id, isCollapsed]) => {
                const panel = document.getElementById(id);
                const header = document.querySelector(`[aria-controls="${id}"]`);
                if (panel && isCollapsed) {
                    panel.classList.add('collapsed');
                    if (header) {
                        header.classList.add('collapsed');
                        header.setAttribute('aria-expanded', 'false');
                    }
                }
            });
        }

        // Restore mute state
        if (prefs.muted != null) {
            isMuted = prefs.muted;
            updateMuteUI();
        }
    }

    // =========================================================
    //  4. LAYER TOGGLES
    // =========================================================
    const toggleIds = ['heatmap', 'buoys', 'vessels', 'pfz', 'anomalies'];
    const panelIds = ['layer-controls', 'species-predictions', 'active-alerts'];

    toggleIds.forEach(id => {
        const el = document.getElementById(`toggle-${id}`);
        if (el) {
            el.addEventListener('change', (e) => {
                oceanMap.toggleLayer(id, e.target.checked);
                savePreferences();
            });
        }
    });

    // =========================================================
    //  5. HAMBURGER TOGGLE (Mobile sidebar — §6)
    // =========================================================
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            const isOpen = sidebar.classList.toggle('open');
            sidebarOverlay.classList.toggle('active', isOpen);
            sidebarToggle.setAttribute('aria-expanded', isOpen);
        });
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            sidebarOverlay.classList.remove('active');
            sidebarToggle.setAttribute('aria-expanded', 'false');
        });
    }

    // =========================================================
    //  6. SOUND/MUTE SYSTEM (§6 — AudioContext beep for critical)
    // =========================================================
    let isMuted = false;
    let audioCtx = null;
    const muteToggle = document.getElementById('mute-toggle');

    function updateMuteUI() {
        if (!muteToggle) return;
        const icon = muteToggle.querySelector('i');
        const label = muteToggle.querySelector('span');
        if (isMuted) {
            icon.className = 'fa-solid fa-volume-xmark';
            muteToggle.classList.add('muted');
            if (label) label.textContent = 'Muted';
        } else {
            icon.className = 'fa-solid fa-volume-high';
            muteToggle.classList.remove('muted');
            if (label) label.textContent = 'Sound';
        }
    }

    if (muteToggle) {
        muteToggle.addEventListener('click', () => {
            isMuted = !isMuted;
            updateMuteUI();
            savePreferences();
        });
    }

    function playAlertBeep(severity) {
        if (isMuted || severity !== 'critical') return;

        try {
            if (!audioCtx) {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }

            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();

            osc.connect(gain);
            gain.connect(audioCtx.destination);

            // Two-tone urgent beep
            osc.type = 'sine';
            osc.frequency.setValueAtTime(880, audioCtx.currentTime);
            osc.frequency.setValueAtTime(660, audioCtx.currentTime + 0.12);

            gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.3);

            osc.start(audioCtx.currentTime);
            osc.stop(audioCtx.currentTime + 0.3);
        } catch (e) {
            // Audio not available — silent fallback
        }
    }

    // =========================================================
    //  7. ALERTS UI — Severity-based styling (§3.4)
    // =========================================================
    function addAlertToUI(data) {
        const list = document.getElementById('alerts-list');
        const reason = data.anomaly_reason || 'Unknown anomaly detected';
        const severity = data.severity || 'critical';

        // Remove info placeholder if present
        const infoEl = list.querySelector('.alert-item.info');
        if (infoEl) infoEl.remove();

        const el = document.createElement('div');
        el.className = `alert-item ${severity}`;
        el.innerHTML = `
            <strong>${data.sensor_name || data.sensor_id || 'System'}</strong>
            <span class="alert-severity-badge ${severity}">${severity.toUpperCase()}</span>
            <br>
            ${reason}<br>
            <small class="alert-time">${new Date().toLocaleTimeString()}</small>
        `;

        list.insertBefore(el, list.firstChild);

        // Keep max 25 alerts
        while (list.children.length > 25) {
            list.removeChild(list.lastChild);
        }

        // Play sound for critical alerts
        playAlertBeep(severity);
    }

    // =========================================================
    //  8. SPECIES PREDICTIONS (fetch with mock fallback)
    // =========================================================
    function loadSpeciesPredictions() {
        const list = document.getElementById('species-list');

        fetch('/api/v1/predictions/species/GRID-01')
            .then(res => {
                if (!res.ok) throw new Error('API unavailable');
                return res.json();
            })
            .then(data => renderSpecies(data))
            .catch(() => {
                console.log('[BlueByte] Using mock species data');
                const mock = [
                    { species: "Indian Mackerel", confidence: 0.87 },
                    { species: "Yellowfin Tuna", confidence: 0.74 },
                    { species: "Oil Sardine", confidence: 0.62 },
                    { species: "Hilsa Shad", confidence: 0.48 },
                    { species: "Pomfret", confidence: 0.35 },
                    { species: "Seer Fish", confidence: 0.22 }
                ];
                renderSpecies(mock);
            });

        function renderSpecies(data) {
            list.innerHTML = '';
            data.sort((a, b) => b.confidence - a.confidence).forEach(item => {
                const perc = (item.confidence * 100).toFixed(0);
                const div = document.createElement('div');
                div.className = 'species-item';
                div.innerHTML = `
                    <div class="species-name">
                        <span>${item.species}</span>
                        <span>${perc}%</span>
                    </div>
                    <div class="species-bar-bg">
                        <div class="species-bar-fill"></div>
                    </div>
                `;
                list.appendChild(div);

                // Animate bar fill after append
                requestAnimationFrame(() => {
                    const fill = div.querySelector('.species-bar-fill');
                    if (fill) fill.style.width = `${perc}%`;
                });
            });
        }
    }

    // =========================================================
    //  9. PFZ DATA (fetch with mock fallback)
    // =========================================================
    function loadPFZ() {
        fetch('/api/v1/predictions/pfz')
            .then(res => {
                if (!res.ok) throw new Error('API unavailable');
                return res.json();
            })
            .then(data => {
                if (data.zones) data.zones.forEach(z => oceanMap.addPFZZone(z));
            })
            .catch(() => {
                console.log('[BlueByte] Using mock PFZ data');
                const mockPFZ = [
                    { lat: 15.5, lon: 72.0, confidence: 0.88, species: "Indian Mackerel", radius_km: 15 },
                    { lat: 10.0, lon: 75.5, confidence: 0.76, species: "Yellowfin Tuna", radius_km: 25 },
                    { lat: 12.2, lon: 81.0, confidence: 0.91, species: "Mixed", radius_km: 10 },
                    { lat: 8.5, lon: 77.0, confidence: 0.68, species: "Seer Fish", radius_km: 18 },
                    { lat: 20.0, lon: 87.5, confidence: 0.82, species: "Hilsa Shad", radius_km: 20 }
                ];
                mockPFZ.forEach(z => oceanMap.addPFZZone(z));
            });
    }

    // =========================================================
    //  10. WEBSOCKET SETUP
    // =========================================================
    const ws = new TelemetryWebSocket('ws://localhost:8000/ws/live-telemetry');

    ws.onConnectionChange((status) => {
        const dot = document.getElementById('connection-status-dot');
        const text = document.getElementById('connection-status-text');
        if (status === 'connected') {
            dot.classList.add('connected');
            text.textContent = 'Connected';
            demoModeActive = false;
        } else {
            dot.classList.remove('connected');
            text.textContent = 'Reconnecting... (Demo Mode)';
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

    // =========================================================
    //  11. DEMO MODE — Rich simulation for hackathon presentation
    //      Uses realistic INCOIS-style buoy names (§5 usability)
    // =========================================================
    let demoModeActive = false;
    let demoInterval = null;

    // Realistic buoy data covering the Indian coastline
    const mockBuoys = [
        {
            id: "BUOY-SW01",
            name: "Goa Coastal Deep-Water Buoy",
            lat: 15.35, lon: 73.68,
            sst: 28.5, sal: 34.2, do: 5.1, chl: 1.8
        },
        {
            id: "BUOY-SW02",
            name: "Kochi Offshore Moored Buoy",
            lat: 9.95, lon: 75.82,
            sst: 29.1, sal: 33.8, do: 4.8, chl: 2.1
        },
        {
            id: "BUOY-BOB01",
            name: "Visakhapatnam Bay Buoy",
            lat: 17.72, lon: 83.35,
            sst: 30.2, sal: 32.5, do: 4.2, chl: 3.4
        },
        {
            id: "BUOY-BOB02",
            name: "Chennai Coastal Monitoring Buoy",
            lat: 13.08, lon: 80.35,
            sst: 29.8, sal: 33.1, do: 4.6, chl: 2.7
        },
        {
            id: "BUOY-AS01",
            name: "Mumbai High Offshore Buoy",
            lat: 19.40, lon: 71.50,
            sst: 27.9, sal: 35.0, do: 5.4, chl: 1.2
        },
        {
            id: "BUOY-BOB03",
            name: "Paradip Coastal Buoy",
            lat: 20.32, lon: 86.75,
            sst: 29.5, sal: 31.8, do: 4.0, chl: 4.1
        },
        {
            id: "BUOY-AS02",
            name: "Lakshadweep Islands Buoy",
            lat: 10.57, lon: 72.63,
            sst: 29.4, sal: 34.6, do: 5.2, chl: 0.8
        },
        {
            id: "BUOY-AN01",
            name: "Andaman Deep-Sea Buoy",
            lat: 11.68, lon: 92.72,
            sst: 30.0, sal: 32.9, do: 4.5, chl: 1.6
        }
    ];

    // Multiple vessel tracks
    const mockVessels = [
        { id: "IND-FV-0342", name: "MV Sagarmala", lat: 8.0, lon: 77.0, heading: 45, speed: 12.5 },
        { id: "IND-FV-0187", name: "FV Matsya Varuna", lat: 14.5, lon: 70.0, heading: 120, speed: 8.2 },
        { id: "IND-CG-0051", name: "ICGS Vikram", lat: 18.0, lon: 84.0, heading: 270, speed: 18.0, flagged: false }
    ];

    // Varied anomaly types and severities
    const anomalyTypes = [
        { reason: "Rapid SST drop detected (-2.5°C/hr)", severity: "critical", zScore: -3.2 },
        { reason: "Dissolved oxygen critically low (hypoxia risk)", severity: "critical", zScore: -4.1 },
        { reason: "Unusual salinity spike (freshwater intrusion)", severity: "high", zScore: 2.8 },
        { reason: "Elevated chlorophyll-a (possible algal bloom)", severity: "high", zScore: 3.5 },
        { reason: "SST above seasonal average", severity: "medium", zScore: 1.9 },
        { reason: "Mild salinity fluctuation", severity: "low", zScore: 1.2 }
    ];

    function startDemoMode() {
        demoModeActive = true;
        console.log('[BlueByte] Starting Demo Mode — simulating live telemetry');

        if (demoInterval) clearInterval(demoInterval);

        let tick = 0;

        demoInterval = setInterval(() => {
            if (!demoModeActive) {
                clearInterval(demoInterval);
                return;
            }

            tick++;

            // Update a random buoy with slight variation
            const buoy = mockBuoys[Math.floor(Math.random() * mockBuoys.length)];
            buoy.sst += (Math.random() - 0.5) * 0.15;
            buoy.sal += (Math.random() - 0.5) * 0.08;
            buoy.do += (Math.random() - 0.5) * 0.05;
            buoy.chl += (Math.random() - 0.5) * 0.1;

            // Clamp values to realistic ranges
            buoy.sst = Math.max(25, Math.min(33, buoy.sst));
            buoy.sal = Math.max(30, Math.min(36, buoy.sal));
            buoy.do = Math.max(3.0, Math.min(7.0, buoy.do));
            buoy.chl = Math.max(0.2, Math.min(6.0, buoy.chl));

            const telemetryData = {
                sensor_id: buoy.id,
                sensor_name: buoy.name,
                lat: buoy.lat,
                lon: buoy.lon,
                sea_surface_temp_c: buoy.sst,
                salinity_psu: buoy.sal,
                dissolved_oxygen_mg_l: buoy.do,
                chlorophyll_a_mg_m3: buoy.chl
            };

            oceanMap.addBuoyReading(telemetryData);
            charts.updateCharts(telemetryData);

            // Move vessels along their headings
            mockVessels.forEach(v => {
                const headingRad = (v.heading * Math.PI) / 180;
                v.lat += Math.cos(headingRad) * 0.015;
                v.lon += Math.sin(headingRad) * 0.015;

                // Slight heading drift
                v.heading = (v.heading + (Math.random() - 0.5) * 4) % 360;

                oceanMap.addVesselPosition({
                    vessel_id: v.id,
                    vessel_name: v.name,
                    lat: v.lat,
                    lon: v.lon,
                    heading: Math.round(v.heading),
                    speed: v.speed + (Math.random() - 0.5) * 1.5,
                    flagged: v.flagged || false
                });
            });

            // Random anomaly (8% chance per tick — enough to demo without overwhelming)
            if (Math.random() > 0.92) {
                const anomalyTemplate = anomalyTypes[Math.floor(Math.random() * anomalyTypes.length)];
                const targetBuoy = mockBuoys[Math.floor(Math.random() * mockBuoys.length)];

                const anomalyData = {
                    sensor_id: targetBuoy.id,
                    sensor_name: targetBuoy.name,
                    lat: targetBuoy.lat,
                    lon: targetBuoy.lon,
                    anomaly_flag: true,
                    anomaly_reason: anomalyTemplate.reason,
                    severity: anomalyTemplate.severity,
                    z_score_sst: anomalyTemplate.zScore
                };

                oceanMap.addAnomalyMarker(anomalyData);
                addAlertToUI(anomalyData);
            }

        }, 1800); // Every 1.8 seconds for a lively demo
    }

    // =========================================================
    //  12. BOOT SEQUENCE
    // =========================================================
    // Load persisted preferences
    const savedPrefs = loadPreferences();
    applyPreferences(savedPrefs);

    // Load initial data
    loadSpeciesPredictions();
    loadPFZ();

    // Connect WebSocket (will fall back to demo mode if server isn't running)
    ws.connect();

    console.log('[BlueByte] 🌊 Dashboard initialized');
});

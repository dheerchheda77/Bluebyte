/**
 * BlueByte AI — Ocean Map Controller
 * Manages the Leaflet map, layer groups, buoy/vessel/PFZ/anomaly markers, and legend.
 */
class OceanMap {
    constructor(containerId) {
        this.map = L.map(containerId, {
            zoomControl: true,
            attributionControl: true
        }).setView([14, 78], 5); // Centered on Indian Ocean

        // Dark theme tiles (CartoDB dark)
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(this.map);

        // Layer Groups — one per toggle
        this.layers = {
            'heatmap': L.layerGroup().addTo(this.map),
            'buoys': L.layerGroup().addTo(this.map),
            'vessels': L.layerGroup().addTo(this.map),
            'pfz': L.layerGroup().addTo(this.map),
            'anomalies': L.layerGroup().addTo(this.map)
        };

        this.heatLayer = null;
        this.heatPoints = [];
        this.markers = {}; // Store markers by ID to update them (no duplicates)

        this.addLegend();
    }

    /**
     * Toggle a layer group on/off without re-fetching data.
     */
    toggleLayer(layerName, visible) {
        if (this.layers[layerName]) {
            if (visible) {
                this.map.addLayer(this.layers[layerName]);
            } else {
                this.map.removeLayer(this.layers[layerName]);
            }
        }
    }

    /**
     * Add or update a buoy reading marker.
     * Matched by sensor_id so markers update in-place rather than duplicate.
     * Values formatted to 2 decimal places with em-dash fallback for missing data.
     */
    addBuoyReading(data) {
        if (!data.lat || !data.lon || !data.sensor_id) return;

        const fmt = (val) => (val != null && !isNaN(val)) ? Number(val).toFixed(2) : '—';

        const popupContent = `
            <div style="min-width: 180px;">
                <strong style="color: #00e5ff; font-size: 0.95rem;">
                    <i class="fa-solid fa-anchor" style="margin-right:4px;"></i>
                    ${data.sensor_name || data.sensor_id}
                </strong>
                <hr style="border: none; border-top: 1px solid rgba(0,229,255,0.2); margin: 6px 0;">
                <div style="display: grid; grid-template-columns: auto 1fr; gap: 3px 12px; font-size: 0.84rem;">
                    <span style="color: #8e9bb0;">SST:</span>
                    <span style="color: #00e5ff; font-family: monospace;">${fmt(data.sea_surface_temp_c)} °C</span>
                    <span style="color: #8e9bb0;">Salinity:</span>
                    <span style="color: #00e676; font-family: monospace;">${fmt(data.salinity_psu)} PSU</span>
                    <span style="color: #8e9bb0;">DO:</span>
                    <span style="color: #ff6f00; font-family: monospace;">${fmt(data.dissolved_oxygen_mg_l)} mg/L</span>
                    <span style="color: #8e9bb0;">Chlorophyll:</span>
                    <span style="color: #76ff03; font-family: monospace;">${fmt(data.chlorophyll_a_mg_m3)} mg/m³</span>
                </div>
            </div>
        `;

        if (this.markers[data.sensor_id]) {
            this.markers[data.sensor_id].setLatLng([data.lat, data.lon]);
            this.markers[data.sensor_id].getPopup().setContent(popupContent);
        } else {
            const marker = L.circleMarker([data.lat, data.lon], {
                radius: 7,
                fillColor: "#00e5ff",
                color: "#00e5ff",
                weight: 1.5,
                opacity: 1,
                fillOpacity: 0.8
            }).bindPopup(popupContent, {
                maxWidth: 260,
                className: 'bluebyte-popup'
            });

            marker.addTo(this.layers['buoys']);
            this.markers[data.sensor_id] = marker;
        }

        // Add to heat points
        if (data.sea_surface_temp_c != null) {
            this.heatPoints.push([data.lat, data.lon, data.sea_surface_temp_c]);
            if (this.heatPoints.length > 500) {
                this.heatPoints.shift();
            }
            this.updateHeatmap();
        }
    }

    /**
     * Add or update a vessel position marker with heading-rotated icon.
     */
    addVesselPosition(data) {
        if (!data.lat || !data.lon || !data.vessel_id) return;

        const popupContent = `
            <div style="min-width: 160px;">
                <strong style="color: #ff6f00; font-size: 0.95rem;">
                    <i class="fa-solid fa-ship" style="margin-right:4px;"></i>
                    ${data.vessel_name || data.vessel_id}
                </strong>
                <hr style="border: none; border-top: 1px solid rgba(255,111,0,0.3); margin: 6px 0;">
                <div style="display: grid; grid-template-columns: auto 1fr; gap: 3px 12px; font-size: 0.84rem;">
                    <span style="color: #8e9bb0;">Heading:</span>
                    <span style="font-family: monospace;">${data.heading != null ? data.heading + '°' : '—'}</span>
                    <span style="color: #8e9bb0;">Speed:</span>
                    <span style="font-family: monospace;">${data.speed != null ? data.speed + ' kn' : '—'}</span>
                    <span style="color: #8e9bb0;">Status:</span>
                    <span style="color: ${data.flagged ? '#ff1744' : '#00e676'};">
                        ${data.flagged ? '⚠ Flagged' : '● Normal'}
                    </span>
                </div>
            </div>
        `;

        const iconHtml = `<div style="transform: rotate(${data.heading || 0}deg); color: #ff6f00; font-size: 18px; filter: drop-shadow(0 0 4px rgba(255,111,0,0.5));">
            <i class="fa-solid fa-location-arrow"></i>
        </div>`;

        const customIcon = L.divIcon({
            html: iconHtml,
            className: 'custom-vessel-icon',
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });

        if (this.markers[data.vessel_id]) {
            this.markers[data.vessel_id].setLatLng([data.lat, data.lon]);
            this.markers[data.vessel_id].setIcon(customIcon);
            this.markers[data.vessel_id].getPopup().setContent(popupContent);
        } else {
            const marker = L.marker([data.lat, data.lon], { icon: customIcon })
                .bindPopup(popupContent, { maxWidth: 240 });
            marker.addTo(this.layers['vessels']);
            this.markers[data.vessel_id] = marker;
        }
    }

    /**
     * Rebuild the heatmap layer from accumulated SST data points.
     */
    updateHeatmap() {
        if (this.heatLayer) {
            this.layers['heatmap'].removeLayer(this.heatLayer);
        }

        if (typeof L.heatLayer !== 'undefined' && this.heatPoints.length > 0) {
            const normalizedPoints = this.heatPoints.map(p => [
                p[0], p[1], Math.max(0.1, Math.min(1.0, (p[2] - 20) / 15))
            ]);

            this.heatLayer = L.heatLayer(normalizedPoints, {
                radius: 25,
                blur: 15,
                maxZoom: 10,
                gradient: { 0.4: 'blue', 0.6: 'cyan', 0.7: 'lime', 0.8: 'yellow', 1.0: 'red' }
            }).addTo(this.layers['heatmap']);
        }
    }

    /**
     * Add a PFZ (Potential Fishing Zone) circle overlay.
     */
    addPFZZone(zone) {
        if (!zone.lat || !zone.lon) return;

        const confPercent = (zone.confidence * 100).toFixed(1);
        const popupContent = `
            <div style="min-width: 160px;">
                <strong style="color: #00e676; font-size: 0.95rem;">
                    <i class="fa-solid fa-fish" style="margin-right:4px;"></i>
                    Potential Fishing Zone
                </strong>
                <hr style="border: none; border-top: 1px solid rgba(0,230,118,0.3); margin: 6px 0;">
                <div style="font-size: 0.84rem;">
                    <div>Confidence: <strong style="color: #00e676;">${confPercent}%</strong></div>
                    <div>Target: <strong>${zone.species || 'Mixed'}</strong></div>
                    <div style="color: #8e9bb0;">Radius: ${zone.radius_km || 10} km</div>
                </div>
            </div>
        `;

        const circle = L.circle([zone.lat, zone.lon], {
            color: '#00e676',
            fillColor: '#00e676',
            fillOpacity: 0.15,
            radius: (zone.radius_km || 10) * 1000,
            weight: 2,
            dashArray: '6 4'
        }).bindPopup(popupContent, { maxWidth: 220 });

        circle.addTo(this.layers['pfz']);
    }

    /**
     * Add an anomaly marker with severity-aware styling.
     * Severity: 'critical' (pulsing glow), 'high' (static red), 'medium' (orange).
     */
    addAnomalyMarker(data) {
        if (!data.lat || !data.lon) return;

        const severity = data.severity || 'critical';

        const popupContent = `
            <div style="min-width: 180px;">
                <strong style="color: #ff1744; font-size: 0.95rem;">
                    <i class="fa-solid fa-triangle-exclamation" style="margin-right:4px;"></i>
                    ANOMALY DETECTED
                </strong>
                <hr style="border: none; border-top: 1px solid rgba(255,23,68,0.3); margin: 6px 0;">
                <div style="font-size: 0.84rem;">
                    <div>Sensor: <strong>${data.sensor_name || data.sensor_id}</strong></div>
                    <div>Reason: ${data.anomaly_reason || 'Unknown'}</div>
                    <div>SST Z-Score: <span style="color: #ff1744; font-family: monospace;">
                        ${data.z_score_sst ? data.z_score_sst.toFixed(2) : 'N/A'}
                    </span></div>
                    <div style="color: #8e9bb0; font-size: 0.78rem; margin-top: 4px;">
                        Severity: <span class="alert-severity-badge ${severity}" style="font-size:0.7rem;">${severity.toUpperCase()}</span>
                    </div>
                </div>
            </div>
        `;

        // Severity-aware icon class
        let iconClass = 'pulse-icon';
        if (severity === 'high') iconClass = 'pulse-icon high';
        else if (severity === 'medium') iconClass = 'pulse-icon medium';

        const pulseIcon = L.divIcon({
            className: iconClass,
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });

        const marker = L.marker([data.lat, data.lon], { icon: pulseIcon })
            .bindPopup(popupContent, { maxWidth: 260 });

        marker.addTo(this.layers['anomalies']);

        // Auto-remove after 5 minutes
        setTimeout(() => {
            if (this.layers['anomalies'].hasLayer(marker)) {
                this.layers['anomalies'].removeLayer(marker);
            }
        }, 300000);
    }

    /**
     * Add styled legend control to the map.
     * Uses CSS classes instead of inline styles for consistency.
     */
    addLegend() {
        const legend = L.control({ position: 'bottomright' });
        legend.onAdd = function () {
            const div = L.DomUtil.create('div', 'map-legend');
            div.innerHTML = `
                <div class="map-legend-title">Map Layers</div>
                <div class="map-legend-item">
                    <span class="map-legend-dot" style="background: #00e5ff;"></span>
                    Buoy / Sensor
                </div>
                <div class="map-legend-item">
                    <span class="map-legend-dot" style="background: #ff6f00;"></span>
                    Vessel
                </div>
                <div class="map-legend-item">
                    <span class="map-legend-dot" style="background: rgba(0,230,118,0.4); border: 1.5px solid #00e676;"></span>
                    PFZ Zone
                </div>
                <div class="map-legend-item">
                    <span class="map-legend-dot" style="background: #ff1744; box-shadow: 0 0 6px #ff1744;"></span>
                    Anomaly
                </div>
                <div class="map-legend-item" style="margin-top: 4px; padding-top: 4px; border-top: 1px solid rgba(0,229,255,0.15);">
                    <span class="map-legend-dot" style="background: linear-gradient(135deg, blue, cyan, lime, yellow, red); opacity: 0.7;"></span>
                    SST Heatmap
                </div>
            `;
            return div;
        };
        legend.addTo(this.map);
    }
}

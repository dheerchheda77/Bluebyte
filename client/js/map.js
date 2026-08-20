class OceanMap {
    constructor(containerId) {
        this.map = L.map(containerId).setView([14, 78], 5); // Centered on Indian Ocean
        
        // Dark theme tiles
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(this.map);

        // Layer Groups
        this.layers = {
            'heatmap': L.layerGroup().addTo(this.map),
            'buoys': L.layerGroup().addTo(this.map),
            'vessels': L.layerGroup().addTo(this.map),
            'pfz': L.layerGroup().addTo(this.map),
            'anomalies': L.layerGroup().addTo(this.map)
        };

        this.heatLayer = null;
        this.heatPoints = [];
        this.markers = {}; // Store markers by ID to update them

        this.addLegend();
    }

    toggleLayer(layerName, visible) {
        if (this.layers[layerName]) {
            if (visible) {
                this.map.addLayer(this.layers[layerName]);
            } else {
                this.map.removeLayer(this.layers[layerName]);
            }
        }
    }

    addBuoyReading(data) {
        if (!data.lat || !data.lon || !data.sensor_id) return;
        
        const popupContent = `
            <strong>Sensor: ${data.sensor_name || data.sensor_id}</strong><br>
            SST: ${data.sea_surface_temp_c ? data.sea_surface_temp_c.toFixed(2) : '--'} °C<br>
            Salinity: ${data.salinity_psu ? data.salinity_psu.toFixed(2) : '--'} PSU<br>
            DO: ${data.dissolved_oxygen_mg_l ? data.dissolved_oxygen_mg_l.toFixed(2) : '--'} mg/L<br>
            Chlorophyll: ${data.chlorophyll_a_mg_m3 ? data.chlorophyll_a_mg_m3.toFixed(2) : '--'} mg/m³
        `;

        if (this.markers[data.sensor_id]) {
            this.markers[data.sensor_id].setLatLng([data.lat, data.lon]);
            this.markers[data.sensor_id].getPopup().setContent(popupContent);
        } else {
            const marker = L.circleMarker([data.lat, data.lon], {
                radius: 6,
                fillColor: "#00e5ff",
                color: "#00e5ff",
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            }).bindPopup(popupContent);
            
            marker.addTo(this.layers['buoys']);
            this.markers[data.sensor_id] = marker;
        }

        // Add to heat points
        if (data.sea_surface_temp_c) {
            this.heatPoints.push([data.lat, data.lon, data.sea_surface_temp_c]);
            // Keep array size reasonable
            if (this.heatPoints.length > 500) {
                this.heatPoints.shift();
            }
            this.updateHeatmap();
        }
    }

    addVesselPosition(data) {
        if (!data.lat || !data.lon || !data.vessel_id) return;
        
        const popupContent = `
            <strong>Vessel: ${data.vessel_id}</strong><br>
            Heading: ${data.heading || '--'}°<br>
            Speed: ${data.speed || '--'} knots
        `;

        const iconHtml = `<div style="transform: rotate(${data.heading || 0}deg); color: #ff6f00; font-size: 16px;">
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
                .bindPopup(popupContent);
            marker.addTo(this.layers['vessels']);
            this.markers[data.vessel_id] = marker;
        }
    }

    updateHeatmap() {
        if (this.heatLayer) {
            this.layers['heatmap'].removeLayer(this.heatLayer);
        }
        
        if (typeof L.heatLayer !== 'undefined' && this.heatPoints.length > 0) {
            // Normalize heat intensity based on SST roughly (20 to 35 C)
            const normalizedPoints = this.heatPoints.map(p => [
                p[0], p[1], Math.max(0.1, Math.min(1.0, (p[2] - 20) / 15))
            ]);
            
            this.heatLayer = L.heatLayer(normalizedPoints, {
                radius: 25,
                blur: 15,
                maxZoom: 10,
                gradient: {0.4: 'blue', 0.6: 'cyan', 0.7: 'lime', 0.8: 'yellow', 1.0: 'red'}
            }).addTo(this.layers['heatmap']);
        }
    }

    addPFZZone(zone) {
        if (!zone.lat || !zone.lon) return;
        
        const popupContent = `
            <strong>Potential Fishing Zone</strong><br>
            Confidence: ${(zone.confidence * 100).toFixed(1)}%<br>
            Target: ${zone.species || 'Mixed'}
        `;

        const circle = L.circle([zone.lat, zone.lon], {
            color: '#00e676',
            fillColor: '#00e676',
            fillOpacity: 0.3,
            radius: (zone.radius_km || 10) * 1000, // convert km to meters
            weight: 2
        }).bindPopup(popupContent);
        
        circle.addTo(this.layers['pfz']);
    }

    addAnomalyMarker(data) {
        if (!data.lat || !data.lon) return;
        
        const popupContent = `
            <strong><i class="fa-solid fa-triangle-exclamation" style="color:red;"></i> ANOMALY DETECTED</strong><br>
            Sensor: ${data.sensor_id}<br>
            Reason: ${data.anomaly_reason || 'Unknown'}<br>
            SST Z-Score: ${data.z_score_sst ? data.z_score_sst.toFixed(2) : 'N/A'}
        `;

        const pulseIcon = L.divIcon({
            className: 'pulse-icon',
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });

        const marker = L.marker([data.lat, data.lon], { icon: pulseIcon })
            .bindPopup(popupContent);
            
        marker.addTo(this.layers['anomalies']);
        
        // Auto-remove after 5 minutes
        setTimeout(() => {
            if (this.layers['anomalies'].hasLayer(marker)) {
                this.layers['anomalies'].removeLayer(marker);
            }
        }, 300000);
    }

    addLegend() {
        const legend = L.control({position: 'bottomright'});
        legend.onAdd = function () {
            const div = L.DomUtil.create('div', 'info legend');
            div.style.backgroundColor = 'rgba(13, 19, 51, 0.8)';
            div.style.padding = '10px';
            div.style.borderRadius = '5px';
            div.style.border = '1px solid var(--border-color)';
            div.style.color = 'white';
            div.style.fontSize = '12px';
            
            div.innerHTML = `
                <div style="margin-bottom:5px;"><span style="display:inline-block; width:10px; height:10px; background:#00e5ff; border-radius:50%; margin-right:5px;"></span> Buoy/Sensor</div>
                <div style="margin-bottom:5px;"><span style="display:inline-block; width:10px; height:10px; background:#ff6f00; margin-right:5px;"></span> Vessel</div>
                <div style="margin-bottom:5px;"><span style="display:inline-block; width:10px; height:10px; background:rgba(0,230,118,0.3); border:1px solid #00e676; border-radius:50%; margin-right:5px;"></span> PFZ Zone</div>
                <div><span style="display:inline-block; width:10px; height:10px; background:#ff1744; border-radius:50%; margin-right:5px; box-shadow: 0 0 5px #ff1744;"></span> Anomaly</div>
            `;
            return div;
        };
        legend.addTo(this.map);
    }
}

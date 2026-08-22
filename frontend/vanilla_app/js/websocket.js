class TelemetryWebSocket {
    constructor(url) {
        this.url = url;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectDelay = 30000; // 30 seconds
        
        this.telemetryCallback = null;
        this.anomalyCallback = null;
        this.connectionCallback = null;
    }

    onTelemetry(callback) {
        this.telemetryCallback = callback;
    }

    onAnomaly(callback) {
        this.anomalyCallback = callback;
    }

    onConnectionChange(callback) {
        this.connectionCallback = callback;
    }

    connect() {
        console.log(`Attempting to connect to ${this.url}...`);
        
        try {
            this.socket = new WebSocket(this.url);

            this.socket.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                if (this.connectionCallback) this.connectionCallback('connected');
            };

            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.anomaly_flag && this.anomalyCallback) {
                        this.anomalyCallback(data);
                    }
                    
                    if (this.telemetryCallback) {
                        this.telemetryCallback(data);
                    }
                } catch (e) {
                    console.error('Error parsing WebSocket message:', e);
                }
            };

            this.socket.onclose = () => {
                console.log('WebSocket disconnected');
                if (this.connectionCallback) this.connectionCallback('disconnected');
                this.scheduleReconnect();
            };

            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.socket.close();
            };

        } catch (e) {
            console.error('Failed to create WebSocket:', e);
            if (this.connectionCallback) this.connectionCallback('disconnected');
            this.scheduleReconnect();
        }
    }

    scheduleReconnect() {
        // Exponential backoff: 1s, 2s, 4s, 8s, up to 30s
        const delay = Math.min(Math.pow(2, this.reconnectAttempts) * 1000, this.maxReconnectDelay);
        console.log(`Reconnecting in ${delay}ms...`);
        this.reconnectAttempts++;
        setTimeout(() => this.connect(), delay);
    }
}

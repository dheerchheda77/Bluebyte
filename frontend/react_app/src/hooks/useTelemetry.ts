import { useState, useEffect, useRef, useCallback } from 'react'
import type { Station, MarineAlert } from '../types/marine'
import { stations as initialStations } from '../data/stations'

interface TelemetryData {
  sensor_id: string
  lat: number
  lon: number
  sea_surface_temp_c?: number
  salinity_psu?: number
  dissolved_oxygen_mg_l?: number
  chlorophyll_a_mg_m3?: number
  anomaly_flag?: boolean
  anomaly_reason?: string
  severity?: 'critical' | 'high' | 'medium' | 'low'
  sensor_name?: string
}

export function useTelemetry(url: string) {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')
  const [stations, setStations] = useState<Station[]>(initialStations)
  const [alerts, setAlerts] = useState<MarineAlert[]>([])
  
  const socketRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectDelay = 30000

  const connect = useCallback(() => {
    setStatus('connecting')
    try {
      const socket = new WebSocket(url)
      socketRef.current = socket

      socket.onopen = () => {
        setStatus('connected')
        reconnectAttempts.current = 0
      }

      socket.onmessage = (event) => {
        try {
          const data: TelemetryData = JSON.parse(event.data)
          
          // Update stations
          setStations(prev => {
            const index = prev.findIndex(s => s.id === data.sensor_id)
            if (index === -1) {
              // Add new station
              const newStation: Station = {
                id: data.sensor_id,
                name: data.sensor_name || data.sensor_id,
                agency: 'LIVE',
                lat: data.lat,
                lng: data.lon,
                sst: data.sea_surface_temp_c || 28.0,
                salinity: data.salinity_psu || 35.0,
                oxygen: data.dissolved_oxygen_mg_l || 4.0,
                chlorophyll: data.chlorophyll_a_mg_m3 || 1.0,
                depth: 50, // mock
                status: data.anomaly_flag ? 'anomaly' : 'nominal',
                updatedMinutes: 0
              }
              return [...prev, newStation]
            }
            
            // Update existing station
            const updated = [...prev]
            updated[index] = {
              ...updated[index],
              lat: data.lat ?? updated[index].lat,
              lng: data.lon ?? updated[index].lng,
              sst: data.sea_surface_temp_c ?? updated[index].sst,
              salinity: data.salinity_psu ?? updated[index].salinity,
              oxygen: data.dissolved_oxygen_mg_l ?? updated[index].oxygen,
              chlorophyll: data.chlorophyll_a_mg_m3 ?? updated[index].chlorophyll,
              status: data.anomaly_flag ? 'anomaly' : 'nominal',
              updatedMinutes: 0
            }
            return updated
          })

          // Handle anomaly alerts
          if (data.anomaly_flag) {
            setAlerts(prev => {
              const severityMap: Record<string, MarineAlert['severity']> = {
                'critical': 'critical',
                'high': 'warning',
                'medium': 'warning',
                'low': 'info'
              }
              const newAlert: MarineAlert = {
                id: `alert-${Date.now()}`,
                severity: severityMap[data.severity || 'high'] || 'warning',
                title: 'Anomaly Detected',
                detail: data.anomaly_reason || 'Unknown anomaly',
                zone: data.sensor_name || data.sensor_id,
                minutesAgo: 0
              }
              // Keep last 25 alerts
              return [newAlert, ...prev].slice(0, 25)
            })
          }

        } catch (e) {
          console.error('Error parsing telemetry message:', e)
        }
      }

      socket.onclose = () => {
        setStatus('disconnected')
        scheduleReconnect()
      }

      socket.onerror = () => {
        socket.close()
      }
    } catch (e) {
      setStatus('disconnected')
      scheduleReconnect()
    }
  }, [url])

  const scheduleReconnect = useCallback(() => {
    const delay = Math.min(Math.pow(2, reconnectAttempts.current) * 1000, maxReconnectDelay)
    reconnectAttempts.current++
    setTimeout(connect, delay)
  }, [connect])

  useEffect(() => {
    connect()
    return () => {
      if (socketRef.current) {
        socketRef.current.close()
      }
    }
  }, [connect])

  return { status, stations, alerts }
}

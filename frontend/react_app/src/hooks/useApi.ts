import { useState, useEffect } from 'react'
import type { PfzZone, SpeciesPrediction } from '../types/marine'
import { pfzZones as fallbackPfz } from '../data/zones'
import { speciesPredictions as fallbackSpecies } from '../data/marineContent'

export function useApi(baseUrl: string) {
  const [pfzZones, setPfzZones] = useState<PfzZone[]>(fallbackPfz)
  const [species, setSpecies] = useState<SpeciesPrediction[]>(fallbackSpecies)

  useEffect(() => {
    // Fetch PFZ zones
    fetch(`${baseUrl}/api/v1/predictions/pfz`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch PFZ')
        return res.json()
      })
      .then(data => {
        if (data.zones && Array.isArray(data.zones)) {
          // Map backend format to frontend PfzZone
          const mapped: PfzZone[] = data.zones.map((z: any, idx: number) => ({
            id: `PFZ-${idx}`,
            name: z.species ? `Potential ${z.species} Zone` : 'Mixed PFZ',
            confidence: z.confidence || 0.8,
            targetSpecies: z.species || 'Mixed',
            // Create a small polygon around the center point for the map
            coords: [
              [z.lat - 0.1, z.lon - 0.1],
              [z.lat + 0.1, z.lon - 0.1],
              [z.lat + 0.1, z.lon + 0.1],
              [z.lat - 0.1, z.lon + 0.1],
            ]
          }))
          setPfzZones(mapped)
        }
      })
      .catch(err => console.warn('Using fallback PFZ data:', err))

    // Fetch Species predictions
    fetch(`${baseUrl}/api/v1/predictions/species/GRID-01`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch Species')
        return res.json()
      })
      .then(data => {
        if (Array.isArray(data)) {
          const mapped: SpeciesPrediction[] = data.map((s: any, idx: number) => ({
            id: `sp-${idx}`,
            common: s.species,
            scientific: s.species,
            confidence: s.confidence,
            trend: (Math.random() - 0.5) * 10, // Mock trend since not in API
            driver: 'SST suitability',
            biomassIndex: Math.floor(s.confidence * 100)
          }))
          setSpecies(mapped)
        }
      })
      .catch(err => console.warn('Using fallback Species data:', err))

  }, [baseUrl])

  return { pfzZones, species }
}

export type DomainId = 'ocean' | 'fisheries' | 'biodiversity'

export type LayerId =
  | 'sst'
  | 'chlorophyll'
  | 'buoys'
  | 'pfz'
  | 'vessels'
  | 'edna'
  | 'anomalies'

export interface LayerDef {
  id: LayerId
  label: string
  domain: DomainId
  detail: string
  color: string
}

export interface Station {
  id: string
  name: string
  agency: string
  lat: number
  lng: number
  sst: number
  salinity: number
  oxygen: number
  chlorophyll: number
  depth: number
  status: 'nominal' | 'anomaly' | 'offline'
  updatedMinutes: number
}

export interface PfzZone {
  id: string
  name: string
  confidence: number
  coords: [number, number][]
  targetSpecies: string
}

export interface VesselTrack {
  id: string
  name: string
  risk: 'clear' | 'review' | 'flagged'
  path: [number, number][]
}

export interface EdnaSite {
  id: string
  name: string
  lat: number
  lng: number
  richness: number
  novelTaxa: number
  sampledDaysAgo: number
}

export interface SpeciesPrediction {
  id: string
  common: string
  scientific: string
  confidence: number
  trend: number
  driver: string
  biomassIndex: number
}

export interface EdnaDetection {
  id: string
  taxon: string
  readShare: number
  siteId: string
  status: 'known' | 'novel' | 'invasive'
  barcode: string
}

export interface MarineAlert {
  id: string
  severity: 'critical' | 'warning' | 'info'
  title: string
  detail: string
  zone: string
  minutesAgo: number
}

export interface DatasetSource {
  id: string
  agency: string
  dataset: string
  records: string
  latency: string
  quality: number
  status: 'streaming' | 'harmonized' | 'stale'
}

export interface SeriesPoint {
  t: string
  sst: number
  salinity: number
  oxygen: number
  chlorophyll: number
  richness: number
}

import type { EdnaSite, PfzZone, VesselTrack } from '../types/marine'

export const pfzZones: PfzZone[] = [
  {
    id: 'PFZ-AS-04',
    name: 'Malpe–Karwar Upwelling Front',
    confidence: 0.91,
    targetSpecies: 'Indian oil sardine',
    coords: [
      [13.9, 73.4],
      [14.3, 74.05],
      [13.2, 74.42],
      [12.6, 74.0],
      [12.85, 73.35],
    ],
  },
  {
    id: 'PFZ-AS-11',
    name: 'Lakshadweep Thermal Ridge',
    confidence: 0.78,
    targetSpecies: 'Yellowfin tuna',
    coords: [
      [11.4, 71.2],
      [11.9, 72.4],
      [10.6, 72.9],
      [10.1, 71.7],
    ],
  },
  {
    id: 'PFZ-BB-06',
    name: 'Godavari Plume Convergence',
    confidence: 0.66,
    targetSpecies: 'Indian mackerel',
    coords: [
      [16.6, 82.1],
      [17.1, 83.4],
      [15.9, 83.8],
      [15.4, 82.5],
    ],
  },
]

export const vesselTracks: VesselTrack[] = [
  {
    id: 'IND-4417',
    name: 'MFV Samudra Rekha',
    risk: 'clear',
    path: [
      [12.9, 74.8],
      [13.2, 74.1],
      [13.6, 73.5],
      [13.9, 73.1],
    ],
  },
  {
    id: 'IND-9820',
    name: 'MFV Nila Kadal',
    risk: 'flagged',
    path: [
      [10.1, 76.0],
      [9.8, 75.1],
      [9.4, 74.2],
      [9.6, 73.4],
      [10.2, 72.8],
    ],
  },
  {
    id: 'UNK-0031',
    name: 'Unregistered AIS drop',
    risk: 'review',
    path: [
      [17.4, 83.6],
      [16.9, 84.4],
      [16.2, 85.1],
    ],
  },
]

export const ednaSites: EdnaSite[] = [
  {
    id: 'EDNA-114',
    name: 'Netrani Transect',
    lat: 14.02,
    lng: 74.33,
    richness: 218,
    novelTaxa: 6,
    sampledDaysAgo: 3,
  },
  {
    id: 'EDNA-207',
    name: 'Gulf of Mannar Reef',
    lat: 9.12,
    lng: 79.14,
    richness: 341,
    novelTaxa: 11,
    sampledDaysAgo: 9,
  },
  {
    id: 'EDNA-063',
    name: 'Sundarbans Estuary',
    lat: 21.68,
    lng: 88.92,
    richness: 156,
    novelTaxa: 4,
    sampledDaysAgo: 14,
  },
  {
    id: 'EDNA-188',
    name: 'Andaman Fringing Reef',
    lat: 11.94,
    lng: 92.94,
    richness: 402,
    novelTaxa: 17,
    sampledDaysAgo: 5,
  },
]

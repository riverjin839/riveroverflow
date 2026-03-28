import { create } from 'zustand'

export interface OntologyObject {
  id: string
  type: string
  key: string
  properties: Record<string, unknown>
}

export interface OntologyLink {
  id: string
  subject_key: string
  subject_type: string
  predicate: string
  object_key: string
  object_type: string
  properties: Record<string, unknown>
}

export interface OntologyRule {
  id: string
  name: string
  description: string
  trigger_type: string
  condition: Record<string, unknown>
  action_type: string
  action_params: Record<string, unknown>
  enabled: boolean
  priority: number
}

export interface OntologySummary {
  objects: Record<string, number>
  total_links: number
  total_rules: number
  enabled_rules: number
}

interface OntologyState {
  objects: OntologyObject[]
  links: OntologyLink[]
  rules: OntologyRule[]
  summary: OntologySummary | null
  loading: boolean
  setObjects: (objects: OntologyObject[]) => void
  setLinks: (links: OntologyLink[]) => void
  setRules: (rules: OntologyRule[]) => void
  setSummary: (summary: OntologySummary) => void
  setLoading: (v: boolean) => void
  updateRule: (id: string, patch: Partial<OntologyRule>) => void
}

export const useOntologyStore = create<OntologyState>((set) => ({
  objects: [],
  links: [],
  rules: [],
  summary: null,
  loading: false,
  setObjects: (objects) => set({ objects }),
  setLinks: (links) => set({ links }),
  setRules: (rules) => set({ rules }),
  setSummary: (summary) => set({ summary }),
  setLoading: (loading) => set({ loading }),
  updateRule: (id, patch) =>
    set((state) => ({
      rules: state.rules.map((r) => (r.id === id ? { ...r, ...patch } : r)),
    })),
}))
